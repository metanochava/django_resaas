"""Safe, restricted filesystem access for the Scaffold IDE - the only
place path traversal/symlink-escape/denylist checks happen. Every read
or write the IDE performs goes through `resolve_safe_path()` first;
nothing else in this codebase should build a Path from IDE-supplied
input directly.

Workspace roots are the real, currently-installed apps (settings.
MY_APPS, same resolution as AppSchemaAPIView._resolve_app_label() for
dotted entries like "django_resaas.saas") plus the frontend project's
`src` directory (module_path_front()'s sibling in management/
apicommands/view/scaffold.py) - never the whole server filesystem."""
import hashlib
import os
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings

SKIP_DIR_NAMES = {"__pycache__", ".git", "node_modules", ".venv", "venv", "dist", ".q-cache"}

# Nunca abrir por default - ver ScaffoldPage.vue's mega-prompt secção
# "NÃO EXPOR SEGREDOS". Comparação por nome de ficheiro, case-insensitive.
DENYLIST_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "credentials.json", "secrets.json", "id_rsa", "id_rsa.pub",
}
DENYLIST_SUFFIXES = {".pem", ".key"}

MAX_READ_BYTES = 2 * 1024 * 1024  # 2MB - ficheiros maiores não são editáveis pelo IDE
MAX_TREE_ENTRIES = 3000


class WorkspaceError(Exception):
    def __init__(self, message, code="workspace_error"):
        super().__init__(message)
        self.message = message
        self.code = code


def _resolve_app_label(app_name):
    """Mesma resolução de AppSchemaAPIView._resolve_app_label() (management/
    apicommands/view/app_schema.py) - duplicada aqui deliberadamente (é
    uma função pura de ~10 linhas) para não acoplar o workspace ao
    módulo de scaffold de apps; ambas resolvem a mesma coisa a partir
    do mesmo registry do Django, nunca podem divergir."""

    for cfg in django_apps.get_app_configs():
        if cfg.name == app_name or cfg.label == app_name:
            return cfg.label
    return app_name


def get_workspace_roots():
    """{root_key: Path} - root_key is exactly the MY_APPS entry string
    (e.g. "django_resaas.saas", "saude") plus "frontend" for the
    consumer app's src/ directory, when it exists."""

    roots = {}

    for app_name in settings.MY_APPS:
        try:
            cfg = django_apps.get_app_config(_resolve_app_label(app_name))
            roots[app_name] = Path(cfg.path).resolve()
        except LookupError:
            continue

    frontend_dir = getattr(settings, "FRONTEND_PROJECT_DIR", None)
    frontend_src = (
        Path(frontend_dir) / "src" if frontend_dir
        else Path(settings.BASE_DIR).parent / "front" / "src"
    )
    if frontend_src.exists():
        roots["frontend"] = frontend_src.resolve()

    return roots


def resolve_safe_path(root_key, rel_path):
    roots = get_workspace_roots()
    root = roots.get(root_key)

    if root is None:
        raise WorkspaceError(f"Unknown or unavailable workspace root: '{root_key}'", "unknown_root")

    rel_path = (rel_path or "").strip().lstrip("/")

    if not rel_path:
        return root

    candidate = (root / rel_path).resolve()

    # is_relative_to() usa o caminho já resolvido (segue symlinks) de
    # ambos os lados - cobre "../../etc/passwd", paths absolutos que
    # escapam da root, e symlinks dentro da root que apontam para fora.
    if not candidate.is_relative_to(root):
        raise WorkspaceError("Path escapes the workspace root", "path_traversal")

    if candidate.name.lower() in DENYLIST_NAMES or candidate.suffix.lower() in DENYLIST_SUFFIXES:
        raise WorkspaceError(f"'{candidate.name}' cannot be opened by the IDE", "denied")

    return candidate


def list_tree(root_key):
    root = resolve_safe_path(root_key, "")

    if not root.exists():
        raise WorkspaceError("Workspace root does not exist on disk", "root_not_found")

    count = 0

    def walk(dir_path):
        nonlocal count
        entries = []

        try:
            children = sorted(
                dir_path.iterdir(),
                key=lambda p: (p.is_file(), p.name.lower()),
            )
        except PermissionError:
            return entries

        for child in children:
            if count >= MAX_TREE_ENTRIES:
                break

            if child.name.startswith(".") and child.name not in (".env",):
                # ficheiros ocultos genéricos não aparecem (menos o
                # próprio ".env", que já é bloqueado de outra forma no
                # denylist mas ainda listado - é mais transparente
                # mostrar que existe e está protegido do que escondê-lo).
                if child.name != ".env":
                    continue

            if child.is_dir():
                if child.name in SKIP_DIR_NAMES:
                    continue
                count += 1
                entries.append({
                    "name": child.name,
                    "path": str(child.relative_to(root)),
                    "type": "directory",
                    "children": walk(child),
                })
            else:
                count += 1
                is_denied = child.name.lower() in DENYLIST_NAMES or child.suffix.lower() in DENYLIST_SUFFIXES
                entries.append({
                    "name": child.name,
                    "path": str(child.relative_to(root)),
                    "type": "file",
                    "denied": is_denied,
                    "size": child.stat().st_size if not is_denied else None,
                })

        return entries

    return walk(root)


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_file(root_key, rel_path):
    path = resolve_safe_path(root_key, rel_path)

    if not path.exists() or not path.is_file():
        raise WorkspaceError("File not found", "not_found")

    if path.stat().st_size > MAX_READ_BYTES:
        raise WorkspaceError("File is too large to open in the IDE", "too_large")

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise WorkspaceError("File is not text (binary content)", "binary_file")

    return {
        "path": rel_path,
        "content": content,
        "hash": _sha256(content),
        "mtime": path.stat().st_mtime,
    }


def write_file_atomic(root_key, rel_path, content):
    """Only performs the write - validation (code_validator.validate_file)
    and conflict detection (expected_hash) are the caller's
    responsibility (IDEWorkspaceAPIView), so both single-file and
    multi-file/transactional callers share the exact same rule: nothing
    reaches here that hasn't already passed validation."""

    from django_resaas.saas.core.utils import safe_write

    path = resolve_safe_path(root_key, rel_path)
    safe_write(str(path), content)

    return {
        "path": rel_path,
        "hash": _sha256(content),
        "mtime": path.stat().st_mtime,
    }


def current_hash(root_key, rel_path):
    """None when the file does not exist yet (a new file - there is
    nothing to conflict with)."""

    path = resolve_safe_path(root_key, rel_path)

    if not path.exists():
        return None

    try:
        return _sha256(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return None

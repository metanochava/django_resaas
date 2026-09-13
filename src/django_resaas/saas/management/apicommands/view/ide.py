"""Scaffold IDE - backend for pages/commands/ScaffoldPage.vue's file
explorer/editor/validation/apply/command-runner panels.

Same privilege class as ScaffoldAPIView (management/apicommands/view/
scaffold.py) - `IsAdminUser`, gated by `_ensure_enabled()` below. Not a
tenant-scoped resource: this reads/writes the PROJECT's own source
code, never tenant data (see mega-prompt secção 19/98 - "não confundir
terminal/IDE com tenant data").

Central rule enforced here, not just documented: `write`/`apply` always
call `code_validator.validate_file()` themselves, regardless of what
the client sent or claims - "O BACKEND DEVE REVALIDAR TUDO ANTES DE
QUALQUER ESCRITA" (mega-prompt regra final #4)."""
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied

from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ViewSet

from django_resaas.saas.core.base.views import registerView
from django_resaas.saas.core.utils import all, fail, ok
from django_resaas.saas.management.apicommands.service import (
    code_validator,
    command_runner_service,
    workspace_service,
)
from django_resaas.saas.management.apicommands.service.workspace_service import WorkspaceError

logger = logging.getLogger(__name__)


def _ide_enabled():
    """Explicit opt-in, not just DEBUG (mega-prompt secção 96: "não
    assumas que DEBUG=True é suficiente"). Defaults to DEBUG so
    existing dev environments keep working unchanged, but a project can
    set SCAFFOLD_IDE_ENABLED=True/False independently of DEBUG."""

    return getattr(settings, "SCAFFOLD_IDE_ENABLED", settings.DEBUG)


@registerView("ide", "django_resaas")
class IDEWorkspaceAPIView(ViewSet):

    permission_classes = [IsAdminUser]

    def _ensure_enabled(self, request):
        if not _ide_enabled():
            raise PermissionDenied("scaffold_ide_disabled")

    def list(self, request):
        return all(request, message="ide_ready")

    # -----------------------------------------------------
    # GET roots/  - which workspaces exist (real MY_APPS + frontend)
    # -----------------------------------------------------
    @action(detail=False, methods=["get"])
    def roots(self, request):
        self._ensure_enabled(request)
        roots = workspace_service.get_workspace_roots()
        return all(request, roots=[{"key": k, "label": k} for k in roots.keys()])

    # -----------------------------------------------------
    # GET tree/?root=<key>
    # -----------------------------------------------------
    @action(detail=False, methods=["get"])
    def tree(self, request):
        self._ensure_enabled(request)
        root = request.query_params.get("root", "")

        try:
            return all(request, tree=workspace_service.list_tree(root))
        except WorkspaceError as exc:
            return fail(request, exc.message, status=400)

    # -----------------------------------------------------
    # GET read/?root=<key>&path=<rel>
    # -----------------------------------------------------
    @action(detail=False, methods=["get"])
    def read(self, request):
        self._ensure_enabled(request)
        root = request.query_params.get("root", "")
        path = request.query_params.get("path", "")

        try:
            data = workspace_service.read_file(root, path)
        except WorkspaceError as exc:
            return fail(request, exc.message, status=400)

        data["language"] = code_validator.detect_language(path)
        return all(request, **data)

    # -----------------------------------------------------
    # POST validate/  {path, content}  - never writes
    # -----------------------------------------------------
    @action(detail=False, methods=["post"])
    def validate(self, request):
        self._ensure_enabled(request)
        path = request.data.get("path", "")
        content = request.data.get("content", "")

        result = code_validator.validate_file(path, content)
        return all(request, **result)

    # -----------------------------------------------------
    # POST write/  {root, path, content, expected_hash?}
    # -----------------------------------------------------
    @action(detail=False, methods=["post"])
    def write(self, request):
        self._ensure_enabled(request)

        root = request.data.get("root", "")
        path = request.data.get("path", "")
        content = request.data.get("content", "")
        expected_hash = request.data.get("expected_hash")

        try:
            actual_hash = workspace_service.current_hash(root, path)
        except WorkspaceError as exc:
            return fail(request, exc.message, status=400)

        if expected_hash and actual_hash and expected_hash != actual_hash:
            return fail(
                request, "file_changed_externally", status=409,
                current_hash=actual_hash,
            )

        validation = code_validator.validate_file(path, content)

        if not validation["valid"]:
            return fail(request, "validation_failed", status=422, validation=validation)

        try:
            result = workspace_service.write_file_atomic(root, path, content)
        except WorkspaceError as exc:
            return fail(request, exc.message, status=400)

        logger.info("[scaffold-ide] write user=%s root=%s path=%s", request.user, root, path)

        return ok(request, "File saved", status=200, validation=validation, **result)

    # -----------------------------------------------------
    # POST apply/  {files: [{root, path, content}]}
    # All-or-nothing: validates every file first, writes NONE if any fails.
    # -----------------------------------------------------
    @action(detail=False, methods=["post"])
    def apply(self, request):
        self._ensure_enabled(request)

        files = request.data.get("files") or []

        if not files:
            return fail(request, "No files to apply", status=400)

        validations = []
        for f in files:
            validation = code_validator.validate_file(f.get("path", ""), f.get("content", ""))
            validations.append({"path": f.get("path"), "root": f.get("root"), **validation})

        if any(not v["valid"] for v in validations):
            return fail(request, "validation_failed", status=422, files=validations)

        written = []
        try:
            for f in files:
                written.append(workspace_service.write_file_atomic(
                    f.get("root", ""), f.get("path", ""), f.get("content", ""),
                ))
        except WorkspaceError as exc:
            # Uma falha a meio (ex.: path inválido descoberto só agora)
            # não deve deixar os ficheiros ANTERIORES desta mesma
            # aplicação como único resultado parcial sem aviso - todos
            # os já validados acima eram válidos, por isso isto só
            # aconteceria por um erro de path/permissão do SO, não de
            # conteúdo; reportamos claramente o que ficou escrito.
            logger.error("[scaffold-ide] apply partial failure user=%s error=%s", request.user, exc.message)
            return fail(request, f"Applied {len(written)}/{len(files)} files before failing: {exc.message}", status=500)

        logger.info("[scaffold-ide] apply user=%s files=%s", request.user, [f.get("path") for f in files])

        return ok(request, f"{len(written)} files applied successfully", status=200, files=written, validations=validations)

    # -----------------------------------------------------
    # GET commands/  - safe command allowlist
    # -----------------------------------------------------
    @action(detail=False, methods=["get"])
    def commands(self, request):
        self._ensure_enabled(request)
        return all(request, commands=command_runner_service.list_commands())

    # -----------------------------------------------------
    # POST run/  {key}
    # -----------------------------------------------------
    @action(detail=False, methods=["post"])
    def run(self, request):
        self._ensure_enabled(request)
        key = request.data.get("key", "")

        result = command_runner_service.run_command(key)
        logger.info("[scaffold-ide] run user=%s key=%s ok=%s", request.user, key, result.get("ok"))

        return all(request, **result)

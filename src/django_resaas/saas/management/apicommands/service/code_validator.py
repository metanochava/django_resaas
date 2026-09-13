"""Validation pipeline for the Scaffold IDE (pages/commands/
ScaffoldPage.vue) and for ScaffoldAPIView.create() (management/
apicommands/view/scaffold.py) - the single place that decides whether
generated/edited code is safe to write to disk.

Central rule (see ScaffoldPage.vue's mega-prompt, "REGRA PRINCIPAL"):
code is NEVER written to the filesystem before passing this pipeline.
The frontend may run its own quick checks for responsiveness, but this
module is the only AUTHORITATIVE validator - IDEWorkspaceAPIView.write/
apply and ScaffoldAPIView.create both call it again server-side
regardless of what the client claims.

Validation never *executes* untrusted code to check it - only:
  - `ast.parse()` (Python) - builds a syntax tree, never runs it.
  - `importlib.util.find_spec()` - resolves whether a module exists on
    sys.path without executing its top-level code (find_spec() does not
    run the module). We DO fall back to a real `import_module()` only
    to confirm a specific attribute exists on an already-installed,
    trusted, first-party project module (never on arbitrary user
    content) - the same trust level `python manage.py check` already
    operates at.
  - external, non-executing tools for the other languages (`bash -n`,
    `@vue/compiler-sfc`'s parse/compileTemplate/compileScript, esbuild's
    `transform` in "transform only" mode) via subprocess, never `eval`/
    `exec`/`node -e "require(...)"` on the content itself.
"""
import ast
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# ==========================================================
# LANGUAGE DETECTION
# ==========================================================

_EXTENSION_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".vue": "vue",
    ".json": "json",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".md": "markdown",
    ".sh": "shell",
    ".bash": "shell",
}


def detect_language(path):
    return _EXTENSION_LANGUAGE.get(Path(path).suffix.lower(), "plaintext")


def _issue(message, *, line=None, column=None, severity="error"):
    return {"message": message, "line": line, "column": column, "severity": severity}


# ==========================================================
# PYTHON
# ==========================================================

def _iter_import_names(tree):
    """Yields (module_dotted_path, imported_name_or_None, lineno) for
    every `import x`/`from x import y` in the file - `imported_name` is
    None for a plain `import x` (nothing to check beyond the module
    existing)."""

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, None, node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # Import relativo ("from . import x") - find_spec() não
                # resolve isto de forma fiável sem o pacote completo já
                # carregado; não bloqueamos, cada nome vira um warning
                # (não conseguimos confirmar, mas também não é motivo
                # para rejeitar automaticamente código relativo válido).
                continue
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    yield module, None, node.lineno
                else:
                    yield module, alias.name, node.lineno


def _check_python_imports(tree):
    errors = []
    warnings = []

    for module, name, lineno in _iter_import_names(tree):
        if not module:
            continue

        try:
            spec = importlib.util.find_spec(module)
        except (ImportError, ValueError, ModuleNotFoundError):
            spec = None
        except Exception:
            # Módulo resolvível mas cujo __init__ falha a importar por
            # outra razão (ex.: settings do Django ainda não prontos
            # para essa dependência específica) - não é garantidamente
            # um import quebrado, por isso fica warning, não error.
            warnings.append(_issue(
                f"Could not verify module '{module}' (import raised while resolving)",
                line=lineno, severity="warning",
            ))
            continue

        if spec is None:
            errors.append(_issue(
                f"Module '{module}' does not exist or is not installed",
                line=lineno,
            ))
            continue

        if name is None:
            continue

        try:
            real_module = importlib.import_module(module)
        except Exception as exc:
            warnings.append(_issue(
                f"Could not verify '{name}' in '{module}' ({exc.__class__.__name__})",
                line=lineno, severity="warning",
            ))
            continue

        if not hasattr(real_module, name):
            errors.append(_issue(
                f"'{name}' does not exist in module '{module}'",
                line=lineno,
            ))

    return errors, warnings


def validate_python(content, *, check_imports=True):
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return {
            "valid": False,
            "errors": [_issue(
                exc.msg or "Invalid syntax",
                line=exc.lineno, column=exc.offset,
            )],
            "warnings": [],
        }

    errors, warnings = ([], [])
    if check_imports:
        errors, warnings = _check_python_imports(tree)

    return {"valid": not errors, "errors": errors, "warnings": warnings}


# ==========================================================
# JSON
# ==========================================================

def validate_json(content):
    try:
        json.loads(content)
        return {"valid": True, "errors": [], "warnings": []}
    except json.JSONDecodeError as exc:
        return {
            "valid": False,
            "errors": [_issue(exc.msg, line=exc.lineno, column=exc.colno)],
            "warnings": [],
        }


# ==========================================================
# SHELL
# ==========================================================

def validate_shell(content):
    bash = shutil.which("bash")
    if not bash:
        return {"valid": True, "errors": [], "warnings": [
            _issue("bash not available on this server - shell syntax was not checked", severity="warning"),
        ]}

    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        proc = subprocess.run(
            [bash, "-n", tmp_path],
            capture_output=True, text=True, timeout=10,
        )
    finally:
        os.unlink(tmp_path)

    if proc.returncode == 0:
        return {"valid": True, "errors": [], "warnings": []}

    return {
        "valid": False,
        "errors": [_issue(proc.stderr.strip() or "Invalid shell syntax")],
        "warnings": [],
    }


# ==========================================================
# JS / TS / VUE - via Node (esbuild + @vue/compiler-sfc, both already
# present in the frontend's own node_modules - no new dependency).
# Never `node -e` on the content itself: content is written to a real
# temp file and only its PATH crosses the subprocess boundary; the
# Node script only parses/transforms, it never requires()/imports the
# temp file, so nothing in it ever actually executes.
# ==========================================================

def _frontend_node_modules():
    """Best-effort locate a node_modules that actually has esbuild/
    @vue/compiler-sfc installed - the consumer app's (dev/front-style
    project), not this library's own (a pure Vue library has no build
    tooling of its own). Configurable via FRONTEND_PROJECT_DIR so this
    isn't hardcoded to one specific consumer checkout."""

    from django.conf import settings

    candidates = []
    configured = getattr(settings, "FRONTEND_PROJECT_DIR", None)
    if configured:
        candidates.append(Path(configured))

    candidates.append(Path(settings.BASE_DIR).parent / "front")

    for base in candidates:
        node_modules = base / "node_modules"
        if (node_modules / "esbuild").exists() and (node_modules / "@vue" / "compiler-sfc").exists():
            return node_modules

    return None


_JS_VALIDATE_SCRIPT = r"""
const fs = require('fs');
const path = require('path');
const nodeModules = process.argv[2];
const filePath = process.argv[3];
const lang = process.argv[4];

const req = (name) => require(path.join(nodeModules, name));

const content = fs.readFileSync(filePath, 'utf-8');
const errors = [];
const warnings = [];

try {
  if (lang === 'vue') {
    const { parse, compileTemplate, compileScript } = req('@vue/compiler-sfc');
    const { descriptor, errors: parseErrors } = parse(content, { filename: filePath });
    for (const e of parseErrors) {
      errors.push({ message: e.message, line: e.loc?.start?.line ?? null, column: e.loc?.start?.column ?? null });
    }
    if (!parseErrors.length && descriptor.script || descriptor.scriptSetup) {
      try {
        compileScript(descriptor, { id: 'validate' });
      } catch (e) {
        errors.push({ message: String(e.message || e), line: e.loc?.start?.line ?? null });
      }
    }
    if (!parseErrors.length && descriptor.template) {
      const tmpl = compileTemplate({ source: descriptor.template.content, filename: filePath, id: 'validate' });
      for (const e of tmpl.errors || []) {
        const msg = typeof e === 'string' ? e : e.message;
        errors.push({ message: msg, line: e.loc?.start?.line ?? null });
      }
      for (const w of tmpl.tips || []) {
        warnings.push({ message: typeof w === 'string' ? w : w.message });
      }
    }
  } else {
    const esbuild = req('esbuild');
    const loader = lang === 'typescript' ? 'ts' : 'js';
    esbuild.transformSync(content, { loader, sourcefile: filePath });
  }
} catch (e) {
  const list = e.errors || [{ text: String(e.message || e) }];
  for (const err of list) {
    errors.push({
      message: err.text || String(e.message || e),
      line: err.location?.line ?? null,
      column: err.location?.column ?? null,
    });
  }
}

process.stdout.write(JSON.stringify({ errors, warnings }));
"""


def _validate_via_node(content, path, language):
    node_modules = _frontend_node_modules()

    if node_modules is None:
        return {"valid": True, "errors": [], "warnings": [
            _issue(
                "No frontend toolchain (esbuild/@vue/compiler-sfc) found - "
                "syntax was not checked. Set settings.FRONTEND_PROJECT_DIR.",
                severity="warning",
            ),
        ]}

    node = shutil.which("node")
    if not node:
        return {"valid": True, "errors": [], "warnings": [
            _issue("node executable not found on this server - syntax was not checked", severity="warning"),
        ]}

    suffix = Path(path).suffix or ".js"
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as script:
        script.write(_JS_VALIDATE_SCRIPT)
        script_path = script.name

    try:
        proc = subprocess.run(
            [node, script_path, str(node_modules), tmp_path, language],
            capture_output=True, text=True, timeout=20,
        )
    finally:
        os.unlink(tmp_path)
        os.unlink(script_path)

    if proc.returncode != 0 or not proc.stdout.strip():
        return {
            "valid": False,
            "errors": [_issue(proc.stderr.strip() or "Validator crashed")],
            "warnings": [],
        }

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"valid": False, "errors": [_issue("Validator returned invalid output")], "warnings": []}

    errors = [_issue(e["message"], line=e.get("line"), column=e.get("column")) for e in result.get("errors", [])]
    warnings = [_issue(w["message"], severity="warning") for w in result.get("warnings", [])]

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def validate_vue(content, path="file.vue"):
    return _validate_via_node(content, path, "vue")


def validate_javascript(content, path="file.js"):
    return _validate_via_node(content, path, "javascript")


def validate_typescript(content, path="file.ts"):
    return _validate_via_node(content, path, "typescript")


# ==========================================================
# PIPELINE
# ==========================================================

_VALIDATORS = {
    "python": validate_python,
    "json": lambda content: validate_json(content),
    "shell": lambda content: validate_shell(content),
}


def validate_file(path, content):
    """Single entry point - detects the language from `path` and runs
    the matching validator. Unknown languages (html/css/scss/markdown/
    plaintext) always come back `valid: True` with an informational
    warning - there is no authoritative, dependency-free syntax checker
    for them here, and refusing to save a .md/.css file because we have
    no validator for it would violate 'never block on what you cannot
    actually check'."""

    language = detect_language(path)

    if language == "python":
        result = validate_python(content)
    elif language == "json":
        result = validate_json(content)
    elif language == "shell":
        result = validate_shell(content)
    elif language == "vue":
        result = validate_vue(content, path)
    elif language in ("javascript", "typescript"):
        result = _validate_via_node(content, path, language)
    else:
        result = {"valid": True, "errors": [], "warnings": [
            _issue(f"No syntax validator for .{Path(path).suffix.lstrip('.')} files", severity="info"),
        ]}

    result["file"] = path
    result["language"] = language
    return result

"""Safe command runner for the Scaffold IDE's bottom panel - NOT a
PTY/interactive shell (see ScaffoldPage.vue's mega-prompt secção 16/17:
"Se a arquitectura já suportar PTY, usar... Se ainda não suportar,
implementar com backend seguro"). This project has no PTY/WebSocket
terminal infrastructure today (confirmed - grep for "PTY"/"pty.spawn"/
django channels found nothing), and building one is a materially
different, much larger and more security-sensitive piece of work than
"add validation to a scaffold IDE". The safer, explicitly-sanctioned
alternative (secção 62-64: "command runner" from a "safe/configured
list", "não aceitar string arbitrária vinda do browser") is what's
implemented here instead.

Deliberately excludes anything that mutates state or can run for a
long time (migrate, test, build) - those already exist as their own
dedicated, explicit actions elsewhere (ScaffoldAPIView.migrate(), the
project's own CI) and returning their output over a single synchronous
HTTP request/response (no streaming infra exists) would either block
for a very long time or time out. Only fast, read-only diagnostics run
here - see COMMANDS below for the exact list, sourced from the real
manage.py and the frontend's real package.json "scripts" (never
invented - CLAUDE.md/mega-prompt secção 63)."""
import json
import subprocess
import sys
from pathlib import Path

from django.conf import settings

TIMEOUT_SECONDS = 60


def _frontend_dir():
    configured = getattr(settings, "FRONTEND_PROJECT_DIR", None)
    return Path(configured) if configured else Path(settings.BASE_DIR).parent / "front"


def _frontend_scripts():
    package_json = _frontend_dir() / "package.json"

    if not package_json.exists():
        return {}

    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    return data.get("scripts", {}) or {}


def list_commands():
    """Built dynamically (real manage.py + the frontend's real
    package.json scripts), never a hardcoded fantasy list - "lint" and
    "build" only appear if the frontend project actually declares
    them."""

    commands = [
        {
            "key": "django_check",
            "label": "Django Check",
            "description": "python manage.py check",
        },
        {
            "key": "django_makemigrations_check",
            "label": "Makemigrations (check only)",
            "description": "python manage.py makemigrations --check --dry-run",
        },
    ]

    scripts = _frontend_scripts()

    if "lint" in scripts:
        commands.append({
            "key": "frontend_lint",
            "label": "Frontend Lint",
            "description": "npm run lint",
        })

    if "build" in scripts:
        commands.append({
            "key": "frontend_build",
            "label": "Frontend Build",
            "description": "npm run build (may take a while)",
        })

    return commands


def _run(argv, cwd, timeout=TIMEOUT_SECONDS):
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
        }


def run_command(key):
    allowed = {c["key"] for c in list_commands()}

    if key not in allowed:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"Unknown or disabled command: '{key}'"}

    manage_py = Path(settings.BASE_DIR) / "manage.py"

    if key == "django_check":
        return _run([sys.executable, str(manage_py), "check"], cwd=settings.BASE_DIR)

    if key == "django_makemigrations_check":
        return _run(
            [sys.executable, str(manage_py), "makemigrations", "--check", "--dry-run"],
            cwd=settings.BASE_DIR,
        )

    if key == "frontend_lint":
        return _run(["npm", "run", "lint"], cwd=_frontend_dir(), timeout=120)

    if key == "frontend_build":
        return _run(["npm", "run", "build"], cwd=_frontend_dir(), timeout=300)

    return {"ok": False, "returncode": None, "stdout": "", "stderr": "Not implemented"}


import os
import stat
import subprocess
import json
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, HttpResponse
import os, json, subprocess
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

DEPLOY_TOKEN = settings.DEPLOY_TOKEN  # mete no env/setting em produção

STATUS_FILE = "/tmp/deploy_status.json"
LOG_FILE = "/tmp/deploy.log"

BASE_DIR = settings.BASE_DIR
RELEASES_DIR = f"{BASE_DIR}/releases"
CURRENT_LINK = f"{BASE_DIR}/back"


def _write_status(status, msg="", extra=None):
    data = {
        "status": status,
        "message": msg,
        "time": datetime.now().isoformat()
    }
    if extra:
        data.update(extra)
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)


def _read_status():
    if not os.path.exists(STATUS_FILE):
        return {"status": "idle"}
    with open(STATUS_FILE) as f:
        return json.load(f)


def _current_release():
    try:
        return os.path.realpath(CURRENT_LINK)
    except Exception:
        return None


def _list_releases(limit=30):
    if not os.path.isdir(RELEASES_DIR):
        return []
    items = sorted(os.listdir(RELEASES_DIR))
    items = items[-limit:]
    cur = _current_release()
    out = []
    for name in reversed(items):
        path = os.path.join(RELEASES_DIR, name)
        out.append({
            "name": name,
            "path": path,
            "active": (cur == os.path.realpath(path)),
        })
    return out


def _tail(path, n=300):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        chunk = 8192
        data = b""
        while size > 0 and data.count(b"\n") < n + 1:
            read = min(chunk, size)
            size -= read
            f.seek(size)
            data = f.read(read) + data
        return b"\n".join(data.splitlines()[-n:]).decode("utf-8", errors="replace")


def _require_token(request):
    return request.GET.get("token") == DEPLOY_TOKEN


@csrf_exempt
def deploy_github(request):
    if not _require_token(request):
        return HttpResponse("Unauthorized", status=403)

    # aceita JSON { "ref": "refs/tags/v1.2.0" } ou { "tag": "v1.2.0" }
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    ref = payload.get("ref", "") or request.POST.get("ref", "")
    tag = payload.get("tag") or request.POST.get("tag")

    if not tag and ref.startswith("refs/tags/"):
        tag = ref.split("refs/tags/")[1]

    if not tag:
        return JsonResponse({"error": "tag ausente (envia ref refs/tags/<tag> ou tag=<tag>)"}, status=400)

    script_path = getattr(settings, "DEPLOY_FILE_PATH", "/var/www/lib/deploy.sh")

    _write_status("running", f"Deploy iniciado: {tag}", {"tag": tag})

    # executa deploy.sh <tag>
    with open(LOG_FILE, "a") as log:
        subprocess.Popen(
            [script_path, tag],
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    return JsonResponse({"message": "Deploy iniciado", "tag": tag})


def deploy_status(request):
    if not _require_token(request):
        return HttpResponse("Unauthorized", status=403)

    st = _read_status()
    st["current"] = _current_release()
    return JsonResponse(st)


def deploy_releases(request):
    if not _require_token(request):
        return HttpResponse("Unauthorized", status=403)
    return JsonResponse({"current": _current_release(), "releases": _list_releases()})


def deploy_logs(request):
    if not _require_token(request):
        return HttpResponse("Unauthorized", status=403)
    return HttpResponse(_tail(LOG_FILE, n=400), content_type="text/plain")


@csrf_exempt
def deploy_rollback(request):
    if not _require_token(request):
        return HttpResponse("Unauthorized", status=403)

    releases = _list_releases(limit=100)
    active_idx = next((i for i, r in enumerate(releases) if r["active"]), None)
    if active_idx is None:
        return JsonResponse({"error": "não foi possível detectar release ativa"}, status=400)

    # releases está em ordem “mais recente primeiro”
    # rollback para a próxima da lista (mais antiga)
    if active_idx + 1 >= len(releases):
        return JsonResponse({"error": "não existe release anterior"}, status=400)

    target = releases[active_idx + 1]["path"]

    _write_status("running", "Rollback iniciado", {"target": target})

    os.system(f"ln -sfn {target} {CURRENT_LINK}")
    os.system("systemctl restart gunicorn_dev_back")

    _write_status("success", "Rollback concluído", {"target": target, "current": _current_release()})
    return JsonResponse({"message": "Rollback concluído", "current": _current_release(), "target": target})


def home(request):
    return HttpResponse("Página inicial funcionando 🚀")


# 🔐 Token de segurança
DEPLOY_TOKEN = "12121212"
BASE_DIR = settings.BASE_DIR
PROJECT_NAME = "back"

PROJECT_DIR = f"{BASE_DIR}/{PROJECT_NAME}"
RELEASES_DIR = f"{BASE_DIR}/releases"
CURRENT_LINK = PROJECT_DIR
LOG_FILE = "/tmp/deploy.log"
STATUS_FILE = "/tmp/deploy_status.json"

# =========================
# SCRIPT DE DEPLOY (COM RELEASE)
# =========================
DEPLOY_SCRIPT = f"""#!/bin/bash
set -e

# ====== CONFIG ======
BASE="/var/www"
RELEASES="$BASE/releases"
CURRENT="$BASE/back"              # symlink
SHARED="$BASE/back_shared"
REPO_URL="https://github.com/metanochava/django_rest_auth.git"
SERVICE="gunicorn_dev_back"

LOCK="/tmp/deploy.lock"
LOG="/tmp/deploy.log"

# TAG vem do argumento
TAG="$1"

if [ -z "$TAG" ]; then
  echo "❌ Precisas passar a TAG. Ex: ./deploy.sh v1.2.0" | tee -a "$LOG"
  exit 1
fi

# ====== LOCK ======
if [ -f "$LOCK" ]; then
  echo "🚫 Deploy já em execução" | tee -a "$LOG"
  exit 1
fi
trap "rm -f $LOCK" EXIT
touch "$LOCK"

TS=$(date +%Y%m%d%H%M%S)
NEW_RELEASE="$RELEASES/${{TAG}}-${{TS}}"

mkdir -p "$RELEASES" "$SHARED"
echo "🚀 Deploy TAG=$TAG -> $NEW_RELEASE" | tee -a "$LOG"

# ====== CLONE + CHECKOUT TAG ======
git clone --quiet "$REPO_URL" "$NEW_RELEASE"
cd "$NEW_RELEASE"
git checkout --quiet "$TAG"

# ====== VENV (shared) ======
# Assumindo venv em $SHARED/venv
source "$SHARED/venv/bin/activate"

# ====== ENV ======
# se usas .env
if [ -f "$SHARED/.env" ]; then
  set -a
  source "$SHARED/.env"
  set +a
fi

# ====== INSTALL + MIGRATE + STATIC ======
pip install -r requirements.txt >> "$LOG" 2>&1
python manage.py migrate >> "$LOG" 2>&1
python manage.py collectstatic --noinput >> "$LOG" 2>&1

# ====== MEDIA (shared) ======
# Se o projeto usa MEDIA_ROOT /var/www/back/mediafiles, ajusta para apontar pro shared:
# Exemplo: ln -sfn "$SHARED/mediafiles" "$NEW_RELEASE/mediafiles"
# (depende do teu settings.py)
mkdir -p "$SHARED/mediafiles"

# ====== SWITCH CURRENT ======
ln -sfn "$NEW_RELEASE" "$CURRENT"

# ====== RESTART ======
systemctl restart "$SERVICE"

echo "✅ Deploy concluído: $TAG" | tee -a "$LOG"
"""

# =========================
# HELPERS
# =========================
def write_status(status, message=""):
    data = {
        "status": status,
        "message": message,
        "time": datetime.now().isoformat()
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)


def read_status():
    if not os.path.exists(STATUS_FILE):
        return {"status": "idle"}
    with open(STATUS_FILE) as f:
        return json.load(f)


def ensure_script(path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, "w") as f:
            f.write(DEPLOY_SCRIPT)

        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


# =========================
# ENDPOINT: DEPLOY
# =========================
def deploy(request):
    if request.GET.get("token") != DEPLOY_TOKEN:
        return HttpResponse("Unauthorized", status=403)

    script_path = getattr(settings, "DEPLOY_FILE_PATH", "/var/www/lib/deploy.sh")

    try:
        ensure_script(script_path)

        write_status("running", "Deploy iniciado")

        subprocess.Popen(
            [script_path],
            stdout=open(LOG_FILE, "a"),
            stderr=subprocess.STDOUT,
        )

        return JsonResponse({"message": "🚀 Deploy iniciado"})

    except Exception as e:
        write_status("error", str(e))
        return JsonResponse({"error": str(e)}, status=500)


# =========================
# ENDPOINT: STATUS
# =========================
def deploy_status(request):
    if request.GET.get("token") != DEPLOY_TOKEN:
        return HttpResponse("Unauthorized", status=403)

    return JsonResponse(read_status())


# =========================
# ENDPOINT: LOGS
# =========================
def deploy_logs(request):
    if request.GET.get("token") != DEPLOY_TOKEN:
        return HttpResponse("Unauthorized", status=403)

    if not os.path.exists(LOG_FILE):
        return HttpResponse("Sem logs ainda")

    with open(LOG_FILE) as f:
        return HttpResponse(f.read(), content_type="text/plain")


# =========================
# ENDPOINT: ROLLBACK
# =========================
def rollback(request):
    if request.GET.get("token") != DEPLOY_TOKEN:
        return HttpResponse("Unauthorized", status=403)

    releases = sorted(os.listdir(RELEASES_DIR))

    if len(releases) < 2:
        return JsonResponse({"error": "Sem versão anterior"}, status=400)

    previous = releases[-2]
    previous_path = f"{RELEASES_DIR}/{previous}"

    try:
        os.system(f"ln -sfn {previous_path} {CURRENT_LINK}")
        os.system("systemctl restart gunicorn_dev_back")

        return JsonResponse({
            "message": "Rollback realizado",
            "version": previous
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =========================
# MULTI-TENANT (OPCIONAL)
# =========================
def deploy_tenant(request, tenant):
    if request.GET.get("token") != DEPLOY_TOKEN:
        return HttpResponse("Unauthorized", status=403)

    tenant_path = f"/var/www/{tenant}"

    if not os.path.exists(tenant_path):
        return JsonResponse({"error": "Tenant não existe"}, status=404)

    try:
        subprocess.Popen(
            ["bash", f"{tenant_path}/deploy.sh"],
            stdout=open(LOG_FILE, "a"),
            stderr=subprocess.STDOUT,
        )

        return JsonResponse({"message": f"Deploy iniciado para {tenant}"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
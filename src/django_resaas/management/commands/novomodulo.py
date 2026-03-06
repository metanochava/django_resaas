import os
import re
from pathlib import Path
from django.conf import settings
from django.core.management.base import CommandError


class ModuleScaffoldService:

    TEMPLATE = {
        "models": ["__init__.py"],
        "serializers": ["__init__.py"],
        "views": ["__init__.py"],
        "services": ["__init__.py"],
        "migrations": ["__init__.py"],
        "lang": ["ptpt.py", "enus.py"],
    }

    # =========================
    # PUBLIC
    # =========================
    @classmethod
    def create(cls, name: str):

        name = cls.clean(name)

        base = Path(settings.BASE_DIR)
        module_path = base / name

        if module_path.exists():
            raise CommandError(f"Módulo '{name}' já existe")

        module_path.mkdir()

        # pastas
        for folder, files in cls.TEMPLATE.items():
            p = module_path / folder
            p.mkdir(parents=True)

            for f in files:
                (p / f).touch()

        cls._create_apps(name, module_path)
        cls._create_urls(module_path)
        cls._create_sidebar(name, module_path)
        cls._add_to_settings(name)

        return str(module_path)

    # =========================

    @staticmethod
    def clean(value):
        return re.sub(r"[^a-zA-Z0-9_]", "", value)

    # =========================

    @staticmethod
    def _create_apps(name, path):
        (path / "apps.py").write_text(f"""
from django.apps import AppConfig

class {name.title()}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '{name}'
""")

    @staticmethod
    def _create_urls(path):
        (path / "urls.py").write_text("""
from django.urls import path, include
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
]
""")

    @staticmethod
    def _create_sidebar(name, path):
        (path / "sidebar.py").write_text(f"""
MENU = "{name}"
ICON = "menu"
SUBMENUS = []
""")

    # =========================
    # settings MY_APPS
    # =========================

    @staticmethod
    def _add_to_settings(app_name):
        settings_file = Path.cwd() / "src/dev/settings.py"

        text = settings_file.read_text()

        pattern = r"MY_APPS\s*=\s*\[[\s\S]*?\]"
        match = re.search(pattern, text)

        if not match:
            raise CommandError("MY_APPS não encontrado")

        block = match.group(0)

        if app_name in block:
            return

        new_block = block[:-1] + f"    '{app_name}',\n]"
        settings_file.write_text(text.replace(block, new_block))

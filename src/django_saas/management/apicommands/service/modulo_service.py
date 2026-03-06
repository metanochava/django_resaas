import os
import re
from pathlib import Path
from django.conf import settings
from django.core.management.base import CommandError
from django_saas.core.utils import clean_name, clean_class_name, clean_file_name
from django_saas.models.tipo_entidade import TipoEntidade
from django_saas.models.entidade import Entidade
from django_saas.models.modulo import Modulo
from django_saas.models.tipo_entidade_modulo import TipoEntidadeModulo
from django_saas.models.entidade_modulo import EntidadeModulo
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType


class ModuloScaffoldService:

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
        name = name.lower()

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

        p = module_path / 'templates' / name
        p.mkdir(parents=True)

        (module_path / "__init__.py").write_text(f"""default_app_config = "{clean_file_name(name)}.apps.RhConfig"\n 
        """)

        cls._create_apps(name, module_path)
        cls._create_urls(module_path)
        cls._create_sidebar(name, module_path)
        cls._create_admin(name, module_path)
        cls._add_to_settings(name)
        cls._alocate_modulo(name)

        

        return str(module_path)

    # =========================

    @staticmethod
    def clean(value):
        return re.sub(r"[^a-zA-Z0-9_]", "", value)

    # =========================

    @staticmethod
    def _create_apps(name, path):
        (path / "apps.py").write_text(f"""
import pkgutil
import importlib
from django.apps import AppConfig

class {name.title()}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = '{clean_file_name(name)}'
    def ready(self):
        import {clean_file_name(name)}.views

        for _, module_name, _ in pkgutil.iter_modules({clean_file_name(name)}.views.__path__):
            importlib.import_module(f"{clean_file_name(name)}.views.{{module_name}}")
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
    def _create_admin(name, path):
        (path / "admin.py").write_text(f"""
from django_saas.core.base.admin import BaseAdmin
from django.contrib import admin

admin.site.site_title = '{clean_name(name)}'
admin.site.index_title = '{clean_name(name)}'

def all_fields(model):
    return [field.name for field in model._meta.fields]

""")

    @staticmethod
    def _alocate_modulo(name):
        tipo_entidade, _ = TipoEntidade.objects.get_or_create(
            nome='SaaS',
            defaults={"estado": 1}
        )

        entidade, _ = Entidade.objects.get_or_create(
            nome="Mytech",
            tipo_entidade=tipo_entidade
        )
        
        modulo, _ = Modulo.objects.get_or_create(
            nome=name,
            defaults={"estado": 1}
        )

        tipo_entidade_modulo, _ = TipoEntidadeModulo.objects.get_or_create(
            modulo=modulo,
            tipo_entidade=tipo_entidade,
            defaults={"estado": 1}
        )

        entidade_modulo, _ = EntidadeModulo.objects.get_or_create(
            modulo=modulo,
            entidade=entidade,
            defaults={"estado": 1}
        )

        
        ct, _ = ContentType.objects.get_or_create(
            app_label=name,
            model="sidebar",
        )

        admin_group, _ = Group.objects.get_or_create(name="SuperAdmin")
        perm, _ = Permission.objects.get_or_create(
            codename=f"view_{clean_file_name(name)}_dashboard",
            content_type=ct,
            defaults={"name": f"Can view {clean_file_name(name)} dashboard"},
        )

        admin_group.permissions.add(perm)


    @staticmethod
    def _create_sidebar(name, path):
        (path / "sidebar.py").write_text(f"""
MENU = "{clean_class_name(name)}"
ICON = "menu"
SUBMENUS = [
    {{
        "menu": "Dashboard",
        "icon": "dashboard",
        "role": "view_{clean_file_name(name)}_dashboard",
        "rota": "view_{clean_file_name(name)}_dashboard",
    }},
]
""")

    # =========================
    # settings MY_APPS
    # =========================




    @staticmethod
    def _add_to_settings(app_name: str):

        module_path = Path(*settings.SETTINGS_MODULE.split(".")).with_suffix(".py")
        settings_file = Path(settings.BASE_DIR) / module_path

        text = settings_file.read_text(encoding="utf-8")

        pattern = r"MY_APPS\s*=\s*\[[\s\S]*?\]"
        match = re.search(pattern, text)

        if not match:
            raise CommandError("MY_APPS não encontrado")

        block = match.group(0)

        # evitar duplicar
        if re.search(rf"['\"]{re.escape(app_name)}['\"]", block):
            return

        # adiciona antes do ]
        new_block = re.sub(
            r"\]",
            f"    '{app_name}',\n]",
            block
        )

        settings_file.write_text(text.replace(block, new_block), encoding="utf-8")


    
    @staticmethod
    def _remove_from_settings(app_name: str):

        module_path = Path(*settings.SETTINGS_MODULE.split(".")).with_suffix(".py")
        settings_file = Path(settings.BASE_DIR) / module_path

        text = settings_file.read_text(encoding="utf-8")

        pattern = r"MY_APPS\s*=\s*\[[\s\S]*?\]"
        match = re.search(pattern, text)

        if not match:
            return

        block = match.group(0)
        app_escaped = re.escape(app_name)

        # remove linha do app (qualquer posição)
        new_block = re.sub(
            rf"""
            ^[ \t]*['"]{app_escaped}['"][ \t]*,?[ \t]*(?:\#.*)?\r?\n?
            """,
            "",
            block,
            flags=re.MULTILINE | re.VERBOSE
        )

        # limpa vírgula antes do ]
        new_block = re.sub(r"\s*\]", "\n]", new_block)

        settings_file.write_text(text.replace(block, new_block), encoding="utf-8")

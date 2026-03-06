import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

# =========================================================
import sys
import importlib
from django.apps import apps

import time

from importlib import import_module
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command

from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action

from django_saas.models.modelo_extra import ModeloExtra
from django_saas.core.base.views import register_view
from django_saas.core.utils import all, ok, fail, warn, clean_class_name, clean_file_name, safe_write

import importlib.util
import importlib
import pprint
from io import StringIO


# =========================================================
# HELPERS
# =========================================================

BASE_DIR = Path(settings.BASE_DIR)


def module_path(m): return BASE_DIR / m
def models_dir(m): return module_path(m) / "models"
def serializers_dir(m): return module_path(m) / "serializers"
def views_dir(m): return module_path(m) / "views"
def services_dir(m): return module_path(m) / "services"


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# =========================================================
# DATACLASS

def reload_app_models(app_label):
    importlib.invalidate_caches()

    # reload rh.models (para executar o __init__.py novo)
    mod = f"{app_label}.models"

    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
    else:
        importlib.import_module(mod)

    # força Django a reler models
    app_config = apps.get_app_config(app_label)
    apps.clear_cache()
    app_config.import_models()


@dataclass
class Field:
    name: str = ""
    type: str = ""
    required: bool = True
    unique: bool = False
    default: Any = None
    verbose_name: str | None = None
    help_text: str | None = None

    max_length: int | None = None
    min_length: int | None = None

    min: float | None = None
    max: float | None = None

    max_digits: int | None = None
    decimal_places: int | None = None

    relation: str | None = None
    on_delete: str | None = None

    upload_to: str | None = None
    choices: list | None = None

    auto_now_add:str | None=None
    auto_now:str | None=None

    height_field:int | None=None
    width_field:int | None=None
    default_currency:str | None=None
    


# =========================================================
# CODEGEN
# =========================================================

def build_model(module, model, fields, extra_perms):

    lines = [
        "from django.db import models",
        "from django_saas.core.base.models import BaseModel",
        "from django_saas.core.utils import guess_name",
        '',
        f"class {model}(BaseModel):",
    ]

    for f in fields:
        opts = []
        
        if f.verbose_name:
            opts.append(f'verbose_name="{f.verbose_name}"')
        if f.help_text:
            opts.append(f'help_text="{f.help_text}"')
        if not f.required:
            opts.append("blank=True")
            opts.append("null=True")
        if f.unique:
            opts.append("unique=True")
        if f.default not in [None, ""]:
                        opts.append(f"""default={ int(f.default) if f.type in ['DecimalField', 'IntegerField', 'BigIntegerField', 'FloatField'] else repr(f.default)}""") 

        if f.min_length:
            opts.append(f"min_length={f.min_length}")
        if f.max_length:
            opts.append(f"max_length={f.max_length}")
        if f.min:
            opts.append(f"min={f.min}")
        if f.max:
            opts.append(f"max={f.max}")
        if f.auto_now_add:
            opts.append(f"auto_now_add={f.auto_now_add}")
        if f.auto_now:
            opts.append(f"auto_now={f.auto_now}")
        if f.height_field:
            opts.append(f"height_field={f.height_field}")
        if f.width_field:
            opts.append(f"width_field={f.width_field}")
        if f.default_currency:
            opts.append(f"default_currency={f.default_currency}")

        max_digits = 10
        decimal_places = 2
        if f.decimal_places:
            decimal_places = f.decimal_places
        if f.max_digits:
            max_digits = f.max_digits

        if f.type == "DecimalField":
            opts.append(f"max_digits={max_digits}")
            opts.append(f"decimal_places={decimal_places}")

        if f.type == "MoneyField":
            if f.default_currency:
                opts.append(f"default_currency={f.default_currency}")
            else:
                opts.append(f"default_currency='MZN'")

            if lines[0] != "from djmoney.models.fields import MoneyField":
                lines.insert(0, "from djmoney.models.fields import MoneyField")


        if f.type in ["ImageField", "FileField"]:
            opts.append(f'upload_to=file_path')
            
        if f.choices:
            choices = [
                (int(c["key"]) if f.type in ["DecimalField", "IntegerField", "BigIntegerField", "FloatField"] else str(c["key"]), c["label"])
                for c in f.choices
            ]
            opts.append(f'choices={choices}')
        

        # RELATION
        if f.type in ["ForeignKey", "OneToOneField"]:
            rel = f"{f.relation}"
            opts.insert(0, f"on_delete=models.{f.on_delete or 'CASCADE'}")
            opts.insert(0, f"'{rel}'")

        if f.type == "ManyToManyField":
            rel = f"{f.relation}"
            opts.insert(0, f"'{rel}'")

        if f.type == "MoneyField":
            lines.append(
                f"    {f.name.lower()} = {f.type}({', '.join(opts)})"
            )
        else:
            lines.append(
                f"    {f.name.lower()} = models.{f.type}({', '.join(opts)})"
            )

    # META PERMS
    if extra_perms:
        lines.append("")
        lines.append("    class Meta:")
        lines.append("        permissions = [")
        for p in extra_perms:
            lines.append(f'            ("{p}", "Can {p} {model}"),')
        lines.append("        ]")

    lines.append(f"""
    def __str__(self):
        return f'{{guess_name(self)}}'
    """)

    


    if f.type in ["ImageField", "FileField"]:  
        lines.append(f"""
def file_path(instance, file_name):
    return f"{{instance.entidade.tipo_entidade.nome}}/{{instance.entidade.nome}}/{{file_name}}"
    """)

    return "\n".join(lines)


def build_serializer(module, model, fields):
    imports = [
        "from django_saas.core.base.serializers import BaseSerializer",
        f"from {module}.models.{clean_file_name(model)} import {model}",
        "from rest_framework import serializers",
    ]

    nested_imports = []
    serializer_fields = []

    for f in fields:
        if "relation" in f:
            rel_module, rel_model = f["relation"].split(".")

            if rel_module.startswith('django_saas'):
                nested_imports.append(f"from {rel_module}.models.{clean_file_name(rel_model)} import {rel_model}")
                nested_imports.append(f"from {rel_module}.data.{clean_file_name(rel_model)}.serializers.{clean_file_name(rel_model)} import {rel_model}Serializer")
            else: 
                nested_imports.append(f"from {rel_module}.models.{clean_file_name(rel_model)} import {rel_model}")
                nested_imports.append(f"from {rel_module}.serializers.{clean_file_name(rel_model)} import {rel_model}Serializer")

            # FK / OneToOne
            if f["type"] in ["ForeignKey", "OneToOneField"]:
                serializer_fields.append(
                    f"""    
    {f['name']}_id = serializers.PrimaryKeyRelatedField(
        source="{f['name']}", queryset={rel_model}.objects.all(), write_only=True
    )"""
                )
                serializer_fields.append(
                    f"    {f['name']} = {rel_model}Serializer(read_only=True)"
                )

            # ManyToMany
            elif f["type"] == "ManyToManyField":
                serializer_fields.append(
                    f"""    
    {f['name']}_ids = serializers.PrimaryKeyRelatedField(
        source="{f['name']}", queryset={rel_model}.objects.all(), many=True, write_only=True
    ) """
                )
                serializer_fields.append(
                    f"    {f['name']} = {rel_model}Serializer(many=True, read_only=True)"
                )

    # remove duplicados
    imports += list(set(nested_imports))

    # montar conteúdo
    content = "\n".join(imports) + f"""

class {model}Serializer(BaseSerializer):
    """
    for line in serializer_fields:
        content += line + "\n"

    content += f"""
    class Meta:
        model = {model}
        fields = "__all__"
    """
    return content



def build_view(module, model):
    return f"""
from django_saas.core.base.views import BaseAPIView
from django_saas.core.base.views import register_view
from {module}.models.{clean_file_name(model)} import {clean_class_name(model)}
from {module}.serializers.{clean_file_name(model)} import {clean_class_name(model)}Serializer


@register_view('{clean_file_name(model)}s')
class {model}APIView(BaseAPIView):
    queryset = {clean_class_name(model)}.objects.all()   
    serializer_class = {clean_class_name(model)}Serializer
    
"""


# =========================================================
# PERMISSIONS
# =========================================================

def ensure_permissions(module, model, extras):

    Model = apps.get_model(module, model)
    ct = ContentType.objects.get_for_model(Model)
    modelo = model
    model = model.lower()
    defaults = []

    perms = defaults + extras

    ModeloExtra.objects.filter(modelo=modelo).delete()

    for p in perms:
        # p = {'method': 'get', 'permission': 'pdf', 'url': '', 'details': True}
        ModeloExtra.objects.get_or_create(
            modelo=modelo,
            icon=p['icon'],
            method=p['method'],
            permission=p['permission'],
            url=p['url'],
            details=p['details']
        )
        Permission.objects.get_or_create(
            codename=f"{p['method']}_{p['permission']}_{model}",
            content_type=ct,
            defaults={"name": f"Can {p['method']}_{p['permission']} {model}"}
        )

    group, _ = Group.objects.get_or_create(name="SuperAdmin")
    group.permissions.add(*Permission.objects.filter(content_type=ct))


def update_admin(module, name, dry_run=False):
    admin_file = os.path.join(BASE_DIR, module, "admin.py")
    line = f"from {module}.models.{clean_file_name(name)} import {name}"

    content_admin = f"""{line}
@admin.register({name})
class {name}Admin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display = ("id",)\n
"""

    if not dry_run:
        if os.path.exists(admin_file):
            with open(admin_file, "r") as f:
                content = f.read()
            if line in content:
                return
        safe_write(admin_file, content_admin, "a")
    return



def update_sidebar( module, model_name, icon = 'list', crud=False,  dry_run=False):
    sidebar_file = Path(module_path(module)) / "sidebar.py"

    # se não existir simplesmente ignora (não é erro crítico)
    if not sidebar_file.exists():
        return None

    # importar sidebar dinamicamente
    spec = importlib.util.spec_from_file_location(
        f"{module}_sidebar",
        sidebar_file
    )
    sidebar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sidebar)

    menu_name = model_name

    new_item = {
        "icon": icon,
        "menu": menu_name,
        "role": f"list_{menu_name.lower()}",
        "rota": f"list_{menu_name.lower()}",
        "add_role": f"add_{menu_name.lower()}",
        "add_rota": f"add_{menu_name.lower()}",
    }
    if crud:
        new_item['crud'] =  dict(module=module.lower(), model=model_name)

    # evitar duplicado
    if any(x["menu"] == menu_name for x in sidebar.SUBMENUS):
        return None

    sidebar.SUBMENUS.append(new_item)

    content = f'''
MENU = "{sidebar.MENU}"
ICON = "{sidebar.ICON}"

SUBMENUS = {pprint.pformat(sidebar.SUBMENUS, indent=4, width=120)}
'''

    formatted = write_python_pretty(content)

    if not dry_run:
        safe_write(str(sidebar_file), formatted)

    return str(sidebar_file)


def write_python_pretty(code: str) -> str:
    import black
    return black.format_str(code, mode=black.FileMode())


# =========================================================
# VIEWSET
# =========================================================

@register_view("scaffold", "django_saas")
class ScaffoldAPIView(ViewSet):

    permission_classes = [IsAdminUser]

    # -----------------------------------------------------
    # LIST (GET) -> usa all()
    # -----------------------------------------------------
    def list(self, request):
        return all(request, message="scaffold_ready")

    # -----------------------------------------------------
    # PREVIEW
    # -----------------------------------------------------
    @action(detail=False, methods=["post"])
    def preview(self, request):

        module = (request.data.get("modulo") or "").strip()
        model  = clean_class_name(request.data.get("modelo") or "").strip()
        fields = request.data.get("fields", [])
        perms  = request.data.get("permissions", [])

        if not module or not model:
            return fail(request, "Nome do módulo ou modelo não po-de estar vazio!")
        if not fields:
            return fail(request, "Tem de ter pelo menos um campo para criar Modelo")
        
        for f in fields:
            if f['name'] == '':
                return fail(request, "Ha campo sem atributo nome.<br> Melhor verificar")
            if f['type'] == '':
                return fail(request, "O campo <b>"+ f['name'] + "</b> esta sem atributo tipo de dado.<br> Melhor Colocar. ")

            if f['choices']:
                if not 'default' in f:
                    return fail(request, "O campo <b>"+ f['name'] + "</b> tem opcoes.<br>  Nessa ordem eh nessecario colocar uma opcao por defeito")



        fobjs = [Field(**f) for f in fields]

        return all(
            request,
            model=build_model(module, model, fobjs, perms),
            serializer=build_serializer(module, model, fields),
            view=build_view(module, model),
        )

    # -----------------------------------------------------
    # CREATE / UPDATE
    # -----------------------------------------------------

    def update_models_init(self, module_path, model_name):

        init_file = os.path.join(BASE_DIR, module_path, "models", "__init__.py")

        line = f"from {module_path}.models.{clean_file_name(model_name)} import {model_name}\n"
        # line = f"from .{clean_file_name(model_name)} import *\n"

        if os.path.exists(init_file):
            with open(init_file, "r") as f:
                content = f.read()

            if line not in content:
                with open(init_file, "a") as f:
                    f.write(line)
        else:
            with open(init_file, "w") as f:
                f.write(line)

    def create(self, request):

        module = (request.data.get("modulo") or "").strip()
        icon = (request.data.get("icon") or "list").strip()
        crud = request.data.get("crud") or False
        model  = clean_class_name(request.data.get("modelo") or "").strip()
        fields = request.data.get("fields", [])
        perms  = request.data.get("permissions", [])

        if not module or not model:
            return fail(request, "Nome do módulo ou modelo não pode estar vazio!")
        if not fields:
            return fail(request, "Tem de ter pelo menos um campo para criar Modelo")

        for f in fields:
            if f['name'] == '':
                return fail(request, "Ha campo sem atributo nome.<br> Melhor verificar")
            if f['type'] == '':
                return fail(request, "O campo <b>"+ f['name'] + "</b> esta sem atributo tipo de dado.<br> Melhor Colocar. ")


        fobjs = [Field(**f) for f in fields]

        write_file(models_dir(module)/f"{clean_file_name(model)}.py",
                   build_model(module, model, fobjs, perms))

        write_file(serializers_dir(module)/f"{clean_file_name(model)}.py",
                   build_serializer(module, model, fields))


        write_file(views_dir(module)/f"{clean_file_name(model)}.py",
                   build_view(module, model))

        update_sidebar(module, model, icon, crud)
        update_admin(module, model)
        self.update_models_init(module, model)
        reload_app_models(module)
        
        return ok(request, 'Modelo Criado com sucesso', status=201, out='migrate')

    @action(detail=False, methods=["post"])
    def migrate(self, request):
        module = (request.data.get("modulo") or "").strip()
        out = StringIO()
       
        call_command("makemigrations", module, stdout=out)
        call_command("migrate", stdout=out)
        
        return ok(request, 'Migracoes feitas com sucesso', status=201, out= out.getvalue()+'.')
    
    @action(detail=False, methods=["post"])
    def permissions(self, request):
        module = (request.data.get("modulo") or "").strip()
        model  = clean_class_name(request.data.get("modelo") or "").strip()
        perms = request.data.get("actions")

        print(module, model, perms)

        ensure_permissions(module, model, perms)
        
        return ok(request, 'Permicoes actualizadas', status=201)


    # @action(detail=True, methods=["get"], url_path=r"(?P<model>[^/.]+)/migrate")
    # def model_schema(self, request, pk=None, model=None):
    #     print(pk, model)
    #     out = StringIO()
    #     sms = ''
    #     try:
    #         print('Criar  migracoes')
    #         call_command("makemigrations", module, stdout=out)
    #         print('Migracoes feitas')
    #         call_command("migrate", stdout=out)
    #         print('Migrado')
    #     except Exception as e:
    #         sms = e.message

    #     if out.getvalue() == '':
    #         sms = 'Migracoes nao feitas'

    #     reload_app_models(module)
    #     ensure_permissions(module, model, perms)
        
    #     return ok(request, 'Modelo Criado com sucesso', status=201, out= out.getvalue()+ sms)


    # -----------------------------------------------------
    # UPDATE
    # -----------------------------------------------------
    def update(self, request, pk=None):
        return self.create(request)

    # -----------------------------------------------------
    # DELETE
    # -----------------------------------------------------
    def destroy(self, request, pk=None):

        module, model = pk.split(".")

        for path in [
            models_dir(module)/f"{clean_file_name(model)}.py",
            serializers_dir(module)/f"{clean_file_name(model)}.py",
            views_dir(module)/f"{clean_file_name(model)}.py",
        ]:
            if path.exists():
                path.unlink()

        out = StringIO()

        call_command("makemigrations", module, stdout=out)
        call_command("migrate", stdout=out)

        return ok(request, status=204, out= out.getvalue())

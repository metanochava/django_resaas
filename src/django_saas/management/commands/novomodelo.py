# django_saas/management/commands/novomodelo.py

import os
from django.core.management.base import BaseCommand
from django.conf import settings
import importlib.util
from pathlib import Path
import pprint

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
import pkgutil
import importlib
import questionary
from rich.console import Console
from rich.table import Table
from django.core.management import call_command
from django_saas.core.utils.safe_write import safe_write

BASE_MODULES_PATH = settings.BASE_DIR



class Command(BaseCommand):
    help = "Cria um novo modelo em qualquer módulo (rh, finance, crm...)"

    def grant_admin_permissions(self, model):
        content_type = ContentType.objects.get_for_model(model)
        perms = Permission.objects.filter(content_type=content_type)

        group, _ = Group.objects.get_or_create(name="SuperAdmin")
        group.permissions.add(*perms)

    def get_models_from_module(self, module):
        models = []
        try:
            app_models = importlib.import_module(f"{module}.models")
            for _, name, _ in pkgutil.iter_modules(app_models.__path__):
                models.append(name.capitalize())
        except Exception:
            pass
        return models

    def tui_main_menu(self):
        return questionary.select(
            "O que deseja fazer?",
            choices=[
                "➕ Adicionar novo campo",
                "❌ Remover campo",
                "📋 Ver campos",
                "✅ Finalizar modelo",
                "🚫 Abortar (cancelar tudo)",
            ],
        ).ask()
    def tui_field_type(self):
        return questionary.select(
            "Tipo do campo:",
            choices=[
                "CharField", "TextField", "IntegerField", "BooleanField", "DateField",
                "ForeignKey", "OneToOneField", "ManyToManyField",
                "FileField", "ImageField",
            ],
        ).ask()

    def tui_yes_no(self, msg):
        return questionary.confirm(msg).ask()

    def tui_choose_module(self):
        return questionary.select(
            "Escolha o módulo:",
            choices=settings.MY_APPS
        ).ask()

    def tui_choose_model(self, module):
        models = self.get_models_from_module(module)
        if not models:
            return None
        return questionary.select(
            f"Escolha o modelo de {module}:",
            choices=models
        ).ask()
    def tui_show_fields(self, fields):
        console = Console()
        table = Table(title="📋 Campos do Modelo")

        table.add_column("#")
        table.add_column("Nome")
        table.add_column("Tipo")
        table.add_column("Relação")
        table.add_column("Null")
        table.add_column("Blank")

        for i, f in enumerate(fields):
            rel = f.get("relation", "-")
            table.add_row(
                str(i + 1),
                f["name"],
                f["type"],
                rel,
                str(f["null"]),
                str(f["blank"]),
            )

        console.print(table)

    def tui_remove_field(self, fields):
        if not fields:
            return fields

        names = [f["name"] for f in fields]
        name = questionary.select("Escolha o campo para remover:", choices=names).ask()
        return [f for f in fields if f["name"] != name]

    def tui_create_field(self):
        name = questionary.text("Nome do campo:").ask()
        field_type = self.tui_field_type()
        verbose = questionary.text("Verbose name:", default=name.replace("_", " ").title()).ask()

        null = self.tui_yes_no("null=True?")
        blank = self.tui_yes_no("blank=True?")
        default = questionary.text("Default (ENTER nenhum):").ask()

        field = {
            "name": name,
            "type": field_type,
            "verbose": verbose,
            "null": null,
            "blank": blank,
            "default": default,
            "choices": None,
        }

        # Choices wizard
        if self.tui_yes_no("Deseja choices?"):
            choices = []
            while True:
                key = questionary.text("Código:").ask()
                label = questionary.text("Label:").ask()
                choices.append((key, label))
                if not self.tui_yes_no("Adicionar outra choice?"):
                    break
            field["choices"] = choices

        # Relações
        if field_type in ["ForeignKey", "OneToOneField", "ManyToManyField"]:
            module = self.tui_choose_module()
            model = self.tui_choose_model(module)
            if model:
                field["relation"] = f"{module}.{model}"

            # on_delete
            if field_type != "ManyToManyField":
                on_delete = questionary.select(
                    "on_delete:",
                    choices=["CASCADE", "PROTECT", "SET_NULL", "SET_DEFAULT", "DO_NOTHING", "RESTRICT"],
                ).ask()
                field["on_delete"] = on_delete

                if on_delete == "SET_NULL":
                    field["null"] = True

            # related_name automático
            field["related_name"] = f"{self.current_model_name.lower()}s"

        # Upload fields
        if field_type in ["FileField", "ImageField"]:
            if self.tui_yes_no("Usar função upload_to personalizada (file_path)?"):
                field["upload_func"] = "file_path"
            else:
                folder = questionary.text("Pasta upload (ex: uploads/):", default="uploads/").ask()
                field["upload_to"] = folder

        return field

    def tui_wizard_fields(self):
        fields = []

        while True:
            action = self.tui_main_menu()

            if action.startswith("➕"):
                fields.append(self.tui_create_field())

            elif action.startswith("❌"):
                fields = self.tui_remove_field(fields)

            elif action.startswith("📋"):
                self.tui_show_fields(fields)

            elif action.startswith("✅"):
                if not fields:
                    print("⚠️ Precisa de pelo menos 1 campo!")
                    continue
                return fields
            elif action.startswith("🚫"):
                return False
                
    def generate_model_code(self, name, fields):
        lines = [
            "from django.db import models",
            "from django_saas.core.base.models import BaseModel",
            "",
        ]

        # Upload path function
        if any(f.get("upload_func") == "file_path" for f in fields):
            lines.append("""
def file_path(instance, file_name):
    return f"{instance.entidade.tipo_entidade.nome}/{instance.entidade.nome}/{file_name}"
    """)

        lines.append(f"class {name}(BaseModel):")
        lines.append(f'    """ Modelo {name} """')
        lines.append("")

        for f in fields:
            opts = []
            opts.append(f'verbose_name="{f["verbose"]}"')
            if f["null"]:
                opts.append("null=True")
            if f["blank"]:
                opts.append("blank=True")
            if f["default"]:
                opts.append(f"default={f['default']}")
            if f["choices"]:
                opts.append(f"choices={f['choices']}")

            # upload fields
            if f["type"] in ["FileField", "ImageField"]:
                if "upload_func" in f:
                    opts.append("upload_to=file_path")
                else:
                    opts.append(f'upload_to="{f["upload_to"]}"') 

            opt_str = ", ".join(opts)

            # Campos normais
            if f["type"] == "CharField":
                lines.append(f"    {f['name']} = models.CharField(max_length=255, {opt_str})")
            elif f["type"] == "TextField":
                lines.append(f"    {f['name']} = models.TextField({opt_str})")
            elif f["type"] == "IntegerField":
                lines.append(f"    {f['name']} = models.IntegerField({opt_str})")
            elif f["type"] == "BooleanField":
                lines.append(f"    {f['name']} = models.BooleanField({opt_str})")
            elif f["type"] == "DateField":
                lines.append(f"    {f['name']} = models.DateField({opt_str})")

            # Relações
            elif f["type"] == "ForeignKey":
                on_delete = f.get("on_delete", "CASCADE")
                rn = f.get("related_name", f"{name.lower()}s")
                lines.append(
                    f"    {f['name']} = models.ForeignKey("
                    f"'{f['relation']}', on_delete=models.{on_delete}, related_name='{rn}', {opt_str})"
                )

            elif f["type"] == "OneToOneField":
                on_delete = f.get("on_delete", "CASCADE")
                rn = f.get("related_name", f"{name.lower()}s")
                lines.append(
                    f"    {f['name']} = models.OneToOneField("
                    f"'{f['relation']}', on_delete=models.{on_delete}, related_name='{rn}', {opt_str})"
                )

            elif f["type"] == "ManyToManyField":
                lines.append(f"    {f['name']} = models.ManyToManyField('{f['relation']}', {opt_str})")

            # Upload
            elif f["type"] == "FileField":
                lines.append(f"    {f['name']} = models.FileField({opt_str})")
            elif f["type"] == "ImageField":
                lines.append(f"    {f['name']} = models.ImageField({opt_str})")

        # __str__
        lines.append("")
        lines.append("    def __str__(self):")
        lines.append(f"        return str(self.id)")

        return "\n".join(lines)







    def add_arguments(self, parser):
        parser.add_argument("ModelName", type=str, help="Nome do modelo (ex: Funcionario)")
        parser.add_argument("--module", type=str, help="Nome do módulo (opcional)")

    def handle(self, *args, **options):
        service = ScaffoldService(settings.BASE_DIR)

        fields = self.tui_wizard_fields()

        service.create(
            module=module,
            model_name=model_name,
            fields=fields
        )
       


        

    # ================== UTILS ==================

    def choose_module(self):
        return questionary.select(
            "Escolha o módulo:",
            choices=settings.MY_APPS
        ).ask()

        

    def serializer_exists(self, module_path, model):
        path = os.path.join(module_path, "serializers", f"{model.lower()}.py")
        return os.path.exists(path)

    def create_simple_serializer(self, module_path, module, model):
        path = os.path.join(module_path, "serializers", f"{model.lower()}.py")

        content = f"""from django_saas.core.base.serializers import BaseSerializer
from {module}.models.{model.lower()} import {model}


class {model}Serializer(BaseSerializer):
    class Meta:
        model = {model}
        fields = "__all__"
    """

        safe_write(path, content)

        self.stdout.write(self.style.SUCCESS(f"✅ {model}Serializer criado automaticamente"))

    def create_service(self, module_path, module, name):
        path = os.path.join(module_path, "services", f"{name.lower()}_service.py")

        content = f"""from {module}.models.{name.lower()} import {name}

class {name}Service:
    \"\"\" Service layer for {name} business rules \"\"\"

    model = {name}

    @classmethod
    def list(cls):
        return cls.model.objects.all()

    @classmethod
    def get(cls, **filters):
        return cls.model.objects.filter(**filters).first()

    @classmethod
    def create(cls, **data):
        return cls.model.objects.create(**data)

    @classmethod
    def update(cls, instance, **data):
        for k, v in data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    @classmethod
    def delete(cls, instance):
        instance.delete()
    """

        safe_write(path, content)

        self.stdout.write(self.style.SUCCESS(f"{name}Service criado em services/ 🚀"))

    def ensure_relation_serializer(self, rel_module, rel_model):
        rel_module_path = os.path.join(BASE_MODULES_PATH, rel_module)

        if not self.serializer_exists(rel_module_path, rel_model):
            if questionary.confirm(
                f"{rel_model}Serializer não encontrado. Criar automaticamente?"
            ).ask():
                self.create_simple_serializer(rel_module_path, rel_module, rel_model)


    def create_serializer(self, module_path, module, name, fields):
        path = os.path.join(module_path, "serializers", f"{name.lower()}.py")

        imports = [
            "from django_saas.core.base.serializers import BaseSerializer",
            f"from {module}.models.{name.lower()} import {name}",
            "from rest_framework import serializers",
        ]

        nested_imports = []
        serializer_fields = []

        for f in fields:
            if "relation" in f:
                rel_module, rel_model = f["relation"].split(".")

                self.ensure_relation_serializer(rel_module, rel_model)

                if rel_module.startswith('django_saas'):
                    nested_imports.append(f"from {rel_module}.models.{rel_model.lower()} import {rel_model}")
                    nested_imports.append(f"from {rel_module}.data.{rel_model.lower()}.serializers.{rel_model.lower()} import {rel_model}Serializer")
                else: 
                    nested_imports.append(f"from {rel_module}.models.{rel_model.lower()} import {rel_model}")
                    nested_imports.append(f"from {rel_module}.serializers.{rel_model.lower()} import {rel_model}Serializer")

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

class {name}Serializer(BaseSerializer):
    """

        for line in serializer_fields:
            content += line + "\n\n"

        content += f"""
    class Meta:
        model = {name}
        fields = "__all__"
    """

        safe_write(path, content)

        self.stdout.write(self.style.SUCCESS(f"{name}Serializer criado: {path} em {module} 🚀"))




    def create_viewset(self, module_path, module, name):
        path = os.path.join(module_path, "views", f"{name.lower()}.py")

        content = f'''from django_saas.core.base.views import BaseAPIView
from django_saas.core.base.views import register_view
from {module}.models.{name.lower()} import {name}
from {module}.serializers.{name.lower()} import {name}Serializer

@register_view('{name.lower()}s')
class {name}APIView(BaseAPIView):
    queryset = {name}.objects.all()
    serializer_class = {name}Serializer
'''
        safe_write(path, content, 'w')
        self.stdout.write(self.style.SUCCESS(f"{name}APIView  criado em {module} 🚀"))

    def update_admin(self, module_path, module, name):
       

        path = os.path.join(module_path, "admin.py")
        content = f"""
from django.contrib import admin
from {module}.models.{name.lower()} import {name}

@admin.register({name})
class {name}Admin(BaseAdmin):
    def get_list_display(self, request): return all_fields(self.model)
    list_display_links = ('id',)
    search_fields = ['id']
"""
        safe_write(path, content, 'a')
        self.stdout.write(self.style.SUCCESS(f"Admin actualizado 🚀"))

    

    def update_sidebar(self, module_path, module, model_name):
        sidebar_file = Path(module_path) / "sidebar.py"

        if not sidebar_file.exists():
            self.stdout.write(f"⚠️ sidebar.py não encontrado em {module}")
            return

        # Importar sidebar.py dinamicamente
        spec = importlib.util.spec_from_file_location(f"{module}_sidebar", sidebar_file)
        sidebar = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sidebar)

        menu_name = model_name
        new_item = {
            "icon": "list",
            "menu": menu_name,
            "role": f"list_{menu_name.lower()}",
            "rota": f"list_{menu_name.lower()}",
            "add_role": f"add_{menu_name.lower()}",
            "add_rota": f"add_{menu_name.lower()}",
        }

        # Evitar duplicados
        if any(x["menu"] == menu_name for x in sidebar.SUBMENUS):
            self.stdout.write(f"⚠️ Submenu {menu_name} já existe")
            return

        sidebar.SUBMENUS.append(new_item)

        # Reescrever sidebar.py formatado
        content = f'''
MENU = "{sidebar.MENU}"
ICON = "{sidebar.ICON}"

SUBMENUS = {pprint.pformat(sidebar.SUBMENUS, indent=4, width=120)}
    '''
        sidebar_file.write_text(write_python_pretty(content))
        self.stdout.write(self.style.SUCCESS(f"✅ Submenu '{menu_name}' adicionado"))


def write_python_pretty(code: str) -> str:
    import black
    return black.format_str(code, mode=black.FileMode())


    def create_model(self, module_path, module, name, fields):
        # usado para related_name automático
          

        path = os.path.join(module_path, "models", f"{name.lower()}.py")

        # gerar código python do model
        content = self.generate_model_code(name, fields)

        # escrever ficheiro
        safe_write(path, content)

        self.stdout.write(self.style.SUCCESS(f"✅ Modelo {name} criado em {module} 🚀"))


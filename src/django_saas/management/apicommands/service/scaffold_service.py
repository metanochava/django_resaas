import os
import logging
from pathlib import Path
logger = logging.getLogger(__name__)


class ScaffoldService:
    """
    Engine única responsável por gerar módulos dinamicamente
    Pode ser chamada via CLI ou API
    """

    def __init__(self, base_path):
        self.base_path = base_path
        self.created_files = []

    # ======================================================
    # PUBLIC API
    # ======================================================

    def create(self, module, model_name, fields, dry_run=False):
        module_path = os.path.join(self.base_path, module)

        try:
            self.created_files = []

            self._step(self.create_model, module_path, module, model_name, fields, dry_run)
            self._step(self.create_serializer, module_path, module, model_name, fields, dry_run)
            self._step(self.create_view, module_path, module, model_name, dry_run)
            self._step(self.create_service, module_path, module, model_name, dry_run)
            self._step(self.update_admin, module_path, module, model_name, dry_run)
            self._step(self.update_sidebar, module_path, module, model_name, dry_run)

            if not dry_run:
                self.run_migrations(module)
                self.grant_admin_permissions(module, model_name)

            logger.info(
                f"[SCAFFOLD] module={module} model={model_name} files={len(self.created_files)}"
            )

            return self.created_files

        except Exception as e:
            logger.exception("Scaffold failed. Rolling back...")
            self.rollback()
            raise e

    # ======================================================
    # INTERNAL EXECUTOR
    # ======================================================

    def _step(self, func, *args):
        path = func(*args)
        if path:
            self.created_files.append(str(path))

    # ======================================================
    # ROLLBACK (🔥 muito importante)
    # ======================================================

    def rollback(self):
        for file in reversed(self.created_files):
            try:
                p = Path(file)
                p.unlink(missing_ok=True)

                parent = p.parent
                if not any(parent.iterdir()):
                    parent.rmdir()
            except Exception:
                pass

    
    def create_model(self, module_path, module, name, fields, dry_run=False):
        path = os.path.join(module_path, "models", f"{name.lower()}.py")

        content = self.generate_model_code(name, fields)

        if not dry_run:
            safe_write(path, content)

        return path

    def create_serializer(self, module_path, module, name, fields, dry_run=False):
        path = os.path.join(module_path, "serializers", f"{name.lower()}.py")

        content = self.generate_serializer_code(module, name, fields)

        if not dry_run:
            safe_write(path, content)

        return path

    def create_view(self, module_path, module, name, dry_run=False):
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

        if not dry_run:
            safe_write(path, content)

        return path


    def create_service(self, module_path, module, name, dry_run=False):
        path = os.path.join(module_path, "services", f"{name.lower()}_service.py")

        content = f"""from {module}.models.{name.lower()} import {name}

class {name}Service:
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

        if not dry_run:
            safe_write(path, content)

        return path


    def update_admin(self, module_path, module, name, dry_run=False):
        path = os.path.join(module_path, "admin.py")

        content = f"""
from {module}.models.{name.lower()} import {name}

@admin.register({name})
class {name}Admin(admin.ModelAdmin):
    list_display = ("id",)
    """

        if not dry_run:
            safe_write(path, content, "a")

        return path


    def update_sidebar(self, module_path, module, model_name, dry_run=False):
        sidebar_file = Path(module_path) / "sidebar.py"

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
            "icon": "list",
            "menu": menu_name,
            "role": f"list_{menu_name.lower()}",
            "rota": f"list_{menu_name.lower()}",
            "add_role": f"add_{menu_name.lower()}",
            "add_rota": f"add_{menu_name.lower()}",
        }

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


    def generate_serializer_code(module, name, fields):
        path = os.path.join(module, "serializers", f"{name.lower()}.py")

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

        return content
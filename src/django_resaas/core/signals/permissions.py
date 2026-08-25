# ==========================================================
# IMPORTS
# ==========================================================
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Permission
from django_resaas.models.group import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

# 🔹 Models do sistema
from django_resaas.models.person import Person
from django_resaas.models.entity_type import EntityType
from django_resaas.models.entity import Entity
from django_resaas.models.theme import Theme, Typography
from django_resaas.models.layout_setting import LayoutSetting, AnimationSetting
from django_resaas.models.user import User


# ==========================================================
# POST MIGRATE - CRIAÇÃO DE PERMISSÕES
# ==========================================================
@receiver(post_migrate)
def create_model_permissions(sender, **kwargs):
    """
    Cria permissões automaticamente por model e garante que
    o group root está sempre atualizado.

    ✔ list_<model>
    ✔ pdf_<model>
    ✔ restore_<model>
    ✔ hard_delete_<model>

    ✔ scaffold permissions

    ✔ Seguro para múltiplas execuções (idempotente)
    """

    # ------------------------------------------------------
    # EXECUTA APENAS NO APP PRINCIPAL
    # ------------------------------------------------------
    if kwargs.get("app_config").name != "django_resaas":
        return

    # ------------------------------------------------------
    # 🔥 FIX CRÍTICO: GARANTE CONTEXTO ANTES DE EXECUTAR
    # Evita erro: entity_type_id = NULL
    # ------------------------------------------------------
    if not EntityType.objects.exists():
        return

    # ------------------------------------------------------
    # APPS PERMITIDAS
    # ------------------------------------------------------
    MY_APPS = getattr(settings, "MY_APPS", []) + ["django.contrib.auth"]
    allowed_apps = [app.split(".")[-1] for app in MY_APPS]

    # ------------------------------------------------------
    # GROUP ROOT
    # ------------------------------------------------------
    admin_group, _ = Group.objects.get_or_create(name="Root")

    created_perms = []

    # ======================================================
    # MODEL EXTRA PERMISSIONS
    # ======================================================
    for model in apps.get_models():

        # 🔹 filtrar apenas apps permitidas
        if model._meta.app_label not in allowed_apps:
            continue

        ct = ContentType.objects.get_for_model(model)

        for codename, label in [
            ("view", "Can view"),       # Nativo
            ("add", "Can add"),         # Nativo
            ("change", "Can change"),   # Nativo
            ("delete", "Can delete"),   # Nativo

            
            ("list", "Can list"),
            ("pdf", "Can pdf"),
            ("pdf_list", "Can pdf list"),
            ("restore", "Can restore"),
            ("hard_delete", "Can hard delete"),
        ]:
            perm, _ = Permission.objects.get_or_create(
                codename=f"{codename}_{model._meta.model_name}",
                content_type=ct,
                defaults={
                    "name": f"{label} {model._meta.verbose_name}"
                },
            )

            created_perms.append(perm)

    # ======================================================
    # SCAFFOLD PERMISSIONS
    # ======================================================
    ct, _ = ContentType.objects.get_or_create(
        app_label="django_resaas",
        model="command",
    )

    for codename, name in [
        ("add_app", "Can add app"),
        ("change_app", "Can change app"),
        ("view_dev", "Can view dev"),
        ("view_scaffold", "Can view scaffold"),
        ("view_crud", "Can view crud"),
        ("add_scaffold", "Can add scaffold"),
        ("change_scaffold", "Can change scaffold"),
        ("delete_scaffold", "Can delete scaffold"),
    ]:
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            content_type=ct,
            defaults={"name": name},
        )

        created_perms.append(perm)

    # ======================================================
    # ATUALIZAR GROUP ROOT
    # ======================================================
    admin_group.permissions.add(*created_perms)


# ==========================================================
# USER → PESSOA (AUTO CREATE)
# ==========================================================
@receiver(post_save, sender=User, dispatch_uid="criar_person_user")
def criar_person_automaticamente(sender, instance, created, **kwargs):
    """
    Cria automaticamente um registo Person quando um User é criado.
    """
    if created:
        Person.objects.get_or_create(
            user=instance,
            defaults={
                "name": instance.first_name or "",
                "surname": instance.last_name or "",
                "email": instance.email or "",
            }
        )


# ==========================================================
# USER → PESSOA (SYNC)
# ==========================================================
@receiver(post_save, sender=User, dispatch_uid="sync_person_user")
def sync_person(sender, instance, **kwargs):
    if getattr(instance, "_skip_sync", False):
        return

    person = getattr(instance, "person", None)

    if person:
        person._skip_sync = True

        person.name = instance.first_name or ""
        person.surname = instance.last_name or ""
        person.email = instance.email or ""

        person.save()



@receiver(post_save, sender=Person, dispatch_uid="sync_user_person")
def sync_user(sender, instance, **kwargs):
    if getattr(instance, "_skip_sync", False):
        return

    if instance.user:
        user = instance.user

        user._skip_sync = True

        user.first_name = instance.name or ""
        user.last_name = instance.surname or ""
        user.email = instance.email or ""

        user.save()


# ==========================================================
# TIPO ENTIDADE → CONFIGURAÇÕES INICIAIS
# ==========================================================
@receiver(post_save, sender=EntityType)
def criar_thema(sender, instance, created, **kwargs):
    """
    Cria automaticamente configurações iniciais quando
    uma EntityType é criada.
    """
    if created and not instance.theme:

        instance.theme = Theme.objects.create(state="Active")
        instance.layout_settings = LayoutSetting.objects.create(state="Active")
        instance.animation_settings = AnimationSetting.objects.create(state="Active")
        instance.typography = Typography.objects.create(state="Active")

        instance.save(update_fields=[
            "theme",
            "layout_settings",
            "animation_settings",
            "typography"
        ])
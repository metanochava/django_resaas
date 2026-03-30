from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
import importlib
from django.db.models.signals import post_save
from django.dispatch import receiver

from django_resaas.models.pessoa import Pessoa

from django_resaas.models.tipo_entidade import TipoEntidade
from django_resaas.models.entidade import Entidade
from django_resaas.models.theme import Theme, Typography
from django_resaas.models.layout_setting import LayoutSetting, AnimationSetting
# from django_resaas.data.theme.serializers.theme import ThemeSerializer, TypographySerializer
# from django_resaas.data.layout_setting.serializers.layout_setting import LayoutSettingSerializer, AnimationSettingSerializer
from django_resaas.models.user import User


from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.conf import settings
from django.apps import apps
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType


@receiver(post_migrate)
def create_model_permissions(sender, **kwargs):
    """
    Cria permissões automaticamente por modelo e garante que
    o grupo root está sempre atualizado.

    ✔ list_<model>
    ✔ pdf_<model>
    ✔ restore_<model>
    ✔ hard_delete_<model>
    ✔ scaffold permissions

    ✔ Atualiza automaticamente quando novos modelos são adicionados
    ✔ Seguro para múltiplas execuções (idempotente)
    """

    # 🔥 executa apenas no app principal
    if kwargs.get("app_config").name != "django_resaas":
        return

    # 🔹 apps permitidas
    MY_APPS = getattr(settings, "MY_APPS", []) + ["django.contrib.auth"]
    allowed_apps = [app.split(".")[-1] for app in MY_APPS]

    # 🔹 grupo root
    admin_group, _ = Group.objects.get_or_create(name="root")

    created_perms = []

    # ==================================================
    # MODEL PERMISSIONS
    # ==================================================
    for model in apps.get_models():

        if model._meta.app_label not in allowed_apps:
            continue

        ct = ContentType.objects.get_for_model(model)

        for codename, label in [
            ("list", "Can list"),
            ("pdf", "Can pdf"),
            ("restore", "Can restore"),
            ("hard_delete", "Can hard delete"),
        ]:
            perm, _ = Permission.objects.get_or_create(
                codename=f"{codename}_{model._meta.model_name}",
                content_type=ct,
                defaults={"name": f"{label} {model._meta.verbose_name}"},
            )
            created_perms.append(perm)

    # ==================================================
    # SCAFFOLD PERMISSIONS
    # ==================================================
    ct, _ = ContentType.objects.get_or_create(
        app_label="django_resaas",
        model="command",
    )

    for codename, name in [
        ("add_modulo", "Can add modulo"),
        ("change_modulo", "Can change modulo"),
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

    # ==================================================
    # ATUALIZAR root (INCREMENTAL)
    # ==================================================
    admin_group.permissions.add(*created_perms)



@receiver(post_save, sender=User, dispatch_uid="criar_pessoa_user")
def criar_pessoa_automaticamente(sender, instance, created, **kwargs):
    if created:
        Pessoa.objects.get_or_create(
            user=instance,
            defaults={
                "nome": instance.first_name or "",
                "apelido": instance.last_name or "",
                "email": instance.email or "",
            }
        )

@receiver(post_save, sender=User, dispatch_uid="sync_pessoa_user")
def sync_pessoa(sender, instance, **kwargs):
    if hasattr(instance, 'pessoa'):
        pessoa = instance.pessoa
        pessoa.nome = instance.first_name or ""
        pessoa.apelido = instance.last_name or ""
        pessoa.email = instance.email or ""
        pessoa.save()


@receiver(post_save, sender=TipoEntidade)
def criar_thema(sender, instance, created, **kwargs):
    if created and not instance.theme:

        instance.theme = Theme.objects.create()
        instance.layout_settings = LayoutSetting.objects.create()
        instance.animation_settings = AnimationSetting.objects.create()
        instance.typography = Typography.objects.create()
        instance.save(update_fields=["theme", "layout_settings", "animation_settings", "typography"])

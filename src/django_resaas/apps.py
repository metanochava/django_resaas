from django.apps import AppConfig
from django.db.models.signals import post_migrate


# ==========================================================
# CREATE SAUDE GROUPS
# ==========================================================
def create_django_resaas_groups(sender, **kwargs):
    if kwargs.get("app_config").name != "django_resaas":
        return

    from django.contrib.auth.models import Group
    GROUPS_WITH_ID = [
        (1, "Guest"),
        (2, "Root"),
        (3, "Admin"),
    ]

    for gid, gname in GROUPS_WITH_ID:
        group, _ = Group.objects.get_or_create(
            id=gid,  # 🔥 FORÇA O ID
            defaults={"name": gname}
        )




class DjangoResaasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "django_resaas"
    verbose_name = "Django SaaS"

    def ready(self):
        """
        Carrega signals de forma segura.

        ✔ evita múltiplas importações
        ✔ evita efeitos colaterais
        """


        # 🔥 SIGNAL CORRETO
        post_migrate.connect(create_django_resaas_groups, sender=self)

        

        # 🔥 IMPORT LAZY (IMPORTANTE)
        self.load_permissions()

        # opcional
        # self.load_admin()

    def load_permissions(self):
        """
        Regista signals de permissões.
        """
        try:
            import django_resaas.core.signals.permissions
        except Exception as e:
            print(f"⚠️ Erro ao carregar permissions signals: {e}")

    def load_admin(self):
        """
        Regista admin automaticamente.
        """
        try:
            from django_resaas.core.base.mixins.admin.auto import register_all_models
            register_all_models()
        except Exception as e:
            print(f"⚠️ Erro ao carregar admin: {e}")
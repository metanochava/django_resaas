from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django_resaas.core.utils.group_creator import GROUPS


# ==========================================================
# CREATE SAUDE GROUPS
# ==========================================================
def create_django_resaas_groups(sender, **kwargs):
    if kwargs.get("app_config").name != "django_resaas":
        return

    from django_resaas.models.group import Group


    for gname in GROUPS:
        group, _ = Group.objects.get_or_create(
            name= gname
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
        from django.contrib import admin
        from django.contrib.auth.models import Group

        try:
            admin.site.unregister(Group)
        except admin.sites.NotRegistered:
            pass


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
from django.apps import AppConfig
from django.db.models.signals import post_migrate

from django_resaas.engine.core.utils.group_creator import GROUPS


# ==========================================================
# CREATE DJANGO RESAAS GROUPS
# ==========================================================

def create_django_resaas_groups(sender, **kwargs):

    if kwargs.get("app_config").name != "django_resaas.engine":
        return

    from django_resaas.engine.models.group import Group

    for gname in GROUPS:

        Group.objects.get_or_create(
            name=gname
        )


# ==========================================================
# APP CONFIG
# ==========================================================

class DjangoResaasConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "django_resaas.engine"

    label = "engine"

    verbose_name = "Django SaaS"


    # ======================================================
    # READY
    # ======================================================

    def ready(self):
        """
        Inicializa os recursos do django_resaas.

        - remove Group padrão do Django Admin
        - cria Groups RESAAS após migrations
        - carrega signals de permissions
        - carrega signals de actions
        """

        # ==================================================
        # ADMIN
        # ==================================================

        from django.contrib import admin

        from django.contrib.auth.models import (
            Group as GG
        )

        try:

            admin.site.unregister(GG)

        except admin.sites.NotRegistered:

            pass


        # ==================================================
        # GROUPS
        # ==================================================

        post_migrate.connect(
            create_django_resaas_groups,
            sender=self
        )


        # ==================================================
        # PERMISSIONS SIGNALS
        # ==================================================

        self.load_permissions()


        # ==================================================
        # ACTION SIGNALS
        # ==================================================

        self.load_actions()


        # ==================================================
        # ADMIN AUTO REGISTER
        # ==================================================

        # self.load_admin()


    # ======================================================
    # PERMISSIONS
    # ======================================================

    def load_permissions(self):
        """
        Regista signals responsáveis pelas permissions.
        """

        try:

            import django_resaas.engine.core.signals.permissions  # noqa: F401

        except Exception as e:

            print(
                f"⚠️ Error loading permissions signals: {e}"
            )


    # ======================================================
    # ACTIONS
    # ======================================================

    def load_actions(self):
        """
        Regista signals responsáveis pelas
        @resaas_action.
        """

        try:

            import django_resaas.engine.core.signals.action_sync  # noqa: F401

        except Exception as e:

            print(
                f"⚠️ Error loading action signals: {e}"
            )


    # ======================================================
    # ADMIN
    # ======================================================

    def load_admin(self):
        """
        Regista models automaticamente no admin.
        """

        try:

            from django_resaas.engine.core.base.mixins.admin.auto import (
                register_all_models
            )

            register_all_models()

        except Exception as e:

            print(
                f"⚠️ Error loading admin: {e}"
            )
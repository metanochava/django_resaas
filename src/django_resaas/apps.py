from django.apps import AppConfig


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
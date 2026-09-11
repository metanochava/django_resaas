import importlib
import pkgutil

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_hr_groups(sender, **kwargs):
    """Cria os perfis (Group templates) do módulo hr - mesmo mecanismo
    de saude/apps.py's create_saude_groups() (ver hr/profiles.py).
    Guard idêntico ao de todos os outros apps.py: só corre depois de
    já existir pelo menos uma EntityType real."""

    if kwargs.get("app_config").label != "hr":
        return

    from django_resaas.saas.models.entity_type import EntityType

    if not EntityType.objects.exists():
        return

    from django_resaas.saas.core.utils.group_creator import group_creator
    from django_resaas.hr.profiles import HR_PROFILES

    group_creator(HR_PROFILES)


class HrConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "django_resaas.hr"
    label = "hr"

    verbose_name = "HR"

    def ready(self):
        """Carrega todas as views do módulo para que os decorators
        @registerView/@resaas_action corram e populem VIEW_REGISTRY
        ANTES do post_migrate (consumido por
        saas/core/signals/action_sync.py's sync_resaas_actions,
        que só cria/actualiza as Permissions das @resaas_action
        quando VIEW_REGISTRY já não está vazio) - mesmo padrão já
        usado por saude/sales/inventory/farmacia's apps.py. Sem isto,
        hr nunca tinha as suas custom action permissions
        (hire_application, calculate_payroll, approve_leaverequest,
        ...) criadas antes do primeiro pedido HTTP real resolver
        hr/urls.py - o que mascarava o problema em produção mas
        quebrava qualquer teste que criasse permissões via ORM antes
        de qualquer request."""

        import django_resaas.hr.views

        for _, module_name, _ in pkgutil.iter_modules(django_resaas.hr.views.__path__):
            importlib.import_module(f"django_resaas.hr.views.{module_name}")

        post_migrate.connect(create_hr_groups, sender=self)

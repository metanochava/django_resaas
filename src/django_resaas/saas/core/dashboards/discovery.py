"""Descoberta automática de `<app>/dashboard.py`.

Clona exactamente o padrão já usado por UserAPIView.menus() para o
sidebar (saas/data/user/views/user.py) - mesmo
`except ModuleNotFoundError as exc: if exc.name == module_name: continue;
raise`, para nunca esconder um import quebrado dentro do próprio
dashboard.py.

Diferença deliberada face ao sidebar: a descoberta de dashboards
percorre TODAS as apps instaladas (django.apps.apps.get_app_configs()),
não só as activas para o tenant do request actual - a descoberta é
tenant-agnostic (roda uma vez por processo); "módulo activo" é uma
verificação por request, feita depois, em permissions.py.
"""

import importlib
import logging

from django.apps import apps

from django_resaas.saas.core.dashboards.exceptions import DashboardConfigError
from django_resaas.saas.core.dashboards.registry import DashboardRegistry
from django_resaas.saas.core.dashboards.validator import DashboardValidator

logger = logging.getLogger(__name__)

_DISCOVERED = False


class DashboardDiscoveryService:

    @staticmethod
    def discover(force=False):
        global _DISCOVERED

        if _DISCOVERED and not force:
            return

        if force:
            DashboardRegistry.clear()

        for app_config in apps.get_app_configs():

            module_name = f"{app_config.name}.dashboard"

            try:
                dashboard_module = importlib.import_module(module_name)

            except ModuleNotFoundError as exc:
                # Ignora só quando esta app não tem dashboard.py.
                # Se dashboard.py existir mas um import interno dele
                # falhar, o erro real é sempre propagado.
                if exc.name == module_name:
                    continue
                raise

            single = getattr(dashboard_module, "DASHBOARD", None)
            many = getattr(dashboard_module, "DASHBOARDS", None)

            if single is None and many is None:
                message = (
                    f"'{module_name}' existe mas não define 'DASHBOARD' "
                    "nem 'DASHBOARDS' - ignorado."
                )
                logger.warning(message)
                continue

            # DASHBOARD (one dict, its name is the module name - original
            # contract) and/or DASHBOARDS (a list of extra dashboards of
            # the same app, each with its own unique name). A dashboard of
            # the list belongs to this app's module unless it says
            # otherwise ("module"), so "module active" keeps being checked
            # against the right App.
            configs = [single] if single is not None else []

            for extra in many or []:
                if isinstance(extra, dict):
                    extra = {**extra}
                    extra.setdefault("module", app_config.label)
                configs.append(extra)

            for config in configs:
                DashboardDiscoveryService._register(config, module_name, app_config)

        _DISCOVERED = True

    @staticmethod
    def _register(config, module_name, app_config):
        try:
            DashboardValidator.validate(config, app_label=app_config.label)

        except DashboardConfigError as exc:
            message = f"Dashboard inválido em '{module_name}': {exc.message}"
            logger.error(message)
            DashboardRegistry.record_error(message)
            return

        DashboardRegistry.register(
            config["name"],
            config,
            app_label=app_config.label,
        )

    @staticmethod
    def reset():
        """Só para testes."""
        global _DISCOVERED
        _DISCOVERED = False
        DashboardRegistry.clear()

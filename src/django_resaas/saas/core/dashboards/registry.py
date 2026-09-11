"""Registry em memória dos dashboards descobertos.

Mesmo espírito de VIEW_REGISTRY (saas/core/base/registry.py) - um
dict global populado uma vez por processo. A diferença crítica é que
aqui a leitura é sempre uma cópia (copy.deepcopy): a configuração
global NUNCA pode ser mutada por um request (ver o teste de
imutabilidade em tests/test_dashboard_registry.py - User A não pode
"contaminar" o que User B recebe).
"""

import copy
import logging

logger = logging.getLogger(__name__)

# {dashboard_name: DASHBOARD dict}
_DASHBOARDS = {}

# Mensagens de dashboards ignorados por erro de validação (não erro de
# import - esse propaga sempre, ver discovery.py). Visível para
# diagnóstico (ex.: comando de management, testes) sem levantar
# excepção durante a descoberta de outro módulo.
_ERRORS = []


class DashboardRegistry:

    @staticmethod
    def register(name, config, *, app_label):
        if name in _DASHBOARDS:
            message = (
                f"Dashboard duplicado: '{name}' já foi registado "
                f"(app '{app_label}' tentou registar outra vez). "
                "Mantido o primeiro, o segundo foi ignorado."
            )
            logger.error(message)
            _ERRORS.append(message)
            return False

        _DASHBOARDS[name] = copy.deepcopy(config)
        return True

    @staticmethod
    def get(name):
        config = _DASHBOARDS.get(name)
        return copy.deepcopy(config) if config is not None else None

    @staticmethod
    def get_all():
        return [
            copy.deepcopy(config)
            for config in sorted(
                _DASHBOARDS.values(),
                key=lambda c: (c.get("order") or 999, c.get("name") or ""),
            )
        ]

    @staticmethod
    def record_error(message):
        _ERRORS.append(message)

    @staticmethod
    def get_errors():
        return list(_ERRORS)

    @staticmethod
    def clear():
        """Só para testes - força uma nova descoberta na próxima
        chamada a DashboardDiscoveryService.discover()."""
        _DASHBOARDS.clear()
        _ERRORS.clear()

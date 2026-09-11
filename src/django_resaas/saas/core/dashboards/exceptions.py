"""Erros do motor de dashboards dinâmicos.

Todos carregam `code`/`message`/`fields` para alimentar directamente o
formato de erro padronizado de DashboardResponseService.error_response()
- ver ali para o contrato JSON exposto na API.
"""


class DashboardEngineError(Exception):
    code = "dashboard_error"
    status_code = 400

    def __init__(self, message, *, fields=None, code=None, status_code=None):
        super().__init__(message)
        self.message = message
        self.fields = fields or {}
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class DashboardConfigError(DashboardEngineError):
    """Configuração declarada em <app>/dashboard.py inválida (schema_version
    desconhecida, campo obrigatório em falta, duplicado, provider
    desconhecido, ...). Nunca deve ser confundido com um erro de import
    real dentro do módulo - esse nunca é apanhado/escondido, ver
    discovery.py."""

    code = "invalid_dashboard_config"


class DashboardNotFoundError(DashboardEngineError):
    code = "dashboard_not_found"
    status_code = 404


class DashboardPermissionError(DashboardEngineError):
    code = "permission_denied"
    status_code = 403


class DashboardFilterError(DashboardEngineError):
    code = "invalid_filter"
    status_code = 400

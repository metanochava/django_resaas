"""Contratos de resposta normalizados por tipo de widget + formato de
erro padronizado - ver `ApiResponse.fail` (saas/core/utils/
api_response.py) para o padrão de erro já existente no projecto, que
este formato mantém compatível (uma mensagem + status), estendido com
`code`/`fields` para os casos estruturados (filtro inválido)."""


class DashboardResponseService:

    @staticmethod
    def widget_response(widget_type, data):
        return {
            "type": widget_type,
            "data": data,
        }

    @staticmethod
    def error_response(exc):
        payload = {
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        }

        if exc.fields:
            payload["error"]["fields"] = exc.fields

        return payload, exc.status_code

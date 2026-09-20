"""The Entity of the request being served, for code that runs without the
request in hand (model signals). Set by TenantContextMiddleware from the
signed X-RESAAS-Context, so it is exactly request.entity_id - never anything
the client can pick freely. None outside a request (shell, commands, tasks)."""
from contextvars import ContextVar

_entity_id = ContextVar("resaas_current_entity_id", default=None)


def current_entity_id():
    return _entity_id.get()


def set_current_entity_id(value):
    return _entity_id.set(value)


def reset_current_entity_id(token):
    _entity_id.reset(token)

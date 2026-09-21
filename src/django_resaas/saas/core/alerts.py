"""Alerts: extra messages a request wants the user to see next to its normal result.

    {"...normal payload...", "alerts": [{"level": "warning", "message": "...",
                                         "code": "employee_without_profile", "details": null}]}

An alert is NOT the failure of the request (that is `error`, see
core/exceptions/handler.py) and a failed request must not repeat its error here.

    level    success | info | warning | error   (backend vocabulary - the frontend maps
             it to its own components, e.g. error -> Quasar "negative")
    message  required, human text, translated with the request's language
    code     optional, stable, technical, never translated
    details  optional, structured extra data

Usage - anywhere a `request` is at hand (view, action, service):

    from django_resaas.saas.core.alerts import add_alert
    add_alert(request, "The employee has no profile yet.", level="warning",
              code="employee_without_profile")

Alerts live on the request (never in module state), so concurrent requests cannot
see each other's. ResaasResponseMixin (BaseAPIView and the legacy viewsets) merges
them into the JSON body of the response, whatever its status.
"""
from django_resaas.saas.core.utils.translate import Translate

LEVELS = ("success", "info", "warning", "error")

_ATTR = "_resaas_alerts"


def build_alert(request, message, level="info", code=None, details=None):
    if level not in LEVELS:
        raise ValueError(f"Unknown alert level {level!r}; use one of {', '.join(LEVELS)}.")

    if not message:
        raise ValueError("An alert needs a message.")

    alert = {"level": level, "message": Translate.tdc(request, str(message))}

    if code:
        alert["code"] = code

    alert["details"] = details

    return alert


def add_alert(request, message, level="info", code=None, details=None):
    """Queue an alert on this request. Returns the alert dict."""
    alert = build_alert(request, message, level=level, code=code, details=details)

    # DRF's Request proxies attribute reads to the HttpRequest, but writes
    # must land on the underlying request so a later read sees them
    target = getattr(request, "_request", request)
    queue = getattr(target, _ATTR, None)

    if queue is None:
        queue = []
        setattr(target, _ATTR, queue)

    queue.append(alert)

    return alert


def pending_alerts(request):
    target = getattr(request, "_request", request)

    return list(getattr(target, _ATTR, None) or [])


def merge_alerts(request, data):
    """Return `data` with the request's alerts in `data["alerts"]` (added to any the
    view already put there). Only a dict payload can carry them; anything else
    (a bare list, a file) is returned untouched."""
    queued = pending_alerts(request)

    if not queued or not isinstance(data, dict):
        return data

    existing = data.get("alerts")
    merged = list(existing) if isinstance(existing, (list, tuple)) else []

    return {**data, "alerts": merged + queued}

"""The RESAAS API exception handler (built ON DRF's, not instead of it).

CONTRACT
--------
A failed request answers, next to its HTTP status (never repeated in the body),
with exactly one top-level key:

    {"error": {"code": "...", "message": "...", "details": ...}}

    message  always; human text, translated (Translate.tdc) with the request's language
    code     only when the caller must tell this condition apart programmatically;
             stable, technical, NEVER translated (DRF's generic "error"/"invalid" are omitted)
    details  structured extra data, null when there is none; for validation errors it
             is the field -> [messages] map, so a form can put each message on its field

The body used to also carry {"detail": "...", "code": "..."} (+ the bare {"field":
["msg"]} map for validation) as DEPRECATED aliases of `error`, kept for older
consumers. Every consumer (django_resaas, quasar_resaas, dev/front, pro/front) has
been migrated onto `error`/`errorMessage()`/`errorCode()` - see
utils/apiContract.js in quasar_resaas - so the aliases were removed instead of kept
forever. New code must read `error` only; nothing reads `detail` or a top-level
`code` any more.

NEVER LEAKS
-----------
An unexpected exception is logged in full on the server and answered with a generic
message - no traceback, SQL, path or value. With DEBUG on, Django's own debug page
is kept (the exception is re-raised) so development is not blinded.
"""
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response

from django_resaas.saas.core.utils.translate import Translate

logger = logging.getLogger(__name__)

VALIDATION_MESSAGE = "Please correct the highlighted fields."
SERVER_ERROR_MESSAGE = "An unexpected error occurred. Please try again later."

# DRF codes that say nothing a client could branch on
GENERIC_CODES = {"error", "invalid"}


def error_body(message, code=None, details=None):
    error = {"message": message}

    if code:
        error["code"] = code

    error["details"] = details

    return {"error": error}


def _translate(request, value):
    if isinstance(value, str) and request is not None:
        return Translate.tdc(request, value)

    return value


def _translate_details(request, value):
    """Translate every message inside a details structure, keep its shape."""
    if isinstance(value, dict):
        return {key: _translate_details(request, item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_translate_details(request, item) for item in value]

    return _translate(request, str(value)) if value is not None else value


def _plain(value):
    """DRF ErrorDetail -> plain str, recursively (JSON-safe, no leaking classes)."""
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]

    return str(value) if value is not None else value


def _code_of(exc):
    """The stable code to publish, or None when there is nothing worth branching on."""
    explicit = getattr(exc, "resaas_code", None)

    if explicit:
        return explicit

    detail = exc.detail
    code = None if isinstance(detail, (dict, list)) else getattr(detail, "code", None)
    code = code or getattr(exc, "default_code", None)

    return None if not code or code in GENERIC_CODES else code


def _body_for(exc, request):
    """The {"error": {...}} body for a known API exception."""
    detail = exc.detail

    # A non-validation exception raised with {"code": ..., "detail": ...} (the
    # pattern some views already use) is one error with a stable code, not a field map.
    if isinstance(detail, dict) and not isinstance(exc, exceptions.ValidationError) and "detail" in detail:
        code = detail.get("code")
        code = str(code) if code else None
        message = _translate(request, str(detail["detail"]))

        return error_body(message, code=code, details=None)

    if isinstance(exc, exceptions.ValidationError) or isinstance(detail, (dict, list)):
        details = _translate_details(request, _plain(detail))
        message = _translate(request, VALIDATION_MESSAGE)

        return error_body(message, code=getattr(exc, "resaas_code", None), details=details)

    message = _translate(request, str(detail))
    code = _code_of(exc)
    extra = _translate_details(request, _plain(getattr(exc, "resaas_details", None)))

    return error_body(message, code=code, details=extra)


def resaas_exception_handler(exc, context):
    request = context.get("request") if context else None

    # Django's own not-found / permission errors become DRF's, exactly as DRF does
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    # imported here, not at module level: this module is reached from
    # core.utils, which settings.py imports while REST_FRAMEWORK is not defined
    # yet. Importing rest_framework.views that early freezes DRF's DEFAULTS
    # (authentication, pagination, ...) for the whole process.
    from rest_framework.views import exception_handler as drf_exception_handler

    response = drf_exception_handler(exc, context)

    if response is not None and isinstance(exc, exceptions.APIException):
        response.data = _body_for(exc, request)

        return response

    if response is not None:
        return response

    # -------- unexpected exception --------
    logger.exception("Unhandled exception in %s", getattr(context.get("view"), "__class__", type(None)).__name__ if context else "?")

    if settings.DEBUG:
        return None  # keep Django's debug page for developers

    return Response(
        error_body(_translate(request, SERVER_ERROR_MESSAGE)),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def error_response(request, message, status_code=status.HTTP_400_BAD_REQUEST, code=None, details=None):
    """A failed answer built by hand (the view decided the error itself, nothing was
    raised). Same contract as an exception answer - {"error": {...}} only."""
    text = _translate(request, message)
    body = error_body(text, code=code, details=_translate_details(request, details))

    return Response(body, status=status_code)

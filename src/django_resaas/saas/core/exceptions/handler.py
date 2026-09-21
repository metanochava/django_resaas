"""The RESAAS API exception handler (built ON DRF's, not instead of it).

CONTRACT
--------
A failed request answers, next to its HTTP status (never repeated in the body):

    {"error": {"code": "...", "message": "...", "details": ...}}

    message  always; human text, translated (Translate.tdc) with the request's language
    code     only when the caller must tell this condition apart programmatically;
             stable, technical, NEVER translated (DRF's generic "error"/"invalid" are omitted)
    details  structured extra data, null when there is none; for validation errors it
             is the field -> [messages] map, so a form can put each message on its field

COMPATIBILITY (DEPRECATED aliases)
----------------------------------
The API used to answer {"detail": "..."} (+ top-level "code") and, for validation,
the bare {"field": ["msg"]} map. Existing consumers still read those, so they are
kept next to `error` until nothing depends on them. New code reads `error` only.

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
    """(body, legacy) for a known API exception."""
    detail = exc.detail

    # A non-validation exception raised with {"code": ..., "detail": ...} (the
    # pattern some views already use) is one error with a stable code, not a field map.
    if isinstance(detail, dict) and not isinstance(exc, exceptions.ValidationError) and "detail" in detail:
        original = str(detail["detail"])
        code = detail.get("code")
        code = str(code) if code else None
        message = _translate(request, original)
        legacy = {"detail": original}

        if code:
            legacy["code"] = code

        return error_body(message, code=code, details=None), legacy

    if isinstance(exc, exceptions.ValidationError) or isinstance(detail, (dict, list)):
        details = _translate_details(request, _plain(detail))
        message = _translate(request, VALIDATION_MESSAGE)
        body = error_body(message, code=getattr(exc, "resaas_code", None), details=details)

        # DEPRECATED alias: the bare field map DRF always answered
        legacy = dict(details) if isinstance(details, dict) else {"non_field_errors": details}

        return body, legacy

    original = str(detail)
    message = _translate(request, original)
    code = _code_of(exc)
    extra = _translate_details(request, _plain(getattr(exc, "resaas_details", None)))
    body = error_body(message, code=code, details=extra)

    # DEPRECATED aliases: {"detail": ..., "code": ...}. `detail` is the text exactly as
    # the exception carried it (untranslated, as it always was): consumers that compare
    # it must keep working. New code reads `error.code` / `error.message`.
    legacy = {"detail": original}

    if code:
        legacy["code"] = code

    return body, legacy


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
        body, legacy = _body_for(exc, request)

        # `error` wins over any legacy key of the same name
        response.data = {**legacy, **body}

        return response

    if response is not None:
        return response

    # -------- unexpected exception --------
    logger.exception("Unhandled exception in %s", getattr(context.get("view"), "__class__", type(None)).__name__ if context else "?")

    if settings.DEBUG:
        return None  # keep Django's debug page for developers

    return Response(
        {**{"detail": _translate(request, SERVER_ERROR_MESSAGE)}, **error_body(_translate(request, SERVER_ERROR_MESSAGE))},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def error_response(request, message, status_code=status.HTTP_400_BAD_REQUEST, code=None, details=None):
    """A failed answer built by hand (the view decided the error itself, nothing was
    raised). Same contract - and same deprecated aliases - as an exception answer."""
    text = _translate(request, message)
    body = error_body(text, code=code, details=_translate_details(request, details))
    legacy = {"detail": text}

    if code:
        legacy["code"] = code

    return Response({**legacy, **body}, status=status_code)

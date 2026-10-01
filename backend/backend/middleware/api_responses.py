"""Consistent error envelopes for Django REST Framework API responses."""

import logging

from django.http import JsonResponse
from rest_framework.exceptions import ErrorDetail
from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _message(value):
    if isinstance(value, (str, ErrorDetail)) and str(value).strip():
        return str(value).strip()
    if isinstance(value, (list, tuple)):
        return " ".join(filter(None, (_message(item) for item in value)))
    if isinstance(value, dict):
        for key in ("message", "detail", "error"):
            candidate = _message(value.get(key))
            if candidate:
                return candidate
        return " ".join(filter(None, (_message(item) for item in value.values())))
    return ""


def error_envelope(data, status_code):
    """Convert any API error payload into the public error response contract."""
    data = data if isinstance(data, dict) else {"details": data}
    is_server_error = status_code >= 500

    details = data.get("details", data.get("errors"))
    if details is None:
        details = {
            key: value
            for key, value in data.items()
            if key not in {"code", "message", "detail", "error", "status"}
        }

    message = (
        "An unexpected server error occurred."
        if is_server_error
        else _message(data.get("message") or data.get("detail") or data.get("error"))
        or _message(details)
        or "The request could not be processed."
    )
    code = data.get("code")
    if not isinstance(code, (str, int, ErrorDetail)) or not str(code).strip():
        code = f"http_{status_code}"

    return {
        "code": str(code),
        "message": message,
        "details": {} if is_server_error else details,
    }


def api_exception_handler(exc, context):
    """Apply the API error envelope to all handled DRF exceptions."""
    response = drf_exception_handler(exc, context)
    if response is None:
        logger.error(
            "Unhandled API exception",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return Response(error_envelope({}, 500), status=500)

    response.data = error_envelope(response.data, response.status_code)
    return response


class APIErrorRendererMixin:
    """Normalize manually returned DRF error responses as well as exceptions."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")
        if response is not None and response.status_code >= 400:
            data = error_envelope(data, response.status_code)
        return super().render(data, accepted_media_type, renderer_context)


class APIJSONRenderer(APIErrorRendererMixin, JSONRenderer):
    pass


class APIBrowsableRenderer(APIErrorRendererMixin, BrowsableAPIRenderer):
    pass


def api_json_error(message, status_code, details=None, code=None):
    """Return the shared error contract from non-DRF Django API views."""
    payload = {"message": message, "details": {} if details is None else details}
    if code is not None:
        payload["code"] = code
    return JsonResponse(error_envelope(payload, status_code), status=status_code)

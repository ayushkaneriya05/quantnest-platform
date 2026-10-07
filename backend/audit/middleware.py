from .services import audit_request


class AuditContextMiddleware:
    """Expose request attribution to shared services, including nested model saves."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = audit_request.set(request)
        try:
            return self.get_response(request)
        finally:
            audit_request.reset(token)

"""Trust ingress headers only after authenticating the configured edge proxy."""
import hmac
import hashlib
import base64
import re
from ipaddress import ip_address
from django.conf import settings
from django.http import JsonResponse


class TrustedIngressMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        response = None
        expected = settings.QUANTNEST_PROXY_TOKEN
        token = request.headers.get("X-QuantNest-Proxy-Token", "")
        trusted = bool(expected and hmac.compare_digest(expected.encode(), token.encode()))
        if settings.QUANTNEST_DEPLOYMENT_MODE == "public" and request.path != "/api/v1/research/tools/":
            if not trusted:
                response = JsonResponse({
                    "code": "untrusted_ingress",
                    "message": "The application gateway could not be verified. Open QuantNest using its configured site URL or contact support.",
                }, status=403)
        if trusted:
            # Gateways overwrite this single-address header. Standard forwarded
            # chains are not used: proxies can append or replace their contents.
            try:
                client = ip_address(request.headers.get("X-QuantNest-Client-IP", ""))
                request.META["REMOTE_ADDR"] = str(getattr(client, "ipv4_mapped", None) or client)
            except ValueError:
                pass
        if response is None:
            response = self.get_response(request)
        if request.path.startswith(("/api/", "/admin/", "/ws/")):
            response["Cache-Control"] = "private, no-store"
            if "Content-Security-Policy" not in response:
                hashes = []
                if not response.streaming and response.get("Content-Type", "").startswith("text/html"):
                    for attributes, script in re.findall(rb"<script\b([^>]*)>([\s\S]*?)</script>", response.content, re.I):
                        if script and not re.search(rb"\bsrc\s*=", attributes, re.I):
                            hashes.append("'sha256-" + base64.b64encode(hashlib.sha256(script).digest()).decode() + "'")
                response["Content-Security-Policy"] = "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; script-src 'self' " + " ".join(hashes) + "; style-src 'self' 'unsafe-inline'; img-src 'self' data:; form-action 'self'"
            response["X-Content-Type-Options"] = "nosniff"
        return response


class TrustedWebSocketIngress:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if settings.QUANTNEST_DEPLOYMENT_MODE == "public":
            secret = settings.QUANTNEST_PROXY_TOKEN.encode()
            tokens = [value for key, value in scope.get("headers", []) if key.lower() == b"x-quantnest-proxy-token"]
            if not secret or len(tokens) != 1 or not hmac.compare_digest(tokens[0], secret):
                await send({"type": "websocket.close", "code": 4403})
                return
        await self.app(scope, receive, send)

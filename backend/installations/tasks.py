import httpx
from celery import shared_task
from django.conf import settings


@shared_task(name="installations.refresh")
def refresh_installation_licence_task():
    if settings.QUANTNEST_DEPLOYMENT_MODE != "private" or not settings.LICENSE_SERVER_URL:
        return "not_configured"
    from urllib.parse import urlparse
    if urlparse(settings.LICENSE_SERVER_URL).scheme != "https":
        raise ValueError("Licence refresh requires HTTPS")
    response = httpx.post(settings.LICENSE_SERVER_URL.rstrip("/") + "/api/v1/installations/refresh/",
        headers={"Authorization": "Bearer " + settings.LICENSE_ACTIVATION_TOKEN},
        json={"installation_id": settings.LICENSE_INSTALLATION_ID}, timeout=15, follow_redirects=False)
    response.raise_for_status()
    from .licensing import import_installation_licence
    claims = import_installation_licence(response.json()["licence"])
    return {"revision": claims["revision"]}

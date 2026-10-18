"""Lease refresh and rollback protection run outside tick evaluation."""
import hashlib
from datetime import timedelta, datetime, timezone as utc
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from commercial.usage import reject_request
from core.lifecycle import require_execution_scope
from .models import Installation, LicenseIssuance, LocalLicenseState
from .signing import sign_licence, verify_licence


def issue_installation_licence(installation):
    contract = installation.contract
    now = timezone.now()
    if not installation.enabled or not contract.approved:
        reject_request("installation_not_approved", "This installation has no active approval.")
    perpetual = contract.rights == "perpetual"
    paid = contract.paid_through if not perpetual else datetime(9999, 12, 31, tzinfo=utc.utc)
    if not paid or paid <= now:
        reject_request("licence_expired", "The renewable licence is past its paid-through time.")
    expires = paid if perpetual else min(paid, contract.offline_until if contract.offline_until and contract.offline_until > now else now + timedelta(hours=24))
    live_until = contract.live_approved_until
    live_approved = bool(live_until and live_until > now and contract.approval_reference and contract.qualified_integrations)
    claims = {"schema_version": 3, "iss": "quantnest-licensing", "aud": str(installation.pk), "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()), "paid_through": int(paid.timestamp()), "rights": contract.rights,
        "revision": contract.revision,
        "supported_releases": contract.supported_releases,
        "qualified_integrations": contract.qualified_integrations,
        "live_approved_until": int(live_until.timestamp()) if live_approved else 0,
        "offline": perpetual or bool(contract.offline_until and contract.offline_until > now)}
    token = sign_licence(claims)
    with transaction.atomic():
        current = Installation.objects.select_for_update().select_related("contract").get(pk=installation.pk)
        from .models import PrivateContract
        current_contract = PrivateContract.objects.select_for_update().get(pk=current.contract_id)
        if not current.enabled or not current_contract.approved or current_contract.revision != contract.revision:
            reject_request("licence_changed", "Approval changed during signing. Refresh the installation again.")
        LicenseIssuance.objects.create(installation=installation, revision=contract.revision,
            key_id=settings.OCI_LICENSE_KEY_VERSION, token_hash=hashlib.sha256(token.encode()).hexdigest(), issued_at=now, expires_at=expires)
        Installation.objects.filter(pk=installation.pk).update(last_refresh=now)
    return token


@transaction.atomic
def import_installation_licence(token):
    claims = verify_licence(token, settings.LICENSE_INSTALLATION_ID)
    now = timezone.now()
    row, _ = LocalLicenseState.objects.select_for_update().get_or_create(installation_id=settings.LICENSE_INSTALLATION_ID,
        defaults={"token": token, "last_seen": now, "highest_revision": claims["revision"]})
    if claims["revision"] < row.highest_revision or now < row.last_seen - timedelta(seconds=120):
        reject_request("licence_rollback", "The licence revision or local clock moved backwards.")
    if row.token != token and claims["revision"] == row.highest_revision:
        previous = verify_licence(row.token, settings.LICENSE_INSTALLATION_ID)
        if claims["iat"] < previous["iat"] or claims["exp"] < previous["exp"]:
            reject_request("licence_rollback", "A newer lease has already been accepted.")
    row.token, row.highest_revision, row.last_seen = token, max(row.highest_revision, claims["revision"]), now
    row.save(update_fields=["token", "highest_revision", "last_seen"])
    return claims


def get_local_entitlements():
    if settings.QUANTNEST_DEPLOYMENT_MODE != "private":
        return {"allow_entries": False, "reason": "not_private"}
    try:
        with transaction.atomic():
            row = LocalLicenseState.objects.select_for_update().get(installation_id=settings.LICENSE_INSTALLATION_ID)
            now = timezone.now()
            claims = verify_licence(row.token, settings.LICENSE_INSTALLATION_ID, now=now)
            if claims.get("supported_releases") and settings.QUANTNEST_RELEASE not in claims["supported_releases"]:
                raise ValueError("unsupported_software_release")
            if claims["revision"] < row.highest_revision or now < row.last_seen - timedelta(seconds=120):
                raise ValueError("licence_rollback")
            lease_end = claims["exp"] if claims.get("offline") else claims["exp"] + 48 * 3600
            deadline = min(lease_end, claims["paid_through"])
            current = now.timestamp()
            expired = current >= deadline
            if expired:
                row.resume_required = True
            row.last_seen = max(now, row.last_seen)
            row.save(update_fields=["last_seen", "resume_required"])
            return {"allow_entries": not expired and not row.resume_required,
                "live_approved": current < claims.get("live_approved_until", 0),
                "revision": claims["revision"], "paid_through": claims["paid_through"],
                "lease_expires": claims["exp"], "rights": claims.get("rights", "renewable"), "offline": bool(claims.get("offline")),
                "qualified_integrations": claims["qualified_integrations"],
                "reason": "licence_expired" if expired else "renewal_resume_required" if row.resume_required else "",
                "in_grace": current > claims["exp"], "maintenance": "separate_from_continuing_use_rights"}
    except Exception as exc:
        return {"allow_entries": False, "reason": "licence_unavailable", "error_code": type(exc).__name__}


def require_active_licence():
    """Private work is unlimited while continuing-use rights remain active."""
    if settings.QUANTNEST_DEPLOYMENT_MODE != "private":
        return
    licence = get_local_entitlements()
    if not licence["allow_entries"]:
        reject_request(licence["reason"], "Activate or renew the installation licence before starting new work.")
    return licence


def require_broker_access(broker_name):
    require_execution_scope("live")
    if settings.QUANTNEST_DEPLOYMENT_MODE == "development":
        return
    licence = require_active_licence()
    if not licence:
        reject_request("private_broker_required", "Execution accounts require a Private installation.")
    if not licence["live_approved"]:
        reject_request("live_not_qualified", "Live execution qualification is missing or expired for this installation.")
    if broker_name not in licence["qualified_integrations"]:
        reject_request("broker_not_qualified", "This broker has not been qualified for the installation.")

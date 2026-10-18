import uuid
from django.conf import settings
from django.db import models


class PrivateContract(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reference = models.CharField(max_length=150, unique=True)
    rights = models.CharField(max_length=20, choices=[("renewable", "Renewable"), ("perpetual", "Perpetual continuing-use rights")])
    paid_through = models.DateTimeField(null=True, blank=True)
    maintenance_through = models.DateTimeField(null=True, blank=True)
    offline_until = models.DateTimeField(null=True, blank=True)
    approval_reference = models.CharField(max_length=300, blank=True)
    live_approved_until = models.DateTimeField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
    supported_releases = models.JSONField(default=list, blank=True)
    support_terms = models.TextField(blank=True)
    setup_minor = models.PositiveIntegerField(default=0)
    recurring_minor = models.PositiveIntegerField(default=0)
    qualified_integrations = models.JSONField(default=list, blank=True)
    deployment_scope = models.TextField(blank=True)

    def __str__(self):
        return self.reference

    def clean(self):
        from django.core.exceptions import ValidationError
        if not isinstance(self.qualified_integrations, list) or any(not isinstance(value, str) for value in self.qualified_integrations):
            raise ValidationError({"qualified_integrations": "Enter a list of qualified broker identifiers."})
        if not isinstance(self.supported_releases, list) or any(not isinstance(value, str) for value in self.supported_releases):
            raise ValidationError({"supported_releases": "Enter a list of software release identifiers."})
        if self.approved and self.rights == "renewable" and not self.paid_through:
            raise ValidationError({"paid_through": "A renewable licence requires an agreed paid-through date."})
        if self.approved and self.live_approved_until and (not self.approval_reference or not self.qualified_integrations):
            raise ValidationError("Live qualification requires an approval reference and qualified broker identifiers.")
        if self.approved and not self.deployment_scope:
            raise ValidationError({"deployment_scope": "Describe the agreed deployment scope before approving."})


class Installation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(PrivateContract, on_delete=models.PROTECT)
    activation_hash = models.CharField(max_length=64)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_refresh = models.DateTimeField(null=True)


class LicenseIssuance(models.Model):
    installation = models.ForeignKey(Installation, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField()
    key_id = models.CharField(max_length=200)
    token_hash = models.CharField(max_length=64)
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    reason = models.CharField(max_length=40, default="refresh")


class LocalLicenseState(models.Model):
    installation_id = models.UUIDField(unique=True)
    token = models.TextField()
    highest_revision = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField()
    resume_required = models.BooleanField(default=False)


class SupportAuthorization(models.Model):
    installation = models.ForeignKey(Installation, on_delete=models.PROTECT)
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    scope = models.CharField(max_length=120)
    authorized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="private_support_authorizations")
    valid_until = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

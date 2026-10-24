import uuid
from django.conf import settings
from django.db import models


from .catalog import REQUEST_TYPES, TICKET_STATUS_LABELS


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    name = models.CharField(max_length=120, blank=True)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    subject = models.CharField(max_length=180)
    body = models.TextField(max_length=10000)
    status = models.CharField(max_length=25, default="received", choices=list(TICKET_STATUS_LABELS.items()))
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_tickets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} ({self.email})"


class Reply(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    body = models.TextField(max_length=10000)
    staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class ErasureRequest(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

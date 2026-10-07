import uuid

from django.db import migrations, models


def expire_untracked_sessions(apps, schema_editor):
    # Old records have no browser identity or refresh-token ownership.
    apps.get_model("users", "UserSession").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("users", "0005_remove_usersession_jti_usersession_session_id")]

    operations = [
        migrations.RunPython(expire_untracked_sessions, migrations.RunPython.noop),
        migrations.AddField(
            model_name="usersession", name="device_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AddField(
            model_name="usersession", name="refresh_jti",
            field=models.CharField(max_length=255, editable=False, default=""),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="usersession",
            constraint=models.UniqueConstraint(fields=("user", "device_id"), name="unique_user_browser_session"),
        ),
    ]

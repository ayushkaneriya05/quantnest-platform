from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_browser_sessions"),
    ]

    operations = [
        migrations.DeleteModel(name="APIKey"),
    ]

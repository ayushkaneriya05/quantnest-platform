from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("paper_trading", "0010_remove_capitalallocation_include_charges"),
    ]

    operations = [
        migrations.AddField(
            model_name="paperorder",
            name="reason",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]

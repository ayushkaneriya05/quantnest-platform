from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("risk_management", "0011_strategyautodisable_form_defaults"),
    ]

    operations = [
        migrations.DeleteModel(name="RiskViolation"),
        migrations.DeleteModel(name="PortfolioRiskProfile"),
    ]

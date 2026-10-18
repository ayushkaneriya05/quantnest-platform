from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("commercial", "0010_remove_operationalapproval")]

    operations = [
        migrations.DeleteModel(name="Expenditure"),
        migrations.DeleteModel(name="OperatingCost"),
        migrations.DeleteModel(name="FinancialReview"),
        migrations.DeleteModel(name="ProviderRate"),
    ]

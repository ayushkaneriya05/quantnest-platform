from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("commercial", "0013_remove_subscription_resume_required"),
        ("customer_support", "0009_remove_product_analytics"),
    ]

    operations = [migrations.DeleteModel(name="DeliveryJob")]

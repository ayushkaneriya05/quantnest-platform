from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('customer_support', '0005_remove_demo_onboarding_step')]
    operations = [
        migrations.DeleteModel(name='Onboarding'),
        migrations.AlterField(
            model_name='ticket', name='request_type',
            field=models.CharField(max_length=20, choices=[
                ('general', 'General enquiry'), ('custom', 'Custom development'),
                ('private', 'Private deployment'), ('support', 'Product support'),
                ('feedback', 'Feedback or suggestion'), ('grievance', 'Grievance'),
                ('security', 'Security report'),
            ]),
        ),
    ]

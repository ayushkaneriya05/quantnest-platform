from django.db import migrations


def remove_old_ai_engine(apps, schema_editor):
    # The removed app is no longer installed. Drop only its four owned tables.
    tables = set(schema_editor.connection.introspection.table_names())
    for table in ("overfit_detection", "strategy_health_score", "market_regime", "ai_recommendation"):
        if table in tables:
            schema_editor.execute(f"DROP TABLE {schema_editor.quote_name(table)}")
    apps.get_model("contenttypes", "ContentType").objects.filter(app_label="ai_engine").delete()


class Migration(migrations.Migration):
    dependencies = [("research", "0001_initial"), ("contenttypes", "0002_remove_content_type_name")]
    operations = [migrations.RunPython(remove_old_ai_engine)]

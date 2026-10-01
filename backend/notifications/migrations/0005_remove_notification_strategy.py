from django.db import migrations


def copy_strategy_context_to_data(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    Strategy = apps.get_model("strategies", "Strategy")
    database = schema_editor.connection.alias

    strategy_ids = set(
        Notification.objects.using(database)
        .exclude(strategy_id__isnull=True)
        .values_list("strategy_id", flat=True)
    )
    strategy_names = dict(
        Strategy.objects.using(database)
        .filter(pk__in=strategy_ids)
        .values_list("pk", "name")
    )

    batch = []
    for notification in (
        Notification.objects.using(database)
        .exclude(strategy_id__isnull=True)
        .only("id", "strategy_id", "data")
        .iterator()
    ):
        data = notification.data if isinstance(notification.data, dict) else {}
        data = dict(data)
        data.setdefault("strategy_id", str(notification.strategy_id))
        strategy_name = strategy_names.get(notification.strategy_id)
        if strategy_name:
            data.setdefault("strategy_name", strategy_name)
        notification.data = data
        batch.append(notification)
        if len(batch) >= 500:
            Notification.objects.using(database).bulk_update(batch, ["data"])
            batch.clear()

    if batch:
        Notification.objects.using(database).bulk_update(batch, ["data"])


def restore_strategy_context(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    Strategy = apps.get_model("strategies", "Strategy")
    database = schema_editor.connection.alias

    notifications = Notification.objects.using(database).only("id", "data").iterator()
    batch = []

    def restore_batch():
        if not batch:
            return
        valid_ids = {item.strategy_id for item in batch}
        existing_ids = {
            str(strategy_id)
            for strategy_id in Strategy.objects.using(database)
            .filter(pk__in=valid_ids)
            .values_list("pk", flat=True)
        }
        for item in batch:
            if str(item.strategy_id) not in existing_ids:
                item.strategy_id = None
        Notification.objects.using(database).bulk_update(batch, ["strategy"])
        batch.clear()

    for notification in notifications:
        data = notification.data if isinstance(notification.data, dict) else {}
        strategy_id = data.get("strategy_id")
        if strategy_id is None:
            continue
        notification.strategy_id = strategy_id
        batch.append(notification)
        if len(batch) >= 500:
            restore_batch()

    restore_batch()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0004_unify_notification_types"),
        ("strategies", "0022_alter_strategy_status"),
    ]

    operations = [
        migrations.RunPython(copy_strategy_context_to_data, restore_strategy_context),
        migrations.RemoveField(model_name="notification", name="strategy"),
    ]

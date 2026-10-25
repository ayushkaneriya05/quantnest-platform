"""Replace the old first-watchlist flag without changing recorded instrument evidence."""

from django.db import migrations


def select_named_watchlists(apps, schema_editor):
    database = schema_editor.connection.alias
    Watchlist = apps.get_model("trading", "Watchlist")
    first_watchlists = {}
    for watchlist in Watchlist.objects.using(database).order_by("pk").values("id", "user_id", "name"):
        first_watchlists.setdefault(watchlist["user_id"], watchlist)

    for model_name, field in (("ResearchSession", "context"), ("ResearchRun", "request")):
        Model = apps.get_model("research", model_name)
        for record in Model.objects.using(database).only("pk", "user_id", field).iterator():
            context = dict(getattr(record, field))
            if "use_watchlist" not in context:
                continue
            selected = context.pop("use_watchlist")
            watchlist = first_watchlists.get(record.user_id) if selected else None
            context["watchlist_id"] = watchlist["id"] if watchlist else None
            if watchlist:
                context["watchlist_name"] = watchlist["name"]
            Model.objects.using(database).filter(pk=record.pk).update(**{field: context})


class Migration(migrations.Migration):
    dependencies = [
        ("research", "0004_conversation_contract"),
        ("trading", "0014_named_watchlists_and_settlement"),
    ]
    operations = [migrations.RunPython(select_named_watchlists, migrations.RunPython.noop)]

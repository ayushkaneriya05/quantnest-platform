from rest_framework import serializers
from analytics.services import SOURCES
from .models import JournalEntry


class JournalEntrySerializer(serializers.ModelSerializer):
    notes = serializers.CharField(required=False, allow_blank=True, max_length=12000)
    lessons_learned = serializers.CharField(required=False, allow_blank=True, max_length=6000)
    mistake_tags = serializers.ListField(child=serializers.CharField(max_length=60), max_length=12, required=False)
    execution_quality = serializers.IntegerField(min_value=1, max_value=5, allow_null=True, required=False)

    class Meta:
        model = JournalEntry
        fields = ["id", "source", "terminal_trade", "paper_trade", "live_trade", "title", "notes",
                  "mistake_tags", "lessons_learned", "execution_quality", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request:
            for source in SOURCES.values():
                self.fields[source["review"]].queryset = source["model"].objects.filter(**{source["owner"]: request.user})

    def validate(self, attrs):
        if self.instance:
            for field in ("source", "terminal_trade", "paper_trade", "live_trade"):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError("A saved review cannot be moved to another execution source or trade.")
        source = attrs.get("source", getattr(self.instance, "source", None))
        relation = SOURCES[source]["review"]
        attached = [field for field in ("terminal_trade", "paper_trade", "live_trade")
                    if attrs.get(field, getattr(self.instance, field, None))]
        if attached != [relation]:
            raise serializers.ValidationError("Attach exactly one completed trade from the selected source.")
        if "mistake_tags" in attrs:
            attrs["mistake_tags"] = list(dict.fromkeys(tag.strip() for tag in attrs["mistake_tags"] if tag.strip()))
        return attrs

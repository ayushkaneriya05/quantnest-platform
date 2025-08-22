from rest_framework import serializers

class PulseResponseSerializer(serializers.Serializer):
    ai_summary = serializers.CharField()
    items = serializers.ListField()  # list of {title, url, source, published_at, sentiment}
    agg = serializers.DictField()    # {pos,neu,neg}
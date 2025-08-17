# backend/trading/serializers.py
from rest_framework import serializers
from .models import PaperOrder, PaperPosition, PaperTrade, PaperAccount, AuditLog

class PaperOrderSerializer(serializers.ModelSerializer):
    remaining_qty = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PaperOrder
        fields = [
            "id", "user", "symbol", "side", "qty", "order_type", "product_type",
            "price", "trigger_price", "status", "filled_qty", "avg_fill_price",
            "created_at", "updated_at",
            # bracket/oco fields
            "parent", "order_tag", "oco_group", "tp_price", "sl_price",
            # SL-M fields
            "is_slm", "stop_trigger_price",
            "remaining_qty",
        ]
        read_only_fields = ("id", "status", "filled_qty", "avg_fill_price", "created_at", "updated_at", "user")

    def get_remaining_qty(self, obj):
        return obj.remaining_qty()

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "order", "action", "performed_by", "timestamp", "details", "user"]
        read_only_fields = fields
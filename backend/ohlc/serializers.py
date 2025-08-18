# backend/ohlc/serializers.py
from rest_framework import serializers
from .models import OHLC

class OHLCSerializer(serializers.ModelSerializer):
    class Meta:
        model = OHLC
        fields = ['symbol', 'tf', 'ts', 'open', 'high', 'low', 'close', 'volume']
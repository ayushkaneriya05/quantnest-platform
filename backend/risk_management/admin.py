from django.contrib import admin
from .models import PositionSizingRule, StrategyAutoDisable


@admin.register(PositionSizingRule)
class PositionSizingRuleAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'sizing_method', 'capital_percentage', 'risk_per_trade_percentage']
    list_filter = ['sizing_method']


@admin.register(StrategyAutoDisable)
class StrategyAutoDisableAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy', 'trigger_type', 'threshold_value', 'is_active']
    list_filter = ['trigger_type', 'is_active']

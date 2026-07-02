from django.contrib import admin
from .models import (
    PositionSizingRule, PortfolioRiskProfile,
    StrategyAutoDisable, RiskViolation
)


@admin.register(PositionSizingRule)
class PositionSizingRuleAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'sizing_method', 'capital_percentage', 'risk_per_trade_percentage']
    list_filter = ['sizing_method']


@admin.register(PortfolioRiskProfile)
class PortfolioRiskProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'max_daily_loss_percentage', 'max_exposure_percentage', 'max_drawdown_percentage']
    list_filter = ['alert_on_breach']


@admin.register(StrategyAutoDisable)
class StrategyAutoDisableAdmin(admin.ModelAdmin):
    list_display = ['name', 'strategy', 'trigger_type', 'threshold_value', 'is_active']
    list_filter = ['trigger_type', 'is_active', 'require_manual_review']


@admin.register(RiskViolation)
class RiskViolationAdmin(admin.ModelAdmin):
    list_display = ['violation_type', 'severity', 'user', 'strategy', 'action_taken', 'is_resolved', 'created_at']
    list_filter = ['violation_type', 'severity', 'action_taken', 'is_resolved']
    search_fields = ['user__username', 'message']
    readonly_fields = ['created_at', 'updated_at']

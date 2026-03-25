from django.contrib import admin
from .models import TimeRule, SpecialEventFilter, RuleGroup, Rule, StopLossRule, TargetRule


@admin.register(TimeRule)
class TimeRuleAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'candle_timeframe', 'market_session', 'start_time', 'end_time']
    list_filter = ['candle_timeframe', 'market_session']


@admin.register(SpecialEventFilter)
class SpecialEventFilterAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'avoid_earnings', 'avoid_news', 'avoid_expiry_day']


class RuleInline(admin.TabularInline):
    model = Rule
    extra = 0


@admin.register(RuleGroup)
class RuleGroupAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'name', 'rule_type', 'logical_operator', 'priority', 'is_active']
    list_filter = ['rule_type', 'logical_operator', 'is_active']
    inlines = [RuleInline]


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ['rule_group', 'category', 'is_active']
    list_filter = ['category', 'is_active']


@admin.register(StopLossRule)
class StopLossRuleAdmin(admin.ModelAdmin):
    list_display = ['rule_group', 'sl_type', 'is_active']
    list_filter = ['sl_type', 'is_active']


@admin.register(TargetRule)
class TargetRuleAdmin(admin.ModelAdmin):
    list_display = ['rule_group', 'target_type', 'is_active']
    list_filter = ['target_type', 'is_active']

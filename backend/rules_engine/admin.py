from django.contrib import admin
from .models import TimeRule, SpecialEventFilter, RuleGroup, Rule


@admin.register(TimeRule)
class TimeRuleAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'candle_timeframe', 'market_session', 'start_time', 'end_time']
    list_filter = ['candle_timeframe', 'market_session']


@admin.register(SpecialEventFilter)
class SpecialEventFilterAdmin(admin.ModelAdmin):
    list_display = ['strategy', 'avoid_earnings', 'avoid_news']


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
    list_display = ['rule_group', 'operand_a_type', 'comparison', 'operand_b_type', 'is_active']
    list_filter = ['operand_a_type', 'operand_b_type', 'is_active']

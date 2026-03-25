"""
Views for the rules_engine app.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import TimeRule, SpecialEventFilter, RuleGroup, Rule, StopLossRule, TargetRule
from .serializers import (
    TimeRuleSerializer, SpecialEventFilterSerializer,
    RuleGroupSerializer, RuleGroupCreateSerializer, RuleSerializer,
    StopLossRuleSerializer, TargetRuleSerializer
)


class TimeRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for time rules."""
    serializer_class = TimeRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        qs = TimeRule.objects.filter(strategy__user=self.request.user)
        strategy_id = self.request.query_params.get('strategy')
        if strategy_id:
            qs = qs.filter(strategy_id=strategy_id)
        return qs


class SpecialEventFilterViewSet(viewsets.ModelViewSet):
    """ViewSet for special event filters."""
    serializer_class = SpecialEventFilterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        qs = SpecialEventFilter.objects.filter(strategy__user=self.request.user)
        strategy_id = self.request.query_params.get('strategy')
        if strategy_id:
            qs = qs.filter(strategy_id=strategy_id)
        return qs


class RuleGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for rule groups."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return RuleGroup.objects.filter(
            strategy__user=self.request.user
        ).prefetch_related('rules')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RuleGroupCreateSerializer
        return RuleGroupSerializer
    
    @action(detail=False, methods=['get'])
    def by_strategy(self, request):
        """Get all rule groups for a strategy."""
        strategy_id = request.query_params.get('strategy_id')
        rule_type = request.query_params.get('type', None)
        
        qs = self.get_queryset().filter(strategy_id=strategy_id)
        if rule_type:
            qs = qs.filter(rule_type=rule_type)
        
        serializer = RuleGroupSerializer(qs, many=True)
        return Response(serializer.data)


class RuleViewSet(viewsets.ModelViewSet):
    """ViewSet for individual rules."""
    serializer_class = RuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Rule.objects.filter(rule_group__strategy__user=self.request.user)


class StopLossRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for stop loss rules."""
    serializer_class = StopLossRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return StopLossRule.objects.filter(rule_group__strategy__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_strategy(self, request):
        """Get stop loss rules for a strategy."""
        strategy_id = request.query_params.get('strategy_id')
        qs = self.get_queryset().filter(rule_group__strategy_id=strategy_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class TargetRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for target/exit rules."""
    serializer_class = TargetRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TargetRule.objects.filter(rule_group__strategy__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_strategy(self, request):
        """Get target rules for a strategy."""
        strategy_id = request.query_params.get('strategy_id')
        qs = self.get_queryset().filter(rule_group__strategy_id=strategy_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

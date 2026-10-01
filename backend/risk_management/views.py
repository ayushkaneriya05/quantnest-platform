"""
Views for the risk_management app.
"""
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import PositionSizingRule, StrategyAutoDisable
from .serializers import PositionSizingRuleSerializer, StrategyAutoDisableSerializer

class PositionSizingRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for position sizing rules."""
    serializer_class = PositionSizingRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        qs = PositionSizingRule.objects.filter(strategy__user=self.request.user)
        strategy_id = self.request.query_params.get('strategy')
        if strategy_id:
            qs = qs.filter(strategy_id=strategy_id)
        return qs

    def create(self, request, *args, **kwargs):
        strategy_id = request.data.get('strategy')
        if strategy_id:
            instance = PositionSizingRule.objects.filter(strategy_id=strategy_id, strategy__user=request.user).first()
            if instance:
                serializer = self.get_serializer(instance, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data)
        return super().create(request, *args, **kwargs)

class StrategyAutoDisableViewSet(viewsets.ModelViewSet):
    """ViewSet for strategy auto-disable rules."""
    serializer_class = StrategyAutoDisableSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        qs = StrategyAutoDisable.objects.filter(strategy__user=self.request.user)
        strategy_id = self.request.query_params.get('strategy')
        if strategy_id:
            qs = qs.filter(strategy_id=strategy_id)
        return qs

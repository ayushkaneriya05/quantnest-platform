"""
Views for the risk_management app.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    PositionSizingRule, PortfolioRiskProfile,
    StrategyAutoDisable, RiskViolation
)
from .serializers import (
    PositionSizingRuleSerializer, PortfolioRiskProfileSerializer,
    StrategyAutoDisableSerializer,
    RiskViolationSerializer
)


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


class PortfolioRiskProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for portfolio risk profile (singleton per user)."""
    serializer_class = PortfolioRiskProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PortfolioRiskProfile.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update current user's risk profile."""
        profile, created = PortfolioRiskProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


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


class RiskViolationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for risk violations (read-only)."""
    serializer_class = RiskViolationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return RiskViolation.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark a violation as resolved."""
        from django.utils import timezone
        
        violation = self.get_object()
        violation.is_resolved = True
        violation.resolved_at = timezone.now()
        violation.resolved_by = request.user
        violation.resolution_notes = request.data.get('notes', '')
        violation.save()
        
        serializer = self.get_serializer(violation)
        return Response(serializer.data)

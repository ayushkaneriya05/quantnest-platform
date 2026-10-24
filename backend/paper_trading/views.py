from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch
from decimal import Decimal
from rest_framework.fields import DecimalField
from .models import (
    PaperAccount, PaperPosition, PaperOrder, PaperTrade,
    Portfolio, FundTransaction,
    PaperTradingSession
)
from .serializers import (
    PaperAccountSerializer, PaperPositionSerializer,
    PaperOrderSerializer, PaperTradeSerializer,
    PortfolioSerializer,
    FundTransactionSerializer,
    PaperTradingSessionSerializer
)
from .services import PaperExecutionService, PortfolioService


class PortfolioViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user portfolio."""
    serializer_class = PortfolioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's portfolio (creates if not exists)."""
        portfolio = PortfolioService.get_or_create_portfolio(request.user)
        serializer = self.get_serializer(portfolio)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        """Deposit funds into portfolio."""
        self.get_object()
        amount = DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01')).run_validation(request.data.get('amount'))
        transaction = PortfolioService.deposit(request.user, amount, request.data.get('notes', ''))
        return Response({'success': True, 'new_balance': transaction.balance_after})

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw funds from portfolio."""
        self.get_object()
        amount = DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.01')).run_validation(request.data.get('amount'))
        try:
            transaction = PortfolioService.withdraw(request.user, amount, request.data.get('notes', ''))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=400)
        return Response({'success': True, 'new_balance': transaction.balance_after})

class FundTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for fund transactions (read-only)."""
    serializer_class = FundTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FundTransaction.objects.filter(portfolio__user=self.request.user)


class PaperSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for paper trading sessions."""
    serializer_class = PaperTradingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        sessions = PaperTradingSession.objects.filter(user=self.request.user).select_related(
            "strategy", "allocation__deployed_version", "charge_profile"
        ).prefetch_related(Prefetch("account", queryset=PaperAccount.objects.with_totals())).order_by("-updated_at")
        session_status = self.request.query_params.get("status")
        if session_status:
            from common.enums import ExecutionSessionStatus
            from rest_framework.fields import ChoiceField
            session_status = ChoiceField(choices=ExecutionSessionStatus.choices).run_validation(session_status)
            sessions = sessions.filter(status=session_status)
        return sessions

    def destroy(self, request, pk=None):
        session = self.get_object()
        try:
            PortfolioService.delete_paper_account(session.account)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def reset(self, request, pk=None):
        session = self.get_object()
        try:
            PortfolioService.reset_paper_account(session.account)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"], url_path="update-allocation")
    def update_allocation(self, request, pk=None):
        session = self.get_object()
        amount = DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01")).run_validation(
            request.data.get("allocation_amount")
        )
        try:
            PortfolioService.update_allocation(session.allocation, amount)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"], url_path="deploy-version")
    def deploy_version(self, request, pk=None):
        from rest_framework.fields import IntegerField
        from strategies.models import StrategyVersion
        from strategies.services import StrategyDeploymentService
        session = self.get_object()
        version_id = IntegerField(min_value=1).run_validation(request.data.get("version_id"))
        try:
            version = StrategyVersion.objects.get(pk=version_id, strategy_id=session.strategy_id)
            StrategyDeploymentService.change_version(session.allocation, version, "paper", request.user)
        except StrategyVersion.DoesNotExist:
            return Response({"error": "Select a saved version of this strategy."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=['post'], url_path='configure-costs')
    def configure_costs(self, request, pk=None):
        session = self.get_object()
        try:
            session = PaperExecutionService.configure_session_costs(
                session,
                slippage_pct=request.data.get('slippage_pct', session.slippage_pct),
                charge_profile_id=request.data.get('charge_profile', session.charge_profile_id),
                include_charges=request.data.get('include_charges', session.include_charges),
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        session = self.get_object()
        try:
            PaperExecutionService.pause_session(session)
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(exc)) from None
        return Response({"status": "PAUSED"})

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        session = self.get_object()
        if session.status == "STOPPED":
            return Response({"error": "Session is already STOPPED"}, status=status.HTTP_400_BAD_REQUEST)
        session, remaining_positions = PaperExecutionService.stop_session(session)
        return Response({"status": session.status, "remaining_positions": remaining_positions})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        session = self.get_object()
        try:
            PaperExecutionService.resume_session(session)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"status": "RUNNING"})


class PaperAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for paper trading accounts."""
    serializer_class = PaperAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaperAccount.objects.with_totals().filter(user=self.request.user).prefetch_related('sessions')

class PaperPositionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for paper positions (read-only - strategy managed only)."""
    serializer_class = PaperPositionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaperPosition.objects.filter(
            account__user=self.request.user
        ).select_related('instrument', 'strategy')


class PaperOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for paper orders (read-only - strategy execution only)."""
    serializer_class = PaperOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaperOrder.objects.filter(
            account__user=self.request.user
        ).select_related('instrument', 'strategy')


class PaperTradeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for paper trades (read-only)."""
    serializer_class = PaperTradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaperTrade.objects.filter(
            account__user=self.request.user
        ).select_related('instrument', 'strategy')

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Read one aggregate snapshot, with the same fields even when empty."""
        from django.db.models import Avg, Count, Q, Sum
        stats = self.get_queryset().aggregate(
            total_trades=Count('id'),
            winning_trades=Count('id', filter=Q(net_pnl__gt=0)),
            losing_trades=Count('id', filter=Q(net_pnl__lt=0)),
            avg_pnl=Avg('net_pnl'), total_pnl=Sum('net_pnl'),
            avg_winner=Avg('net_pnl', filter=Q(net_pnl__gt=0)),
            avg_loser=Avg('net_pnl', filter=Q(net_pnl__lt=0)),
        )
        for key in ('avg_pnl', 'total_pnl', 'avg_winner', 'avg_loser'):
            stats[key] = float(stats[key] or 0)
        stats['win_rate'] = stats['winning_trades'] / stats['total_trades'] * 100 if stats['total_trades'] else 0
        return Response(stats)

from common.pagination import StandardPagination
from common.list_filters import record_filters
from django.db.models import Count, Q
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
    pagination_class = StandardPagination
    """ViewSet for fund transactions (read-only)."""
    serializer_class = FundTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = record_filters(FundTransaction.objects.filter(portfolio__user=self.request.user), self.request.query_params, 'created_at', instrument=False, account=False)
        kind = self.request.query_params.get('type')
        if kind:
            qs = qs.filter(transaction_type=kind)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(notes__icontains=search) | Q(transaction_type__icontains=search))
        return qs.order_by('-created_at', '-id')


class PaperSessionViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination
    """ViewSet for paper trading sessions."""
    serializer_class = PaperTradingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        counts = {row['status']: row['count'] for row in PaperTradingSession.objects.filter(user=request.user).values('status').annotate(count=Count('id')).order_by()}
        return Response({'total': sum(counts.values()), 'statuses': counts})

    def get_queryset(self):
        sessions = PaperTradingSession.objects.filter(user=self.request.user).select_related(
            "strategy", "allocation__deployed_version__created_by", "charge_profile"
        ).prefetch_related(Prefetch("account", queryset=PaperAccount.objects.with_totals())).order_by("-created_at", "-id")
        session_status = self.request.query_params.get("status") if self.action == "list" else None
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
    pagination_class = StandardPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaperAccount.objects.with_totals().filter(user=self.request.user).prefetch_related('sessions').order_by('-created_at', '-id')

class PaperPositionViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination
    """ViewSet for paper positions (read-only - strategy managed only)."""
    serializer_class = PaperPositionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = PaperPosition.objects.filter(account__user=self.request.user, quantity__gt=0).select_related('instrument', 'strategy')
        return record_filters(qs, self.request.query_params, 'opened_at').order_by('-opened_at', '-id')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        from common.valuation import position_totals
        return Response(position_totals(self.get_queryset()))


class PaperOrderViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination
    """ViewSet for paper orders (read-only - strategy execution only)."""
    serializer_class = PaperOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = PaperOrder.objects.filter(account__user=self.request.user).select_related('instrument', 'strategy')
        qs = record_filters(qs, self.request.query_params, 'placed_at')
        value = self.request.query_params.get('status')
        if value:
            from rest_framework.fields import ChoiceField
            value = ChoiceField(choices=PaperOrder._meta.get_field('status').choices).run_validation(value)
            qs = qs.filter(status=value)
        return qs.order_by('-placed_at', '-id')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        from common.enums import OrderStatus
        return Response(self.get_queryset().aggregate(total=Count('id'),
            filled=Count('id', filter=Q(status=OrderStatus.FILLED)),
            active=Count('id', filter=Q(status__in=[OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL])),
            rejected=Count('id', filter=Q(status=OrderStatus.REJECTED))))


class PaperTradeViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination
    """ViewSet for paper trades (read-only)."""
    serializer_class = PaperTradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = PaperTrade.objects.filter(account__user=self.request.user).select_related('instrument', 'strategy')
        qs = record_filters(qs, self.request.query_params, 'exit_time')
        mode = self.request.query_params.get('pnl_mode', 'net')
        from rest_framework.fields import ChoiceField
        mode = ChoiceField(choices=['net', 'gross']).run_validation(mode)
        field = mode + '_pnl'
        outcome = ChoiceField(choices=['all', 'winning', 'losing']).run_validation(self.request.query_params.get('filter', 'all'))
        if outcome != 'all':
            qs = qs.filter(**{field + ('__gt' if outcome == 'winning' else '__lt'): 0})
        return qs.order_by('-exit_time', '-id')

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Read one aggregate snapshot, with the same fields even when empty."""
        from django.db.models import Avg, Count, Q, Sum
        field = 'gross_pnl' if request.query_params.get('pnl_mode') == 'gross' else 'net_pnl'
        qs = self.get_queryset()
        stats = qs.aggregate(
            total_trades=Count('id'),
            winning_trades=Count('id', filter=Q(**{field + '__gt': 0})),
            losing_trades=Count('id', filter=Q(**{field + '__lt': 0})),
            avg_pnl=Avg(field), total_pnl=Sum(field),
            avg_winner=Avg('net_pnl', filter=Q(**{field + '__gt': 0})),
            avg_loser=Avg('net_pnl', filter=Q(**{field + '__lt': 0})),
        )
        for key in ('avg_pnl', 'total_pnl', 'avg_winner', 'avg_loser'):
            stats[key] = float(stats[key] or 0)
        stats['win_rate'] = stats['winning_trades'] / stats['total_trades'] * 100 if stats['total_trades'] else 0
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.localdate()
        recent = qs.filter(exit_time__date__gte=today - timedelta(days=29), exit_time__date__lte=today)
        daily = list(recent.annotate(date=TruncDate('exit_time')).values('date').annotate(pnl=Sum(field)).order_by('date'))
        wins = recent.aggregate(total=Count('id'), wins=Count('id', filter=Q(**{field + '__gt': 0})))
        stats['performance'] = {
            'weekPnl': qs.filter(exit_time__date__gte=today - timedelta(days=6), exit_time__date__lte=today).aggregate(pnl=Sum(field))['pnl'] or 0,
            'monthPnl': qs.filter(exit_time__date__gte=today.replace(day=1), exit_time__date__lte=today).aggregate(pnl=Sum(field))['pnl'] or 0,
            'bestDay': max(daily, key=lambda row: row['pnl']) if daily else None,
            'worstDay': min(daily, key=lambda row: row['pnl']) if daily else None,
            'winRate': wins['wins'] / wins['total'] * 100 if wins['total'] else 0,
            'closedTradeCount': wins['total'], 'pnlBars': daily[-14:],
        }
        return Response(stats)

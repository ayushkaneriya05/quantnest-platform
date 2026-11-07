"""Read-only, owner-scoped settlement history. Financial writes use commands."""
from django.db.models import Q
from rest_framework import generics, serializers
from common.pagination import StandardPagination
from rest_framework.permissions import IsAuthenticated

from common.enums import ExecutionMode
from instruments.serializers import InstrumentSerializer
from .models import SettlementPosting


class SettlementSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(source='price.instrument', read_only=True)
    kind = serializers.CharField(source='price.get_kind_display', read_only=True)
    effective_at = serializers.DateTimeField(source='price.effective_at', read_only=True)
    available_at = serializers.DateTimeField(source='price.available_at', read_only=True)
    source = serializers.CharField(source='price.source', read_only=True)

    class Meta:
        model = SettlementPosting
        fields = ('id', 'instrument', 'kind', 'effective_at', 'available_at', 'source',
                  'account_id', 'session_id', 'route_id', 'leg_id', 'quantity', 'gross', 'fees', 'cash_change')
        read_only_fields = fields


class SettlementHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SettlementSerializer
    pagination_class = StandardPagination
    mode = ExecutionMode.TERMINAL

    def get_queryset(self):
        from paper_trading.models import PaperAccount
        from trading.models import Account
        from trading.views import filter_history_dates
        model = PaperAccount if self.mode == ExecutionMode.PAPER else Account
        accounts = model.objects.filter(user=self.request.user)
        identity = self.request.query_params.get('account_id')
        if identity:
            identity = serializers.IntegerField(min_value=1).run_validation(identity)
            accounts = accounts.filter(pk=identity)
        rows = SettlementPosting.objects.filter(mode=self.mode, account_id__in=accounts.values('pk')).select_related('price__instrument')
        search = self.request.query_params.get('symbol', '')[:100]
        if search:
            rows = rows.filter(Q(price__instrument__name__icontains=search) | Q(price__instrument__sym_ticker__icontains=search))
        return filter_history_dates(rows, self.request, 'price__effective_at')

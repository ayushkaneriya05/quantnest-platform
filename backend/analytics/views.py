import csv

from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .services import SOURCES, TradeFiltersSerializer, execution_report, execution_review_context, trade_queryset, trade_rows


class TradePagination(PageNumberPagination):
    page_size = 25


def request_filters(request):
    serializer = TradeFiltersSerializer(data=request.query_params.dict())
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class ExecutionReportViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(execution_report(request.user, request_filters(request)))

    @action(detail=False, methods=["post"], url_path="research-context")
    def research_context(self, request):
        from research.context import resolve_context
        from research.models import ResearchSession
        from research.serializers import ResearchSessionSerializer
        settings, evidence = execution_review_context(request.user, request.data)
        context = resolve_context(request.user, {}, {"execution_review": settings, "execution_evidence": evidence})
        session = ResearchSession.objects.create(user=request.user, title=f"{settings['filters']['source'].title()} execution review", context=context)
        return Response(ResearchSessionSerializer(session).data, status=201)

    @action(detail=False, methods=["get"])
    def trades(self, request):
        filters = request_filters(request)
        qs = trade_queryset(request.user, filters).order_by("-exit_time", "-id")
        paginator = TradePagination()
        page = paginator.paginate_queryset(qs.values_list("id", flat=True), request)
        return paginator.get_paginated_response(trade_rows(qs.filter(pk__in=page), filters["source"], request.user))

    @action(detail=False, methods=["get"])
    def export(self, request):
        filters = request_filters(request)
        qs = trade_queryset(request.user, filters).order_by("-exit_time", "-id")
        if qs.count() > 50000:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Export up to 50,000 closes at once; narrow the date range.")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filters["source"].lower()}-closes.csv"'
        writer = csv.writer(response)
        writer.writerow(["Source", "P&L basis", "Symbol", "Strategy", "Account", "Side", "Quantity", "Entry price", "Exit price", "Entry time", "Exit time", "Realized P&L", "Recorded charges"])
        fields = ("symbol", "strategy_name", "account_name", "side", "quantity", "entry_price", "exit_price", "entry_time", "exit_time", "pnl", "charges")
        for row in qs.values_list(*fields).iterator(chunk_size=1000):
            values = [value.isoformat() if hasattr(value, "isoformat") else value for value in row]
            values = ["'" + value if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"} else value for value in values]
            writer.writerow([filters["source"], SOURCES[filters["source"]]["basis"], *values])
        return response

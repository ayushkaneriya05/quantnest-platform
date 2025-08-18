
# backend/trading/views.py
from decimal import Decimal
from datetime import datetime, timezone
import json
import redis
import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import PaperOrder, PaperTrade, PaperPosition, PaperAccount, AuditLog
from .serializers import PaperOrderSerializer, AuditLogSerializer
from .orderbook import add_order_to_orderbook, match_in_orderbook, remove_order_from_orderbook_by_oid
from .services.order_execution import execute_market_fill
from .orderbook import create_bracket_children
from .permissions import IsOwnerOrReadOnly

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

class PlaceOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        data["user"] = request.user.id
        serializer = PaperOrderSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        order = serializer.save(user=request.user)
        r.sadd(f"orders:pending:{order.symbol}", str(order.id))
        try:
            match_in_orderbook(order)
            if order.qty - order.filled_qty > 0 and order.order_type == PaperOrder.ORDER_MARKET:
                ltp_raw = r.get(f"delayed:tick:{order.symbol}")
                if ltp_raw:
                    ltp = json.loads(ltp_raw).get("last")
                    execute_market_fill(order, order.qty - order.filled_qty, Decimal(str(ltp)))
        except Exception:
            pass
        return Response(PaperOrderSerializer(order).data, status=status.HTTP_201_CREATED)

class CancelOrderView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def post(self, request, order_id):
        order = get_object_or_404(PaperOrder, id=order_id, user=request.user)
        if order.status != PaperOrder.STATUS_PENDING:
            return Response({"detail": "Not cancellable"}, status=status.HTTP_400_BAD_REQUEST)
        remove_order_from_orderbook_by_oid(order.symbol, order.id)
        order.status = PaperOrder.STATUS_CANCELLED
        order.save(update_fields=["status", "updated_at"])
        AuditLog.objects.create(order=order, action=AuditLog.ACTION_CANCELLED, performed_by=request.user)
        return Response({"ok": True})

class ModifyOrderView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def post(self, request, order_id):
        order = get_object_or_404(PaperOrder, id=order_id, user=request.user)
        if order.status != PaperOrder.STATUS_PENDING:
            return Response({"detail": "Cannot modify"}, status=status.HTTP_400_BAD_REQUEST)
        
        price = request.data.get("price")
        qty = request.data.get("qty")
        with transaction.atomic():
            if price is not None:
                order.price = Decimal(str(price))
            if qty is not None:
                if int(qty) < order.filled_qty:
                    return Response({"detail": "qty less than filled"}, status=status.HTTP_400_BAD_REQUEST)
                order.qty = int(qty)
            order.save()
            # update orderbook mapping
            remove_order_from_orderbook_by_oid(order.symbol, order.id)
            if order.order_type == PaperOrder.ORDER_LIMIT:
                add_order_to_orderbook(order)
            AuditLog.objects.create(order=order, action=AuditLog.ACTION_MODIFIED, performed_by=request.user, details={"price": str(order.price), "qty": order.qty})
        return Response(PaperOrderSerializer(order).data)


class OrdersListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaperOrderSerializer

    def get_queryset(self):
        return PaperOrder.objects.filter(user=self.request.user).order_by("-created_at")


class TradesListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        trades = PaperTrade.objects.filter(order__user=request.user).select_related("order").order_by("-ts")[:500]
        payload = [
            {"id": t.id, "order_id": t.order_id, "qty": t.qty, "price": str(t.price), "ts": t.ts.isoformat()}
            for t in trades
        ]
        return Response(payload)


class PositionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pos = PaperPosition.objects.filter(user=request.user)
        payload = []
        for p in pos:
            payload.append({
                "symbol": p.symbol, "qty": p.qty, "avg_price": str(p.avg_price),
                "realized_pnl": str(p.realized_pnl), "unrealized_pnl": str(p.unrealized_pnl),
                "sl_price": str(p.sl_price) if p.sl_price else None, "tp_price": str(p.tp_price) if p.tp_price else None
            })
        return Response(payload)


class AccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        acct, _ = PaperAccount.objects.get_or_create(user=request.user)
        return Response({
            "balance": str(acct.balance), "equity": str(acct.equity), "margin_used": str(acct.margin_used)
        })


class OrderbookSnapshotView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, symbol):
        """
        Returns top N bids and asks using Redis zsets.
        """
        depth = int(request.query_params.get("depth", 10))
        bids = r.zrange(f"orderbook:bids:{symbol}", 0, depth - 1, withscores=True)
        asks = r.zrange(f"orderbook:asks:{symbol}", 0, depth - 1, withscores=True)

        def _parse_entry(member_score):
            if not member_score:
                return None
            member, score = member_score
            try:
                obj = json.loads(member)
                oid = int(obj["oid"])
                order = PaperOrder.objects.filter(id=oid).first()
                if not order:
                    return None
                return {"price": float(order.price or 0), "qty": order.remaining_qty(), "order_id": order.id, "ts": order.created_at.isoformat()}
            except Exception:
                return None

        bids_parsed = [_parse_entry(b) for b in bids if _parse_entry(b)]
        asks_parsed = [_parse_entry(a) for a in asks if _parse_entry(a)]
        return Response({"bids": bids_parsed, "asks": asks_parsed})


class BracketOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Place bracket order (entry + TP + SL). Supports SL-M if 'sl_is_slm' true.
        Fields:
            symbol, side, qty, entry_type (MARKET/LIMIT), entry_price, tp_price, sl_price, sl_is_slm (bool)
        """
        user = request.user
        data = request.data
        symbol = data.get("symbol")
        side = data.get("side")
        qty = int(data.get("qty"))
        entry_type = data.get("entry_type", "MARKET")
        entry_price = data.get("entry_price")
        tp_price = data.get("tp_price")
        sl_price = data.get("sl_price")
        sl_is_slm = bool(data.get("sl_is_slm", False))

        if not (symbol and side and qty and tp_price and sl_price):
            return Response({"detail": "missing fields"}, status=status.HTTP_400_BAD_REQUEST)

        order = PaperOrder.objects.create(
            user=user, symbol=symbol, side=side, qty=qty,
            order_type=entry_type, price=Decimal(str(entry_price)) if entry_price else None,
            tp_price=Decimal(str(tp_price)), sl_price=Decimal(str(sl_price)),
            order_tag=PaperOrder.ORDER_TAG_ENTRY, status=PaperOrder.STATUS_PENDING
        )
        # create children
        tp_order, sl_order = create_bracket_children(order, tp_price=Decimal(str(tp_price)), sl_price=Decimal(str(sl_price)))
        # mark SL child as SL-M if requested
        if sl_is_slm:
            sl_order.is_slm = True
            sl_order.stop_trigger_price = Decimal(str(sl_price))
            sl_order.save(update_fields=["is_slm", "stop_trigger_price"])

        r.sadd(f"orders:pending:{symbol}", str(order.id))

        # immediate matching attempt for entry
        try:
            match_in_orderbook(order)
            remaining = order.qty - order.filled_qty
            if remaining > 0 and entry_type == PaperOrder.ORDER_LIMIT:
                add_order_to_orderbook(order)
            elif remaining > 0 and entry_type == PaperOrder.ORDER_MARKET:
                ltp_raw = r.get(f"delayed:tick:{symbol}")
                if ltp_raw:
                    ltp = json.loads(ltp_raw).get("last")
                    execute_market_fill(order, remaining, Decimal(str(ltp)))
        except Exception:
            pass

        return Response({"entry": PaperOrderSerializer(order).data, "tp_id": tp_order.id, "sl_id": sl_order.id}, status=status.HTTP_201_CREATED)


class CoverOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Place a cover order (entry + required SL). Similar to bracket but only SL child.
        """
        user = request.user
        data = request.data
        symbol = data.get("symbol")
        side = data.get("side")
        qty = int(data.get("qty"))
        entry_type = data.get("entry_type", "MARKET")
        entry_price = data.get("entry_price")
        sl_price = data.get("sl_price")
        sl_is_slm = bool(data.get("sl_is_slm", False))
        if not (symbol and side and qty and sl_price):
            return Response({"detail": "missing"}, status=status.HTTP_400_BAD_REQUEST)

        order = PaperOrder.objects.create(user=user, symbol=symbol, side=side, qty=qty, order_type=entry_type, price=Decimal(str(entry_price)) if entry_price else None, order_tag=PaperOrder.ORDER_TAG_ENTRY, status=PaperOrder.STATUS_PENDING, sl_price=Decimal(str(sl_price)))
        order.create_oco_group()
        oco = order.oco_group
        sl_side = "SELL" if side == "BUY" else "BUY"
        sl_child = PaperOrder.objects.create(user=user, symbol=symbol, side=sl_side, qty=qty, order_type=PaperOrder.ORDER_SLM if sl_is_slm else PaperOrder.ORDER_LIMIT, price=Decimal(str(sl_price)) if not sl_is_slm else None, parent=order, order_tag=PaperOrder.ORDER_TAG_COVER_SL, status=PaperOrder.STATUS_PENDING, oco_group=oco)
        if sl_is_slm:
            sl_child.is_slm = True
            sl_child.stop_trigger_price = Decimal(str(sl_price))
            sl_child.save(update_fields=["is_slm", "stop_trigger_price"])
        r.sadd(f"orders:pending:{symbol}", str(order.id))

        # attempt immediate matching similar to bracket
        try:
            match_in_orderbook(order)
            remaining = order.qty - order.filled_qty
            if remaining > 0 and entry_type == PaperOrder.ORDER_LIMIT:
                add_order_to_orderbook(order)
            elif remaining > 0:
                ltp_raw = r.get(f"delayed:tick:{symbol}")
                if ltp_raw:
                    ltp = json.loads(ltp_raw).get("last")
                    execute_market_fill(order, remaining, Decimal(str(ltp)))
        except Exception:
            pass

        return Response({"entry": PaperOrderSerializer(order).data, "sl_child": sl_child.id}, status=status.HTTP_201_CREATED)


# ... (PlaceOrderView, CancelOrderView, ModifyOrderView are unchanged)

class AuditLogsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        order_id = request.query_params.get("order_id")
        qs = AuditLog.objects.filter(order__user=request.user) # Corrected query
        if order_id:
            qs = qs.filter(order_id=order_id)
        qs = qs.order_by("-timestamp")[:500]
        return Response(AuditLogSerializer(qs, many=True).data)

# ... (rest of the file is unchanged)
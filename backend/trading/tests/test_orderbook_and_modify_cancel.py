# backend/trading/tests/test_orderbook_and_modify_cancel.py
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from trading.models import PaperOrder, PaperAccount, PaperPosition
from trading.orderbook import add_order_to_orderbook, match_in_orderbook, remove_order_from_orderbook_by_oid
import redis, os
from django.conf import settings

User = get_user_model()
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

@pytest.mark.django_db
def test_limit_matching_and_partial_fill():
    # create seller with limit sell 10 @100
    s = User.objects.create_user(username="seller", password="p")
    b = User.objects.create_user(username="buyer", password="p")
    sell = PaperOrder.objects.create(user=s, symbol="TEST", side="SELL", qty=10, order_type="LIMIT", price=Decimal("100"))
    add_order_to_orderbook(sell)
    buy = PaperOrder.objects.create(user=b, symbol="TEST", side="BUY", qty=6, order_type="LIMIT", price=Decimal("110"))
    res = match_in_orderbook(buy)
    buy.refresh_from_db()
    sell.refresh_from_db()
    assert res["matched"] == 6
    assert buy.status in ("PARTIAL","FILLED")
    assert sell.status in ("PARTIAL","FILLED")
    assert sell.filled_qty == 6 or sell.filled_qty == 6

@pytest.mark.django_db
def test_cancel_order_removes_from_book():
    u = User.objects.create_user(username="u1", password="p")
    o = PaperOrder.objects.create(user=u, symbol="CXL", side="BUY", qty=5, order_type="LIMIT", price=Decimal("50"))
    add_order_to_orderbook(o)
    # ensure mapping exists
    mem = r.get(f"order:member:{o.id}")
    assert mem is not None
    # cancel
    removed = remove_order_from_orderbook_by_oid("CXL", o.id)
    assert removed is True
    assert r.get(f"order:member:{o.id}") is None
    
# backend/trading/tests/test_matching.py
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from trading.models import PaperOrder, PaperAccount, PaperPosition
from trading.tasks import should_fill_order

User = get_user_model()

@pytest.mark.django_db
def test_should_fill_limit_buy():
    user = User.objects.create_user(username="u1", password="p")
    order = PaperOrder.objects.create(user=user, symbol="RELIANCE", side="BUY", qty=10, order_type="LIMIT", price=Decimal("100"))
    tick = {"symbol":"RELIANCE", "ts":"2025-01-01T10:00:00Z", "last": 95}
    assert should_fill_order(order, tick) is True

@pytest.mark.django_db
def test_should_not_fill_limit_buy_higher():
    user = User.objects.create_user(username="u2", password="p")
    order = PaperOrder.objects.create(user=user, symbol="TCS", side="BUY", qty=5, order_type="LIMIT", price=Decimal("200"))
    tick = {"symbol":"TCS","ts":"2025-01-01T10:00:00Z","last": Decimal("205")}
    assert should_fill_order(order, tick) is False  

@pytest.mark.django_db
def test_market_order_always_fill():
    user = User.objects.create_user(username="u3", password="p")
    order = PaperOrder.objects.create(user=user, symbol="INFY", side="SELL", qty=3, order_type="MARKET")
    tick = {"symbol":"INFY","ts":"2025-01-01T10:00:00Z","last": Decimal("1500")}
    assert should_fill_order(order, tick) is True

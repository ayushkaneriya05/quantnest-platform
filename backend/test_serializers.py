import os
import django
import sys

# Setup Django environment
sys.path.append(r'e:\QuantNest\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quantnest.settings')
django.setup()

from django.contrib.auth import get_user_model
from risk_management.serializers import PositionSizingRuleSerializer, PortfolioRiskProfileSerializer
from strategies.serializers import EntryOrderConfigSerializer
from risk_management.models import PortfolioRiskProfile
from strategies.models import EntryOrderConfig

User = get_user_model()
user = User.objects.first()

print("Testing PortfolioRiskProfile Serializer...")
profile_data = {
    "max_daily_loss_percentage": 5,
    "max_daily_loss_amount": None,
    "max_daily_trades": 50,
    "max_open_positions": 10,
    "max_exposure_percentage": 80,
    "max_per_strategy_allocation": 25,
    "max_per_instrument_exposure": 10,
    "max_drawdown_percentage": 15,
    "trailing_drawdown_reset": True,
    "alert_on_breach": True,
    "halt_on_breach": False
}

serializer = PortfolioRiskProfileSerializer(data=profile_data, partial=True)
if not serializer.is_valid():
    print("Portfolio Profile Errors:", serializer.errors)
else:
    print("Portfolio Profile OK")

print("\nTesting EntryOrderConfig Serializer...")
entry_data = {
    "order_type": "MARKET",
    "entry_price_logic": "LTP",
    "price_offset": None,
    "slippage_tolerance_pct": 0.1,
    "allow_partial_entry": False,
    "max_entry_attempts": 3,
    "entry_cooldown_seconds": 60,
}

# The payload to EntryOrderConfigViewSet.patch
entry_serializer = EntryOrderConfigSerializer(data=entry_data, partial=True)
if not entry_serializer.is_valid():
    print("EntryOrderConfig Errors:", entry_serializer.errors)
else:
    print("EntryOrderConfig OK")


print("\nTesting PositionSizingRule Serializer...")
sizing_data = {
    "sizing_method": "CAPITAL_BASED",
    "fixed_quantity": None,
    "capital_percentage": 10,
    "risk_per_trade_amount": None,
    "risk_per_trade_percentage": None,
    "max_daily_trades": 10,
    "max_open_positions": 5
}
sizing_serializer = PositionSizingRuleSerializer(data=sizing_data, partial=True)
if not sizing_serializer.is_valid():
    print("PositionSizingRule Errors:", sizing_serializer.errors)
else:
    print("PositionSizingRule OK")


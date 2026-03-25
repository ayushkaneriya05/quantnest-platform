import os
import sys
import django

sys.path.append(r'e:\QuantNest\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quantnest.settings')
django.setup()

from django.contrib.auth import get_user_model
from risk_management.models import PortfolioRiskProfile
from risk_management.serializers import PortfolioRiskProfileSerializer

User = get_user_model()
user = User.objects.first()

if not user:
    print("No user found")
    sys.exit(1)

profile, created = PortfolioRiskProfile.objects.get_or_create(user=user)
print(f"Profile created: {created}")

data = {
    "max_daily_loss_percentage": 10,
    "max_daily_loss_amount": None,
    "max_daily_trades": 100,
    "max_open_positions": 20,
    "max_exposure_percentage": 50,
    "max_per_strategy_allocation": 20,
    "max_per_instrument_exposure": 5,
    "max_drawdown_percentage": 20,
    "trailing_drawdown_reset": True,
    "alert_on_breach": True,
    "halt_on_breach": False
}

serializer = PortfolioRiskProfileSerializer(profile, data=data, partial=True)
if serializer.is_valid():
    try:
        serializer.save()
        print("Profile saved successfully")
    except Exception as e:
        print(f"Save error: {e}")
else:
    print(f"Validation errors: {serializer.errors}")


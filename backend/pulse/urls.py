from django.urls import path
from .views import DailyPulseView

urlpatterns = [
    path('daily/', DailyPulseView.as_view(), name='pulse-daily'),
]
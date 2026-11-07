"""
URL configuration for the instruments app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InstrumentViewSet

router = DefaultRouter()
router.register(r'instruments', InstrumentViewSet, basename='instrument')

urlpatterns = [
    path('', include(router.urls)),
]

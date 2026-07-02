"""
URL configuration for the common app.
"""
from django.urls import path
from .enums_view import enum_choices
from . import views

urlpatterns = [
    path('enums/', enum_choices, name='enum-choices'),
    path('errors/', views.log_frontend_error, name='log-frontend-error'),
]

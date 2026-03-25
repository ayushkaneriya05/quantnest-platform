"""
URL configuration for the common app.
"""
from django.urls import path
from .enums_view import enum_choices

urlpatterns = [
    path('enums/', enum_choices, name='enum-choices'),
]

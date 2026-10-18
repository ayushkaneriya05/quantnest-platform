"""
URL configuration for the common app.
"""
from django.urls import path
from .enums_view import enum_choices
from .choices import choices

urlpatterns = [
    path('enums/', enum_choices, name='enum-choices'),
    path('choices/', choices, name='dropdown-choices'),
]

# backend/trading/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)

class IsOwnerOrReadOnly(BasePermission):
    """
    Allow safe methods to anyone; modifications only to owner.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user_id == request.user.id

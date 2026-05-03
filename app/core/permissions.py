"""
Custom permissions for the core app.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Allow read-only access for everyone.
    Write access is restricted to objects owned by the request.user.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return getattr(obj, "owner", None) == request.user


class IsPremiumUserForAI(BasePermission):
    """Allow access only to premium users for AI endpoints."""

    message = "AI features require a premium plan."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_premium
        )

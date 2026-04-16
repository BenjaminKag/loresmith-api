"""
ViewSet for Tag objects.
"""
from rest_framework import viewsets, permissions

from core import models, serializers
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Tags"])
class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Tag objects via the API."""

    serializer_class = serializers.TagSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsOwnerOrReadOnly,
    ]

    def get_queryset(self):
        """Return tags for the authenticated user only."""
        return models.Tag.objects.filter(
            owner=self.request.user
        ).order_by("name")

    def perform_create(self, serializer):
        """Set the owner user on creation."""
        serializer.save(owner=self.request.user)

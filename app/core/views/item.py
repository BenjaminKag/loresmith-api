"""
ViewSet for Item objects.
"""
from rest_framework import viewsets, permissions

from core import models, serializers
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Items"])
class ItemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Item objects via the API."""

    queryset = models.Item.objects.all().select_related("created_by")
    serializer_class = serializers.ItemSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def perform_create(self, serializer):
        """Set the created_by user on creation."""
        serializer.save(created_by=self.request.user)

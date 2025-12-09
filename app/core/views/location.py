"""
ViewSet for Location objects.
"""
from rest_framework import viewsets, permissions

from core import models, serializers
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Locations"])
class LocationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Location objects via the API."""

    queryset = models.Location.objects.all().select_related(
        "parent",
        "created_by"
    )
    serializer_class = serializers.LocationSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def perform_create(self, serializer):
        """Set the created_by user on creation."""
        serializer.save(created_by=self.request.user)

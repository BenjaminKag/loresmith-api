"""
ViewSet for Faction objects.
"""
from rest_framework import viewsets, permissions

from core import models, serializers
from core.permissions import IsOwnerOrReadOnly


class FactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Faction objects via the API."""

    queryset = models.Faction.objects.all().select_related(
        "location",
        "created_by"
    )
    serializer_class = serializers.FactionSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def perform_create(self, serializer):
        """Set the created_by user on creation."""
        serializer.save(created_by=self.request.user)

"""
ViewSet for Location objects.
"""
from rest_framework import viewsets, permissions

from core import models
from core import serializers
from core.permissions import IsOwnerOrReadOnly


class LocationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Location objects via the API."""

    queryset = models.Location.objects.all()
    serializer_class = serializers.LocationSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def perform_create(self, serializer):
        """
        When creating a new Location via the API, automatically
        set `created_by` to the authenticated user.
        """
        serializer.save(created_by=self.request.user)

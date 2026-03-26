"""
ViewSet for Location objects.
"""
from rest_framework import viewsets, permissions

from django.db.models import Q

from core import models, serializers
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Locations"])
class LocationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Location objects via the API."""

    serializer_class = serializers.LocationSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def perform_create(self, serializer):
        """Set the owner user on creation."""
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        base_queryset = models.Location.objects.select_related(
            "parent",
            "owner"
        )

        user = self.request.user

        if user.is_authenticated:
            return base_queryset.filter(
                Q(owner=user) |
                Q(stories__visibility=models.Story.Visibility.PUBLIC)
            ).distinct()

        return base_queryset.filter(
            stories__visibility=models.Story.Visibility.PUBLIC
        ).distinct()

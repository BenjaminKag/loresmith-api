"""
ViewSets for trait sets and traits.
"""
from rest_framework import viewsets, permissions

from core import models, serializers
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Traits"])
class TraitSetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing TraitSet objects via the API."""

    serializer_class = serializers.TraitSetSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsOwnerOrReadOnly,
    ]

    def get_queryset(self):
        """Return trait sets for the authenticated user only."""
        return (
            models.TraitSet.objects
            .filter(owner=self.request.user)
            .order_by("name")
        )

    def perform_create(self, serializer):
        """Set the owner user on creation."""
        serializer.save(owner=self.request.user)


@extend_schema(tags=["Traits"])
class TraitViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Trait objects via the API."""

    serializer_class = serializers.TraitSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsOwnerOrReadOnly,
    ]

    def get_queryset(self):
        """Return traits from the authenticated user's trait sets only."""
        return (
            models.Trait.objects
            .filter(trait_set__owner=self.request.user)
            .select_related("trait_set")
            .order_by("trait_set__name", "key")
        )

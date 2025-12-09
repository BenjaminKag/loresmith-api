"""
ViewSet for Character objects.
"""
from rest_framework import viewsets, permissions

from core import models, serializers
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Characters"])
class CharacterViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Character objects via the API."""

    queryset = (
        models.Character.objects
        .all()
        .select_related("location", "created_by")
        .prefetch_related("affiliations", "equipment")
    )
    serializer_class = serializers.CharacterSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def perform_create(self, serializer):
        """Set the created_by user on creation."""
        serializer.save(created_by=self.request.user)

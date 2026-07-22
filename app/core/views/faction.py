"""
ViewSet for Faction objects.
"""
from rest_framework import viewsets, permissions

# from django.db.models import Q

from core import models, serializers
from core.mixins import TagFilterMixin
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    tags=["Factions"],
    parameters=[
        OpenApiParameter(
            name="tags",
            type=str,
            location=OpenApiParameter.QUERY,
            description=(
                "Comma-separated tag names. AND logic. Example: Anemo,Yaksha"
            ),
        ),
    ],
)
class FactionViewSet(TagFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Faction objects via the API."""

    serializer_class = serializers.FactionSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def perform_create(self, serializer):
        """Set the owner user on creation."""
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        base_queryset = (
            models.Faction.objects
            .select_related("location", "owner")
            .prefetch_related("tags")
        )

        user = self.request.user

        """
        # Authenticated users can see their own factions and
        # any factions that are public.
        if user.is_authenticated:
            queryset = base_queryset.filter(
                Q(owner=user) |
                Q(stories__visibility=models.Story.Visibility.PUBLIC)
            ).distinct()

        else:
            queryset = base_queryset.filter(
                stories__visibility=models.Story.Visibility.PUBLIC
            ).distinct()
        """

        # Only show factions owned by the user,
        # since the profile generation relies on that.

        if user.is_authenticated:
            queryset = base_queryset.filter(owner=user)

        else:
            queryset = base_queryset.none()

        return self.apply_tag_filters(queryset)

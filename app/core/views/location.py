"""
ViewSet for Location objects.
"""
from rest_framework import viewsets, permissions

# from django.db.models import Q

from core import models, serializers
from core.mixins import TagFilterMixin
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    tags=["Locations"],
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
class LocationViewSet(TagFilterMixin, viewsets.ModelViewSet):
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
        base_queryset = (
            models.Location.objects
            .select_related("parent", "owner")
            .prefetch_related("tags")
        )

        user = self.request.user

        """
        # Authenticated users can see their own locations and
        # any locations that are public.

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

        # Only show locations owned by the user,
        # since the profile generation relies on that.

        if user.is_authenticated:
            queryset = base_queryset.filter(owner=user)

        else:
            queryset = base_queryset.none()

        return self.apply_tag_filters(queryset)

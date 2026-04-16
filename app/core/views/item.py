"""
ViewSet for Item objects.
"""
from rest_framework import viewsets, permissions

from django.db.models import Q

from core import models, serializers
from core.mixins import TagFilterMixin
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    tags=["Items"],
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
class ItemViewSet(TagFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Item objects via the API."""

    serializer_class = serializers.ItemSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def perform_create(self, serializer):
        """Set the owner user on creation."""
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        base_queryset = (
            models.Item.objects
            .select_related("owner")
            .prefetch_related("tags")
        )

        user = self.request.user

        if user.is_authenticated:
            queryset = base_queryset.filter(
                Q(owner=user) |
                Q(stories__visibility=models.Story.Visibility.PUBLIC)
            ).distinct()

        else:
            queryset = base_queryset.filter(
                stories__visibility=models.Story.Visibility.PUBLIC
            ).distinct()

        return self.apply_tag_filters(queryset)

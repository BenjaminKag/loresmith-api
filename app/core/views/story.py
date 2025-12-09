"""
ViewSet for Story objects.
"""
from rest_framework import viewsets, permissions

from core import models, serializers
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema


@extend_schema(tags=["Stories"])
class StoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Story objects via the API."""

    queryset = (
        models.Story.objects
        .all()
        .select_related("parent", "created_by")
        .prefetch_related(
            "characters",
            "locations",
            "factions",
            "items"
        )
    )
    serializer_class = serializers.StorySerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    @extend_schema(
        summary="List stories",
        description=(
            "Return all stories in the world, including "
            "standalone lore entries, "
            "quest arcs and smaller parts (chapters/scenes).\n\n"
            "Use this endpoint to browse your narrative content. You can then "
            "follow the `id` to fetch a single story with the detail endpoint."
        ),
    )
    def list(self, request, *args, **kwargs):
        """List stories in the LoreSmith world."""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new story",
        description=(
            "Create a new story or lore entry. You can optionally:\n"
            "- Set the `kind` (standalone / arc / part)\n"
            "- Choose a `story_type` (lore entry, quest, backstory, etc.)\n"
            "- Attach related characters, locations, "
            "factions and items by ID\n"
            "- Set `parent` to nest the story under a larger arc\n\n"
            "By default, stories are created as private "
            "(`visibility = private`)."
        ),
    )
    def create(self, request, *args, **kwargs):
        """Create a new story."""
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Set the created_by user on creation."""
        serializer.save(created_by=self.request.user)

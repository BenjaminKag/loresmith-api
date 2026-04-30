"""
ViewSet for Story objects.
"""
from rest_framework import (
    viewsets,
    permissions,
    status,
)
from rest_framework.decorators import action
from rest_framework.response import Response

from django.db.models import Q
from django.shortcuts import get_object_or_404

from core import models, serializers
from core.mixins import TagFilterMixin
from core.permissions import IsOwnerOrReadOnly

from core.utils import (
    get_visible_story_subtree,
    build_story_child_map,
    get_story_wiki_entities,
    get_story_wiki_metadata,
)

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter
)

from core.services.ai_client import (
    AiServiceError,
    DailyBudgetExceeded
)
from core.services.story_analysis_generator import StoryAnalysisGenerator
from core.throttling import AIUserThrottle


@extend_schema(
    tags=["Stories"],
    parameters=[
        OpenApiParameter(
            name="tags",
            type=str,
            location=OpenApiParameter.QUERY,
            description=(
                "Comma-separated tag names. AND logic. Example: Anemo,Yaksha",
            ),
        ),
    ],
)
class StoryViewSet(TagFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Story objects via the API."""

    serializer_class = serializers.StorySerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    @extend_schema(
        tags=["AI"],
        operation_id="story_analyze",
        description=(
            "Analyze this story with the AI assistant. "
            "Uses the title, summary and body as input and returns "
            "a structured analysis: summary, themes, tone, strengths, "
            "weaknesses and suggestions."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=serializers.StoryAIAnalysisSerializer,
                description="AI analysis returned successfully."
            ),
            400: OpenApiResponse(description="Nothing to analyze."),
            429: OpenApiResponse(description="AI daily budget or rate limit."),
            503: OpenApiResponse(description="AI service unavailable."),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="analyze",
        throttle_classes=[AIUserThrottle],
    )
    def analyze(self, request, pk=None):
        story = self.get_object()

        if not (
            story.summary or ""
        ).strip() and not (story.body or "").strip():
            return Response(
                {
                    "detail": "Nothing to analyze "
                    "(summary/body are empty)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        generator = StoryAnalysisGenerator()

        try:
            analysis = generator.generate(story)
        except DailyBudgetExceeded as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except AiServiceError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_data = {
            "entity_type": "story",
            "entity_id": story.id,
            "entity_label": story.title,
            "summary": analysis["summary"],
            "themes": analysis["themes"],
            "tone": analysis["tone"],
            "strengths": analysis["strengths"],
            "weaknesses": analysis["weaknesses"],
            "suggestions": analysis["suggestions"],
            "consistency_notes": analysis["consistency_notes"],
            "open_questions": analysis["open_questions"],
            "meta": analysis["meta"],
        }

        return Response(response_data, status=status.HTTP_200_OK)

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
        """Set the owner user on creation."""
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        base_queryset = (
            models.Story.objects
            .select_related("parent", "owner")
            .prefetch_related(
                "characters",
                "locations",
                "factions",
                "items",
                "tags",
                "sub_stories",
            )
        )

        user = self.request.user

        if user.is_authenticated:
            queryset = base_queryset.filter(
                Q(owner=user) |
                Q(visibility=models.Story.Visibility.PUBLIC)
            ).distinct()
        else:
            queryset = base_queryset.filter(
                visibility=models.Story.Visibility.PUBLIC
            ).distinct()

        return self.apply_tag_filters(queryset)

    @extend_schema(
        tags=["Story Wikis"],
        summary="Get story wiki overview",
    )
    @action(detail=True, methods=["get"])
    def wiki(self, request, pk=None):
        """Return wiki data for a story subtree."""
        story = self.get_object()

        if story.kind == models.Story.Kind.PART:
            return Response(
                {
                    "detail": (
                        "Wiki is only available for STORY "
                        "or STANDALONE stories."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        stories = get_visible_story_subtree(story, request.user)
        story_child_map = build_story_child_map(stories)
        wiki_entities = get_story_wiki_entities(stories)
        metadata = get_story_wiki_metadata(story, stories, wiki_entities)

        serializer_context = self.get_serializer_context()
        serializer_context["story_child_map"] = story_child_map

        aggregated = {
            "characters": serializers.WikiCharacterSerializer(
                wiki_entities["characters"],
                many=True,
                context=serializer_context,
            ).data,
            "items": serializers.WikiItemSerializer(
                wiki_entities["items"],
                many=True,
                context=serializer_context,
            ).data,
            "locations": serializers.WikiLocationSerializer(
                wiki_entities["locations"],
                many=True,
                context=serializer_context,
            ).data,
            "factions": serializers.WikiFactionSerializer(
                wiki_entities["factions"],
                many=True,
                context=serializer_context,
            ).data,
        }

        tree = serializers.StoryWikiTreeSerializer(
            story,
            context=serializer_context,
        ).data

        return Response(
            {
                "story": metadata,
                "aggregated": aggregated,
                "tree": tree,
            }
        )

    @extend_schema(
        tags=["Story Wikis"],
        summary="Get character wiki page",
    )
    @action(
        detail=True,
        methods=["get"],
        url_path=r"wiki/characters/(?P<character_id>[^/.]+)",
    )
    def wiki_character(self, request, pk=None, character_id=None):
        """Return character wiki data within a story subtree context."""
        story = self.get_object()

        if story.kind == models.Story.Kind.PART:
            return Response(
                {
                    "detail": (
                        "Wiki is only available for STORY "
                        "or STANDALONE stories."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        visible_stories = get_visible_story_subtree(story, request.user)
        visible_story_ids = {
            visible_story.id for visible_story in visible_stories
        }

        character = get_object_or_404(models.Character, id=character_id)

        if not character.stories.filter(id__in=visible_story_ids).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer_context = self.get_serializer_context()
        serializer_context["visible_stories"] = visible_stories

        serializer = serializers.CharacterWikiDetailSerializer(
            character,
            context=serializer_context,
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Story Wikis"],
        summary="Get location wiki page",
    )
    @action(
        detail=True,
        methods=["get"],
        url_path=r"wiki/locations/(?P<location_id>[^/.]+)",
    )
    def wiki_location(self, request, pk=None, location_id=None):
        """Return location wiki data within a story subtree context."""
        story = self.get_object()

        if story.kind == models.Story.Kind.PART:
            return Response(
                {
                    "detail": (
                        "Wiki is only available for STORY "
                        "or STANDALONE stories."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        visible_stories = get_visible_story_subtree(story, request.user)
        visible_story_ids = {
            visible_story.id for visible_story in visible_stories
        }

        location = get_object_or_404(models.Location, id=location_id)

        if not location.stories.filter(id__in=visible_story_ids).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer_context = self.get_serializer_context()
        serializer_context["visible_stories"] = visible_stories

        serializer = serializers.LocationWikiDetailSerializer(
            location,
            context=serializer_context,
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Story Wikis"],
        summary="Get item wiki page",
    )
    @action(
        detail=True,
        methods=["get"],
        url_path=r"wiki/items/(?P<item_id>[^/.]+)",
    )
    def wiki_item(self, request, pk=None, item_id=None):
        """Return item wiki data within a story subtree context."""
        story = self.get_object()

        if story.kind == models.Story.Kind.PART:
            return Response(
                {
                    "detail": (
                        "Wiki is only available for STORY "
                        "or STANDALONE stories."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        visible_stories = get_visible_story_subtree(story, request.user)
        visible_story_ids = {
            visible_story.id for visible_story in visible_stories
        }

        item = get_object_or_404(models.Item, id=item_id)

        if not item.stories.filter(id__in=visible_story_ids).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer_context = self.get_serializer_context()
        serializer_context["visible_stories"] = visible_stories

        serializer = serializers.ItemWikiDetailSerializer(
            item,
            context=serializer_context,
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Story Wikis"],
        summary="Get faction wiki page",
    )
    @action(
        detail=True,
        methods=["get"],
        url_path=r"wiki/factions/(?P<faction_id>[^/.]+)",
    )
    def wiki_faction(self, request, pk=None, faction_id=None):
        """Return faction wiki data within a story subtree context."""
        story = self.get_object()

        if story.kind == models.Story.Kind.PART:
            return Response(
                {
                    "detail": (
                        "Wiki is only available for STORY "
                        "or STANDALONE stories."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        visible_stories = get_visible_story_subtree(story, request.user)
        visible_story_ids = {
            visible_story.id for visible_story in visible_stories
        }

        faction = get_object_or_404(models.Faction, id=faction_id)

        if not faction.stories.filter(id__in=visible_story_ids).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer_context = self.get_serializer_context()
        serializer_context["visible_stories"] = visible_stories

        serializer = serializers.FactionWikiDetailSerializer(
            faction,
            context=serializer_context,
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

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

from core import models, serializers
from core.permissions import IsOwnerOrReadOnly

from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.ai_client import (
    LoreAIService,
    AiServiceError,
    DailyBudgetExceeded
)
from core.throttling import AIUserThrottle


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

        # Build the text to send to AI
        parts = [
            story.title or "",
            story.summary or "",
            story.body or "",
        ]
        text = "\n\n".join(p for p in parts if p and p.strip())

        if not text:
            return Response(
                {
                    "detail": "Nothing to analyze "
                    "(title/summary/body are empty)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = LoreAIService()

        try:
            analysis = service.analyze_text(text)
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
        """Set the created_by user on creation."""
        serializer.save(created_by=self.request.user)

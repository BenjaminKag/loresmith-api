"""
ViewSet for Character objects.
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
from core.services.character_profile_generator import (
    CharacterProfileGenerator,
)
from core.services.ai_client import AiServiceError

from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    tags=["Characters"],
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
class CharacterViewSet(TagFilterMixin, viewsets.ModelViewSet):
    """ViewSet for managing Character objects via the API."""

    serializer_class = serializers.CharacterSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    ]

    def perform_create(self, serializer):
        """Set the owner user on creation."""
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        base_queryset = (
            models.Character.objects
            .select_related("location", "owner")
            .prefetch_related("affiliations", "equipment", "tags")
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

    @action(detail=True, methods=["get"], url_path="profile-options")
    def profile_options(self, request, pk=None):
        """Return grouped trait options for a character."""
        character = self.get_object()

        trait_sets = character.profile_trait_sets.all()

        data = []

        for trait_set in trait_sets:
            traits = trait_set.traits.all()

            data.append({
                "set": {
                    "id": trait_set.id,
                    "name": trait_set.name,
                },
                "traits": [
                    {"key": t.key, "label": t.label}
                    for t in traits
                ]
            })

        serializer = serializers.TraitGroupSerializer(data, many=True)
        return Response(serializer.data)

    @extend_schema(
        request={
            "type": "object",
            "properties": {
                "include_story_context": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Whether to include related story "
                        "context in AI generation."
                    ),
                }
            },
            "required": [],
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "profile": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "meta": {
                        "type": "object",
                    },
                },
            }
        },
        description=(
            "Generate a suggested profile for an existing character. "
            "The result is not saved automatically. "
            "Only the character owner can use this action."
        ),
    )
    @action(detail=True, methods=["post"], url_path="generate-profile")
    def generate_profile(self, request, pk=None):
        character = get_object_or_404(
            models.Character.objects.filter(owner=request.user),
            pk=pk,
        )

        include_story_context = request.data.get(
            "include_story_context",
            False,
        )

        generator = CharacterProfileGenerator()

        try:
            result = generator.generate(
                character,
                include_story_context=include_story_context,
            )
        except AiServiceError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)

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

# from django.db.models import Q
from django.shortcuts import get_object_or_404

from core import models, serializers
from core.mixins import TagFilterMixin
from core.permissions import IsOwnerOrReadOnly, IsPremiumUserForAI
from core.services import ai_idempotency, ai_usage
from core.services.character_profile_generator import (
    CharacterProfileGenerator,
)
from core.services.ai_client import AiServiceError, DailyBudgetExceeded

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

        """
        # Owners can see all their characters.
        # Everyone can see characters in public stories.

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

        # Only show characters owned by the user,
        # since the profile generation relies on that.

        if user.is_authenticated:
            queryset = base_queryset.filter(owner=user)

        else:
            queryset = base_queryset.none()

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
    @action(
        detail=True,
        methods=["post"],
        url_path="generate-profile",
        permission_classes=[
            permissions.IsAuthenticated,
            IsOwnerOrReadOnly,
            IsPremiumUserForAI,
        ],
    )
    def generate_profile(self, request, pk=None):
        character = get_object_or_404(
            models.Character.objects.filter(owner=request.user),
            pk=pk,
        )

        include_story_context = request.data.get(
            "include_story_context",
            False,
        )

        request_payload = {
            "character_id": character.id,
            "character_input": {
                "name": character.name,
                "description": character.description,
                "profile_trait_sets": [
                    {
                        "id": trait_set.id,
                        "name": trait_set.name,
                        "traits": [
                            {
                                "key": trait.key,
                                "label": trait.label,
                            }
                            for trait in trait_set.traits.all()
                        ],
                    }
                    for trait_set in (
                        character.profile_trait_sets
                        .prefetch_related("traits")
                        .all()
                    )
                ],
            },
            "settings": {
                "endpoint_type": models.AIEndpointType.CHARACTER_PROFILE,
                "include_story_context": include_story_context,
            },
        }

        try:
            request_log, created = (
                ai_idempotency.create_in_progress_request(
                    user=request.user,
                    endpoint_type=models.AIEndpointType.CHARACTER_PROFILE,
                    request_payload=request_payload,
                )
            )
        except ai_idempotency.AIRequestInProgress:
            return Response(
                {
                    "detail": (
                        "A matching character profile generation request "
                        "is already in progress."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not created:
            response_data = dict(request_log.response_payload)
            meta = dict(response_data.get("meta", {}))
            meta["deduped"] = True
            response_data["meta"] = meta

            return Response(response_data, status=status.HTTP_200_OK)

        generator = CharacterProfileGenerator()

        try:
            result = generator.generate(
                character,
                user=request.user,
                include_story_context=include_story_context,
            )

            ai_idempotency.mark_request_completed(
                request_log,
                result,
            )

            ai_usage.record_ai_usage(
                user=request.user,
                endpoint_type=models.AIEndpointType.CHARACTER_PROFILE,
                meta=result.get("meta", {}),
                request_log=request_log,
            )

        except DailyBudgetExceeded as exc:
            ai_idempotency.mark_request_failed(request_log, str(exc))
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        except AiServiceError as exc:
            ai_idempotency.mark_request_failed(request_log, str(exc))
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)

    @extend_schema(
        request=serializers.CharacterProfileApplySerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "profile": {"type": "object"},
                },
            }
        },
        description=(
            "Save or replace a character profile. "
            "The submitted profile must use selected trait sets and traits."
        ),
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="apply-profile",
        permission_classes=[
            permissions.IsAuthenticated,
            IsOwnerOrReadOnly,
        ],
    )
    def apply_profile(self, request, pk=None):
        """Save or replace a character profile."""
        character = get_object_or_404(
            models.Character.objects.filter(owner=request.user),
            pk=pk,
        )

        serializer = serializers.CharacterProfileApplySerializer(
            data=request.data,
            context={
                **self.get_serializer_context(),
                "character": character,
            },
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()

        return Response(
            {
                "profile": profile.data,
            },
            status=status.HTTP_200_OK,
        )

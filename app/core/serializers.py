"""
Serializers for core models.
"""

from rest_framework import serializers
from . import models


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model."""
    image = serializers.ImageField(
        use_url=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = models.Location
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "owner")

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)


class FactionSerializer(serializers.ModelSerializer):
    """Serializer for Faction model."""
    image = serializers.ImageField(
        use_url=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = models.Faction
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "owner")

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)


class ItemSerializer(serializers.ModelSerializer):
    """Serializer for Item model."""
    image = serializers.ImageField(
        use_url=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = models.Item
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "owner")

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)


class CharacterSerializer(serializers.ModelSerializer):
    """Serializer for Character model."""
    image = serializers.ImageField(
        use_url=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = models.Character
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "owner")

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            location = attrs.get("location")
            affiliations = attrs.get("affiliations", [])
            equipment = attrs.get("equipment", [])

            if location and location.owner != user:
                raise serializers.ValidationError({
                    "location":
                    "You can only assign your own locations."
                })

            for faction in affiliations:
                if faction.owner != user:
                    raise serializers.ValidationError({
                        "affiliations":
                        "You can only assign your own factions."
                    })

            for item in equipment:
                if item.owner != user:
                    raise serializers.ValidationError({
                        "equipment":
                        "You can only assign your own items."
                    })

        return attrs


class StorySerializer(serializers.ModelSerializer):
    """Serializer for Story model."""
    image = serializers.ImageField(
        use_url=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = models.Story
        fields = "__all__"
        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
            "owner"
        )

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        parent = attrs.get("parent", getattr(self.instance, "parent", None))

        # story / standalone must be root
        if kind in {
            models.Story.Kind.STORY,
            models.Story.Kind.STANDALONE,
        } and parent is not None:
            raise serializers.ValidationError(
                {"parent": f"{kind} entries cannot have a parent."}
            )

        # part must have a parent
        if kind == models.Story.Kind.PART and parent is None:
            raise serializers.ValidationError(
                {"parent": "Part entries must have a parent."}
            )

        # part can only belong to story or part
        if kind == models.Story.Kind.PART and parent is not None:
            if parent.kind not in {
                models.Story.Kind.STORY,
                models.Story.Kind.PART,
            }:
                raise serializers.ValidationError(
                    {
                        "parent": (
                            "Part entries can only belong to a story "
                            "or another part."
                        )
                    }
                )

        # prevent self-parenting on update
        if self.instance and parent and self.instance.pk == parent.pk:
            raise serializers.ValidationError(
                {"parent": "A story cannot be its own parent."}
            )

        # standalone cannot have children
        if (
            self.instance
            and kind == models.Story.Kind.STANDALONE
            and self.instance.sub_stories.exists()
        ):
            raise serializers.ValidationError(
                {"kind": "Standalone entries cannot have child stories."}
            )

        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            characters = attrs.get("characters", [])
            locations = attrs.get("locations", [])
            factions = attrs.get("factions", [])
            items = attrs.get("items", [])

            for character in characters:
                if character.owner != user:
                    raise serializers.ValidationError({
                        "characters":
                        "You can only assign your own characters."
                    })

            for location in locations:
                if location.owner != user:
                    raise serializers.ValidationError({
                        "locations":
                        "You can only assign your own locations."
                    })

            for faction in factions:
                if faction.owner != user:
                    raise serializers.ValidationError({
                        "factions":
                        "You can only assign your own factions."
                    })

            for item in items:
                if item.owner != user:
                    raise serializers.ValidationError({
                        "items":
                        "You can only assign your own items."
                    })

        return attrs


class StoryAIAnalysisMetaSerializer(serializers.Serializer):
    ai_mode = serializers.CharField()
    model = serializers.CharField(allow_null=True, required=False)
    input_tokens = serializers.IntegerField(allow_null=True, required=False)
    output_tokens = serializers.IntegerField(allow_null=True, required=False)
    total_tokens = serializers.IntegerField(allow_null=True, required=False)


class StoryAIAnalysisSerializer(serializers.Serializer):
    entity_type = serializers.CharField()
    entity_id = serializers.IntegerField()
    entity_label = serializers.CharField()

    summary = serializers.CharField()
    themes = serializers.ListField(child=serializers.CharField())
    tone = serializers.CharField()
    strengths = serializers.ListField(child=serializers.CharField())
    weaknesses = serializers.ListField(child=serializers.CharField())
    suggestions = serializers.ListField(child=serializers.CharField())

    meta = StoryAIAnalysisMetaSerializer()

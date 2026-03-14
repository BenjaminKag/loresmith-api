"""
Serializers for core models.
"""
from rest_framework import serializers
from . import models


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model."""
    class Meta:
        model = models.Location
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "created_by")


class FactionSerializer(serializers.ModelSerializer):
    """Serializer for Faction model."""
    class Meta:
        model = models.Faction
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "created_by")


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Item
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "created_by")


class CharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Character
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "created_by")


class StorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Story
        fields = "__all__"
        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
            "created_by"
        )

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

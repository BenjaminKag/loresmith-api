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
        read_only_fields = ("id", "slug", "created_at", "updated_at", "created_by")


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

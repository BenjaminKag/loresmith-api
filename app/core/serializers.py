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

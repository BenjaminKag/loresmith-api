"""
Admin configuration for LoreSmith core models.
"""
from django.contrib import admin  # noqa: F401

from . import models


@admin.register(models.Location)
class LocationAdmin(admin.ModelAdmin):
    """Admin for Location model."""

    list_display = (
        "name",
        "location_type",
        "parent",
        "created_by",
        "created_at"
    )
    list_filter = ("location_type", "created_by")
    search_fields = ("name", "description", "parent__name")
    raw_id_fields = ("parent", "created_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Faction)
class FactionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "faction_type",
        "location",
        "created_by",
        "created_at"
    )
    list_filter = ("faction_type", "created_by")
    search_fields = ("name", "description", "location__name")
    raw_id_fields = ("location", "created_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "item_type", "rarity", "created_by", "created_at")
    list_filter = ("item_type", "rarity", "created_by")
    search_fields = ("name", "description")
    raw_id_fields = ("created_by",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "species",
        "gender",
        "location",
        "created_by",
        "created_at"
    )
    list_filter = ("species", "gender", "created_by")
    search_fields = ("name", "description", "location__name")
    raw_id_fields = ("location", "created_by")
    filter_horizontal = ("affiliations", "equipment")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "kind",
        "story_type",
        "visibility",
        "created_by",
        "created_at",
    )
    list_filter = ("kind", "story_type", "visibility", "created_by")
    search_fields = ("title", "summary", "body")
    raw_id_fields = ("parent", "created_by")
    filter_horizontal = ("characters", "locations", "factions", "items")
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("title",)}

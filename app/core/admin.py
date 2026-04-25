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
        "owner",
        "created_at"
    )
    list_filter = ("location_type", "owner")
    search_fields = ("name", "description", "parent__name")
    raw_id_fields = ("parent", "owner")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Faction)
class FactionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "faction_type",
        "location",
        "owner",
        "created_at"
    )
    list_filter = ("faction_type", "owner")
    search_fields = ("name", "description", "location__name")
    raw_id_fields = ("location", "owner")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "item_type", "rarity", "owner", "created_at")
    list_filter = ("item_type", "rarity", "owner")
    search_fields = ("name", "description")
    raw_id_fields = ("owner",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "location",
        "owner",
        "created_at"
    )
    list_filter = ("owner",)
    search_fields = ("name", "description", "location__name")
    raw_id_fields = ("location", "owner")
    filter_horizontal = ("affiliations", "equipment")
    readonly_fields = ("created_at", "updated_at")


@admin.register(models.Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "kind",
        "story_type",
        "visibility",
        "owner",
        "created_at",
    )
    list_filter = ("kind", "story_type", "visibility", "owner")
    search_fields = ("title", "summary", "body")
    raw_id_fields = ("parent", "owner")
    filter_horizontal = ("characters", "locations", "factions", "items")
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    list_filter = ("owner",)
    search_fields = ("name",)


@admin.register(models.TraitSet)
class TraitSetAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_default", "created_at")
    list_filter = ("is_default", "owner")
    search_fields = ("name",)
    readonly_fields = ("slug",)


@admin.register(models.Trait)
class TraitAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "trait_set")
    list_filter = ("trait_set",)
    search_fields = ("label", "key")
    readonly_fields = ("key",)

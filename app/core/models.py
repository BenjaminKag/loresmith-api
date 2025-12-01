"""
Core models for LoreSmith application.
"""
from django.db import models
from django.conf import settings


class Location(models.Model):
    """Represents a place in the world."""

    class Meta:
        ordering = ["name"]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    location_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. continent, country, city, bar, dungeon"
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sub_locations",
        help_text="If set, this location is inside another location."
    )

    tags = models.JSONField(default=list, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locations",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Faction(models.Model):
    """Represents a group, affiliation, organization, clan, etc."""

    class Meta:
        ordering = ["name"]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    faction_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. kingdom, guild, clan, cult, company, etc."
    )

    location = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="factions",
        help_text="Primary location associated with this faction."
    )

    # To be made a model in the future
    tags = models.JSONField(default=list, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="factions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Item(models.Model):
    """Represents weapons, tools, artifacts, gear, etc."""

    class Meta:
        ordering = ["name"]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    item_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. weapon, armor, artifact, tool, consumable, etc."
    )
    rarity = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. common, rare, legendary, etc."
    )

    tags = models.JSONField(default=list, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Character(models.Model):
    """Core character model."""

    class Meta:
        ordering = ["name"]

    # Basic identity
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    age = models.IntegerField(null=True, blank=True)
    age_description = models.CharField(max_length=50, blank=True)
    # To be made a model in the future
    species = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=50, blank=True)

    affiliations = models.ManyToManyField(
        Faction,
        blank=True,
        related_name="members",
    )

    location = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="characters",
        help_text="Primary location associated with this character."
    )

    # Relationships
    # Example structure:
    # {
    #   "mentor": [character_id, ...],
    #   "siblings": [character_id, ...]
    # }
    relationships = models.JSONField(default=dict, blank=True)

    equipment = models.ManyToManyField(
        Item,
        blank=True,
        related_name="holders",
    )

    tags = models.JSONField(default=list, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="characters",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

"""
Core models for LoreSmith application.
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.exceptions import ValidationError


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

    tags = models.JSONField(default=list, null=True, blank=True)
    extra_data = models.JSONField(default=dict, null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_locations",
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
    tags = models.JSONField(default=list, null=True, blank=True)
    extra_data = models.JSONField(default=dict, null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_factions",
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

    tags = models.JSONField(default=list, null=True, blank=True)
    extra_data = models.JSONField(default=dict, null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_items",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Character(models.Model):
    """Core character model."""

    class Meta:
        ordering = ["name"]

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

    tags = models.JSONField(default=list, null=True, blank=True)
    extra_data = models.JSONField(default=dict, null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_characters",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Story(models.Model):
    """Represents a full story or a lore entry."""

    class Meta:
        ordering = ["kind", "parent__id", "order", "title"]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    summary = models.TextField(blank=True)
    body = models.TextField(blank=True)

    # Hierarchy rules:
    # - story: root entry that can contain parts
    # - standalone: root entry that cannot contain children
    # - part: nested section under story or part
    class Kind(models.TextChoices):
        STORY = "story", "Story"
        STANDALONE = "standalone", "Standalone"
        PART = "part", "Part"

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.STANDALONE,
    )

    class StoryType(models.TextChoices):
        LORE = "lore_entry", "Main Lore Entry"
        QUEST = "quest", "Quest"
        BACKSTORY = "backstory", "Backstory"
        WORLD_EVENT = "world_event", "World Event"
        MYTH = "myth", "Myth / Legend"
        DIALOGUE = "dialogue", "Dialogue"
        OTHER = "other", "Other"

    story_type = models.CharField(
        max_length=50,
        choices=StoryType.choices,
        default=StoryType.LORE,
    )

    class Visibility(models.TextChoices):
        DRAFT = "draft", "Draft"
        PRIVATE = "private", "Private"
        PUBLIC = "public", "Public"
        ARCHIVED = "archived", "Archived"

    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )

    in_world_date = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. 'Year 1107 AE', 'Before the Archon War'"
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sub_stories",
    )
    order = models.PositiveIntegerField(default=0)

    characters = models.ManyToManyField(
        "Character",
        blank=True,
        related_name="stories"
    )
    locations = models.ManyToManyField(
        "Location",
        blank=True,
        related_name="stories"
    )
    factions = models.ManyToManyField(
        "Faction",
        blank=True,
        related_name="stories"
    )
    items = models.ManyToManyField(
        "Item",
        blank=True,
        related_name="stories"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_stories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def clean(self):
        # story and standalone must be root
        if (
            self.kind in {self.Kind.STORY, self.Kind.STANDALONE}
            and self.parent is not None
        ):
            raise ValidationError({
                "parent": f"{self.kind} entries cannot have a parent."
            })

        # part must have a parent
        if self.kind == self.Kind.PART and self.parent is None:
            raise ValidationError({
                "parent": "Part entries must have a parent."
            })

        # part can only be under story or part
        if (
            self.kind == self.Kind.PART
            and self.parent is not None
        ):
            if self.parent.kind not in {self.Kind.STORY, self.Kind.PART}:
                raise ValidationError({
                    "parent":
                    "Part entries can only belong to a story or another part."
                })

        # prevent self-parenting
        if self.parent_id is not None and self.parent_id == self.id:
            raise ValidationError({
                "parent": "A story cannot be its own parent."
            })

        # standalone cannot have children
        if (
            self.kind == self.Kind.STANDALONE
            and self.pk
            and self.sub_stories.exists()
        ):
            raise ValidationError({
                "kind": "Standalone entries cannot have child stories."
            })

        # public child requires public parent
        if (
            self.visibility == self.Visibility.PUBLIC
            and self.parent is not None
            and self.parent.visibility != self.Visibility.PUBLIC
        ):
            raise ValidationError({
                "visibility": "A public story cannot have a non-public parent."
            })

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        self.full_clean()
        super().save(*args, **kwargs)

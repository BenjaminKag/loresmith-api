"""
Core models for LoreSmith application.
"""
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.exceptions import ValidationError

from .mixins import ImageCleanupMixin


DEFAULT_TRAIT_SETS = {
    "Physical Traits": [
        "Age",
        "Height",
        "Weight",
        "Eye Color",
        "Hair Color",
        "Species",
        "Gender",
        "Body Type",
        "Distinguishing Features",
    ],
    "Personality Traits": [
        "Quirks",
        "Fears",
        "Goals",
        "Strengths",
        "Weaknesses",
        "Values",
        "Temperament",
        "Hobbies",
    ],
}


def slugify_underscore(value: str) -> str:
    return slugify(value).replace("-", "_")


def create_default_trait_sets_for_user(user):
    """Create default trait sets and traits for a new user."""
    for set_name, trait_labels in DEFAULT_TRAIT_SETS.items():
        trait_set, _ = TraitSet.objects.get_or_create(
            owner=user,
            slug=slugify_underscore(set_name),
            defaults={
                "name": set_name,
                "is_default": True,
            },
        )

        for label in trait_labels:
            Trait.objects.get_or_create(
                trait_set=trait_set,
                key=slugify_underscore(label),
                defaults={"label": label},
            )


class TraitSet(models.Model):
    """User-defined grouping of traits (e.g. Physical, Personality)."""

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "slug"],
                name="unique_trait_set_slug_per_user"
            )
        ]

    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)

    is_default = models.BooleanField(default=False)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trait_sets",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.slug = slugify_underscore(self.name)

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Trait(models.Model):
    """Defines a single trait key within a trait set (e.g. age, height)."""

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(
                fields=["trait_set", "key"],
                name="unique_trait_key_per_set"
            )
        ]

    trait_set = models.ForeignKey(
        "TraitSet",
        on_delete=models.CASCADE,
        related_name="traits",
    )

    key = models.CharField(max_length=255)
    label = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.key = slugify_underscore(self.label)

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.trait_set.name}: {self.label}"


class Tag(models.Model):
    """User-scoped tag that can be attached to multiple entity types."""

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_tag_per_user"
            )
        ]

    name = models.CharField(max_length=100)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tags",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def normalize_name(self, name: str) -> str:
        """Normalize tag name for consistency."""
        # strip leading/trailing spaces
        name = name.strip()

        # collapse multiple spaces into one
        name = " ".join(name.split())

        # normalize casing (Title Case)
        name = name.title()

        return name

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.normalize_name(self.name)

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Location(ImageCleanupMixin, models.Model):
    """Represents a place in the world."""

    class Meta:
        ordering = ["name"]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    image = models.ImageField(
        null=True,
        blank=True,
        upload_to="uploads/location/"
    )

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

    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="locations",
    )

    extra_data = models.JSONField(default=dict, null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_locations",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        old_image = self._get_old_image()
        super().save(*args, **kwargs)
        self._delete_old_image_if_replaced(old_image)

    def delete(self, *args, **kwargs):
        self._delete_image_file()
        super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Faction(ImageCleanupMixin, models.Model):
    """Represents a group, affiliation, organization, clan, etc."""

    class Meta:
        ordering = ["name"]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    image = models.ImageField(
        null=True,
        blank=True,
        upload_to="uploads/faction/"
    )

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

    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="factions",
    )

    extra_data = models.JSONField(default=dict, null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_factions",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        old_image = self._get_old_image()
        super().save(*args, **kwargs)
        self._delete_old_image_if_replaced(old_image)

    def delete(self, *args, **kwargs):
        self._delete_image_file()
        super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Item(ImageCleanupMixin, models.Model):
    """Represents weapons, tools, artifacts, gear, etc."""

    class Meta:
        ordering = ["name"]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    image = models.ImageField(
        null=True,
        blank=True,
        upload_to="uploads/item/"
    )

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

    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="items",
    )

    extra_data = models.JSONField(default=dict, null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_items",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        old_image = self._get_old_image()
        super().save(*args, **kwargs)
        self._delete_old_image_if_replaced(old_image)

    def delete(self, *args, **kwargs):
        self._delete_image_file()
        super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Character(ImageCleanupMixin, models.Model):
    """Core character model."""

    class Meta:
        ordering = ["name"]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(
        null=True,
        blank=True,
        upload_to="uploads/character/"
    )

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

    profile_trait_sets = models.ManyToManyField(
        "TraitSet",
        blank=True,
        related_name="characters",
    )

    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="characters",
    )

    extra_data = models.JSONField(default=dict, null=True, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_characters",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        old_image = self._get_old_image()
        super().save(*args, **kwargs)
        self._delete_old_image_if_replaced(old_image)

    def delete(self, *args, **kwargs):
        self._delete_image_file()
        super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class CharacterProfile(models.Model):
    """Structured profile values for a character."""

    character = models.OneToOneField(
        "Character",
        on_delete=models.CASCADE,
        related_name="profile",
    )

    data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile for {self.character.name}"


class Story(ImageCleanupMixin, models.Model):
    """Represents a full story or a lore entry."""

    class Meta:
        ordering = ["kind", "parent__id", "order", "title"]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    summary = models.TextField(blank=True)
    body = models.TextField(blank=True)
    image = models.ImageField(
        null=True,
        blank=True,
        upload_to="uploads/story/"
    )

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

    allowed_trait_sets = models.ManyToManyField(
        "TraitSet",
        blank=True,
        related_name="stories",
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
    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="stories",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
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
        old_image = self._get_old_image()

        self.slug = slugify(self.title)

        self.full_clean()
        super().save(*args, **kwargs)

        self._delete_old_image_if_replaced(old_image)

    def delete(self, *args, **kwargs):
        self._delete_image_file()
        super().delete(*args, **kwargs)

    def get_effective_trait_sets(self):
        """Return the trait sets effective for this story (inherit if PART)."""

        if self.kind != self.Kind.PART:
            return self.allowed_trait_sets.all()

        current = self.parent
        while current:
            if current.kind != self.Kind.PART:
                return current.allowed_trait_sets.all()
            current = current.parent

        return TraitSet.objects.none()

    def get_effective_trait_keys(self):
        """Return a set of allowed trait keys for this story."""

        trait_sets = self.get_effective_trait_sets()

        return set(
            Trait.objects.filter(
                trait_set__in=trait_sets
            ).values_list("key", flat=True)
        )


class StoryAnalysis(models.Model):
    """Stored AI analysis result for a story input snapshot."""

    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    input_hash = models.CharField(max_length=64)
    result = models.JSONField()
    ai_mode = models.CharField(max_length=20)
    model = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["story", "owner", "input_hash"],
                name="unique_story_analysis_per_input",
            ),
        ]
        indexes = [
            models.Index(fields=["story", "owner", "input_hash"]),
        ]

    def __str__(self):
        return f"Analysis for {self.story.title} ({self.input_hash[:8]})"

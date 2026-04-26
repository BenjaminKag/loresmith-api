"""
Serializers for core models.
"""

from rest_framework import serializers
from . import models, utils
from core.mixins import TagNamesMixin


def get_default_trait_sets_for_user(user):
    """Return the user's default trait sets."""
    return models.TraitSet.objects.filter(
        owner=user,
        is_default=True,
    )


class TraitSetSerializer(serializers.ModelSerializer):
    """Serializer for user-owned trait sets."""

    class Meta:
        model = models.TraitSet
        fields = (
            "id",
            "name",
            "slug",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Update a trait set and apply it to existing objects if made default.
        """
        was_default = instance.is_default

        instance = super().update(instance, validated_data)

        if not was_default and instance.is_default:
            for story in models.Story.objects.filter(
                owner=instance.owner
            ).exclude(kind=models.Story.Kind.PART):
                story.allowed_trait_sets.add(instance)

            for character in models.Character.objects.filter(
                owner=instance.owner
            ):
                character.profile_trait_sets.add(instance)

        return instance

    def validate_name(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return value

        slug = models.slugify_underscore(value)

        queryset = models.TraitSet.objects.filter(
            owner=user,
            slug=slug,
        )

        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError(
                "You already have a trait set with this name."
            )

        return value


class TraitSerializer(serializers.ModelSerializer):
    """Serializer for traits inside a trait set."""

    class Meta:
        model = models.Trait
        fields = (
            "id",
            "trait_set",
            "key",
            "label",
            "created_at",
        )
        read_only_fields = (
            "id",
            "key",
            "created_at",
        )

    def validate_trait_set(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user and user.is_authenticated and value.owner != user:
            raise serializers.ValidationError(
                "You can only add traits to your own trait sets."
            )

        return value

    def validate(self, attrs):
        trait_set = attrs.get(
            "trait_set",
            getattr(self.instance, "trait_set", None)
        )
        label = attrs.get("label", getattr(self.instance, "label", None))

        if trait_set and label:
            key = models.slugify_underscore(label)

            queryset = models.Trait.objects.filter(
                trait_set=trait_set,
                key=key,
            )

            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)

            if queryset.exists():
                raise serializers.ValidationError({
                    "label": "This trait already exists in this trait set."
                })

        return attrs


class TraitGroupSerializer(serializers.Serializer):
    """Grouped traits by trait set."""

    set = serializers.DictField()
    traits = serializers.ListField()


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model."""

    class Meta:
        model = models.Tag
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user
        return super().create(validated_data)

    def validate_name(self, value):
        """Ensure tag name is unique per user."""
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return value

        # normalize once
        normalized_name = value.title()

        queryset = models.Tag.objects.filter(
            owner=user,
            name=normalized_name,
        )

        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError(
                "You already have a tag with this name."
            )

        return normalized_name


class LocationSerializer(TagNamesMixin, serializers.ModelSerializer):
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
        tags = validated_data.pop("tags", [])

        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user

        instance = super().create(validated_data)

        if tags:
            self._replace_tags(instance, tags)

        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        instance = super().update(instance, validated_data)

        if tags is not None:
            self._replace_tags(instance, tags)

        return instance


class FactionSerializer(TagNamesMixin, serializers.ModelSerializer):
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
        tags = validated_data.pop("tags", [])

        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user

        instance = super().create(validated_data)

        if tags:
            self._replace_tags(instance, tags)

        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        instance = super().update(instance, validated_data)

        if tags is not None:
            self._replace_tags(instance, tags)

        return instance


class ItemSerializer(TagNamesMixin, serializers.ModelSerializer):
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
        tags = validated_data.pop("tags", [])

        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user

        instance = super().create(validated_data)

        if tags:
            self._replace_tags(instance, tags)

        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        instance = super().update(instance, validated_data)

        if tags is not None:
            self._replace_tags(instance, tags)

        return instance


class CharacterSerializer(TagNamesMixin, serializers.ModelSerializer):
    """Serializer for Character model."""
    image = serializers.ImageField(
        use_url=True,
        required=False,
        allow_null=True
    )

    profile = serializers.JSONField(required=False)

    class Meta:
        model = models.Character
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "owner")

    def to_representation(self, instance):
        """
        Customize the output representation of a Character.

        Since the profile is stored in a separate CharacterProfile model,
        we manually inject it into the response.

        If a profile exists, return its JSON data.
        Otherwise, return null.
        """
        representation = super().to_representation(instance)

        if hasattr(instance, "profile"):
            representation["profile"] = instance.profile.data
        else:
            representation["profile"] = None

        return representation

    def _merge_profile_data(self, existing_data, incoming_data):
        """Merge incoming profile data into existing profile data."""
        merged_data = existing_data.copy()

        for key, value in incoming_data.items():
            normalized_key = models.slugify_underscore(key)

            if value is None:
                merged_data.pop(normalized_key, None)
            else:
                merged_data[normalized_key] = value

        return merged_data

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        profile_data = validated_data.pop("profile", None)

        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user

        instance = super().create(validated_data)

        if tags:
            self._replace_tags(instance, tags)

        default_trait_sets = get_default_trait_sets_for_user(instance.owner)
        instance.profile_trait_sets.add(*default_trait_sets)

        if profile_data is not None:
            models.CharacterProfile.objects.create(
                character=instance,
                data=self._merge_profile_data({}, profile_data),
            )

        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        profile_data = validated_data.pop("profile", None)

        instance = super().update(instance, validated_data)

        if tags is not None:
            self._replace_tags(instance, tags)

        if profile_data is not None:
            profile, _ = models.CharacterProfile.objects.get_or_create(
                character=instance,
            )
            profile.data = self._merge_profile_data(
                profile.data,
                profile_data
            )
            profile.save()

        return instance

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        profile_data = attrs.get("profile")

        # If profile data is provided, validate that all keys
        # correspond to valid traits for this user.
        if profile_data is not None and user and user.is_authenticated:
            # Determine which trait sets to use
            if self.instance:
                trait_sets = self.instance.profile_trait_sets.all()
            else:
                trait_sets = attrs.get("profile_trait_sets")

            # If character has selected trait sets → use them
            if trait_sets:
                valid_keys = set(
                    models.Trait.objects.filter(
                        trait_set__in=trait_sets
                    ).values_list("key", flat=True)
                )
            else:
                # fallback: allow all user traits
                valid_keys = set(
                    models.Trait.objects.filter(
                        trait_set__owner=user
                    ).values_list("key", flat=True)
                )

            # Normalize incoming keys
            incoming_keys = {
                models.slugify_underscore(key)
                for key in profile_data.keys()
            }

            invalid_keys = incoming_keys - valid_keys

            if invalid_keys:
                allowed_keys_sorted = sorted(valid_keys)

                raise serializers.ValidationError({
                    "profile": (
                        f"Invalid trait(s): {sorted(invalid_keys)}. "
                        f"Allowed traits: {allowed_keys_sorted}"
                    )
                })

        # Validate profile_trait_sets against story.allowed_trait_sets
        if user and user.is_authenticated:
            # Determine incoming or existing trait sets
            if self.instance:
                profile_trait_sets = attrs.get(
                    "profile_trait_sets",
                    self.instance.profile_trait_sets.all()
                )
            else:
                profile_trait_sets = attrs.get("profile_trait_sets")

            # If no trait sets provided -> nothing to validate
            if profile_trait_sets:
                # Determine stories (incoming or existing)
                if self.instance:
                    stories = attrs.get("stories", self.instance.stories.all())
                else:
                    stories = attrs.get("stories")

                if stories:
                    allowed_sets = set()

                    for story in stories:
                        # Resolve root story (handle PART)
                        root = story
                        while root.parent:
                            root = root.parent

                        # Add allowed sets from root story
                        allowed_sets.update(root.allowed_trait_sets.all())

                    profile_set_ids = {ts.id for ts in profile_trait_sets}
                    allowed_set_ids = {ts.id for ts in allowed_sets}

                    invalid_sets = profile_set_ids - allowed_set_ids

                    if invalid_sets:
                        invalid_set_names = [
                            ts.name for ts in profile_trait_sets
                            if ts.id in invalid_sets
                        ]

                        raise serializers.ValidationError({
                            "profile_trait_sets": (
                                "Trait sets not allowed by stories: "
                                f"{invalid_set_names}"
                            )
                        })

        # If the user is authenticated, validate that any
        # assigned relationships belong to the user.
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


class StorySerializer(TagNamesMixin, serializers.ModelSerializer):
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
        tags = validated_data.pop("tags", [])

        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data["owner"] = request.user

        instance = super().create(validated_data)

        if tags:
            self._replace_tags(instance, tags)

        if instance.kind != models.Story.Kind.PART:
            default_trait_sets = get_default_trait_sets_for_user(
                instance.owner
            )
            instance.allowed_trait_sets.add(*default_trait_sets)

        return instance

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)

        instance = super().update(instance, validated_data)

        if tags is not None:
            self._replace_tags(instance, tags)

        return instance

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


# Wiki serializers

class WikiCharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Character
        fields = ["id", "name"]
        read_only_fields = fields


class WikiItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Item
        fields = ["id", "name"]
        read_only_fields = fields


class WikiLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Location
        fields = ["id", "name"]
        read_only_fields = fields


class WikiFactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Faction
        fields = ["id", "name"]
        read_only_fields = fields


class StoryWikiTreeSerializer(serializers.ModelSerializer):
    """Recursive serializer for story wiki tree nodes."""

    characters = WikiCharacterSerializer(many=True, read_only=True)
    items = WikiItemSerializer(many=True, read_only=True)
    locations = WikiLocationSerializer(many=True, read_only=True)
    factions = WikiFactionSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = models.Story
        fields = [
            "id",
            "title",
            "slug",
            "kind",
            "order",
            "characters",
            "items",
            "locations",
            "factions",
            "children",
        ]
        read_only_fields = fields

    def get_children(self, obj):
        child_map = self.context.get("story_child_map")

        if child_map is not None:
            children = child_map.get(obj.id, [])
        else:
            request = self.context.get("request")
            user = getattr(request, "user", None)

            children = [
                child for child in obj.sub_stories.all().order_by("order")
                if utils.is_story_visible_to_user(child, user)
            ]

        return StoryWikiTreeSerializer(
            children,
            many=True,
            context=self.context,
        ).data


class WikiStoryReferenceSerializer(serializers.ModelSerializer):
    """Minimal story reference for wiki detail pages."""

    class Meta:
        model = models.Story
        fields = ["id", "title"]
        read_only_fields = fields


class CharacterWikiDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for character wiki pages."""

    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    stories = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:
        model = models.Character
        fields = [
            "id",
            "name",
            "description",
            "image",
            "tags",
            "stories",
            "profile",
        ]
        read_only_fields = fields

    def get_stories(self, obj):
        visible_stories = self.context.get("visible_stories", [])
        visible_story_ids = {story.id for story in visible_stories}

        stories = obj.stories.filter(
            id__in=visible_story_ids
        ).order_by("order")

        return WikiStoryReferenceSerializer(
            stories,
            many=True,
            context=self.context,
        ).data

    def get_profile(self, obj):
        """Return character profile if it exists."""
        if hasattr(obj, "profile"):
            return obj.profile.data
        return None


class LocationWikiDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for location wiki pages."""

    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    stories = serializers.SerializerMethodField()

    class Meta:
        model = models.Location
        fields = [
            "id",
            "name",
            "description",
            "image",
            "location_type",
            "tags",
            "stories",
        ]
        read_only_fields = fields

    def get_stories(self, obj):
        visible_stories = self.context.get("visible_stories", [])
        visible_story_ids = {story.id for story in visible_stories}

        stories = obj.stories.filter(
            id__in=visible_story_ids
        ).order_by("order")

        return WikiStoryReferenceSerializer(
            stories,
            many=True,
            context=self.context,
        ).data


class ItemWikiDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for item wiki pages."""

    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    stories = serializers.SerializerMethodField()

    class Meta:
        model = models.Item
        fields = [
            "id",
            "name",
            "description",
            "image",
            "item_type",
            "rarity",
            "tags",
            "stories",
        ]
        read_only_fields = fields

    def get_stories(self, obj):
        visible_stories = self.context.get("visible_stories", [])
        visible_story_ids = {story.id for story in visible_stories}

        stories = obj.stories.filter(
            id__in=visible_story_ids
        ).order_by("order")

        return WikiStoryReferenceSerializer(
            stories,
            many=True,
            context=self.context,
        ).data


class FactionWikiDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for faction wiki pages."""

    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    stories = serializers.SerializerMethodField()

    class Meta:
        model = models.Faction
        fields = [
            "id",
            "name",
            "description",
            "image",
            "faction_type",
            "tags",
            "stories",
        ]
        read_only_fields = fields

    def get_stories(self, obj):
        visible_stories = self.context.get("visible_stories", [])
        visible_story_ids = {story.id for story in visible_stories}

        stories = obj.stories.filter(
            id__in=visible_story_ids
        ).order_by("order")

        return WikiStoryReferenceSerializer(
            stories,
            many=True,
            context=self.context,
        ).data

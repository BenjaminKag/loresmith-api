"""
Serializers for core models.
"""

from rest_framework import serializers
from . import models, utils
from core.mixins import TagNamesMixin


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

    class Meta:
        model = models.Character
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

    class Meta:
        model = models.Character
        fields = [
            "id",
            "name",
            "description",
            "image",
            "age",
            "species",
            "gender",
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

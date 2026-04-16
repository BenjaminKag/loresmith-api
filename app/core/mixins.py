"""
Reusable model mixins for core app.
"""

from rest_framework import serializers

from core import models


class ImageCleanupMixin:
    image_field_name = "image"

    def _get_old_image(self):
        """Fetch the previous image from DB (if exists)."""
        if not self.pk:
            return None

        try:
            old_instance = self.__class__.objects.get(pk=self.pk)
            return getattr(old_instance, self.image_field_name)
        except self.__class__.DoesNotExist:
            return None

    def _delete_old_image_if_replaced(self, old_image):
        """Delete old image if it was replaced or removed."""
        new_image = getattr(self, self.image_field_name)

        if old_image and old_image != new_image:
            old_image.delete(save=False)

    def _delete_image_file(self):
        """Delete current image file."""
        image = getattr(self, self.image_field_name)
        if image:
            image.delete(save=False)


class TagNamesField(serializers.ListField):
    """Accept tag names as input and serialize tag names as output."""

    child = serializers.CharField()

    def to_representation(self, value):
        # value may be a ManyRelatedManager, queryset, or plain iterable
        if hasattr(value, "all"):
            value = value.all()
        return [tag.name for tag in value]


class TagNamesMixin:
    """Shared tag handling for serializers that accept tag names."""

    def get_fields(self):
        fields = super().get_fields()
        fields["tags"] = TagNamesField(required=False)
        return fields

    def _get_request_user(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError(
                {"tags": "Authenticated user is required for tag handling."}
            )
        return user

    def _get_or_create_tags(self, tag_names):
        """Normalize, get or create tags for the current user."""
        user = self._get_request_user()
        tags = []

        for raw_name in tag_names:
            normalized_name = models.Tag(
                name=raw_name,
                owner=user,
            ).normalize_name(raw_name)

            tag, _ = models.Tag.objects.get_or_create(
                owner=user,
                name=normalized_name,
            )
            tags.append(tag)

        return tags

    def _replace_tags(self, instance, tag_names):
        """Replace instance tags from a list of tag names."""
        tags = self._get_or_create_tags(tag_names)
        instance.tags.set(tags)


class TagFilterMixin:
    """Mixin to filter queryset by tag names (AND logic)."""

    def apply_tag_filters(self, queryset):
        tags_param = self.request.query_params.get("tags")

        if not tags_param:
            return queryset

        tag_names = [
            tag.strip()
            for tag in tags_param.split(",")
            if tag.strip()
        ]

        for tag_name in tag_names:
            queryset = queryset.filter(
                tags__name__iexact=tag_name
            )

        return queryset.distinct()

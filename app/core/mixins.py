"""
Reusable model mixins for core app.
"""


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

# Gallery Form - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django import forms
from django.conf import settings
from projects.models.gallery import Gallery


class GalleryForm(forms.ModelForm):
    """Form for uploading and managing gallery images."""

    class Meta:
        model = Gallery
        fields = [
            'image',
            'caption',
            'is_primary',
            'display_order',
        ]
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'Image caption...'}),
            'display_order': forms.NumberInput(attrs={'min': '0'}),
        }
        labels = {
            'is_primary': 'Set as Primary/Cover Image',
            'display_order': 'Display Order',
        }
        help_texts = {
            'is_primary': 'Only one image can be primary per project',
            'display_order': 'Lower numbers appear first',
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with project context."""
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

    def clean_image(self):
        """Validate uploaded image."""
        image = self.cleaned_data.get('image')
        if not image:
            raise forms.ValidationError('Image is required.')

        # Check file size
        if image.size > settings.MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                f'Image size exceeds {settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB limit.'
            )

        # Check file extension
        ext = image.name.split('.')[-1].lower()
        allowed = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        if ext not in allowed:
            raise forms.ValidationError(
                f'Only {", ".join(allowed)} formats are allowed.'
            )

        return image

    def clean_is_primary(self):
        """Validate primary flag."""
        is_primary = self.cleaned_data.get('is_primary', False)
        if is_primary and self.project:
            # Check if project already has a primary image
            existing_primary = Gallery.objects.filter(
                project=self.project,
                is_primary=True
            )
            if self.instance and self.instance.pk:
                existing_primary = existing_primary.exclude(id=self.instance.pk)

            if existing_primary.exists():
                # Warn but allow - save will handle it
                pass

        return is_primary
"""
Service form with icon picker and image upload.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django import forms
from django.utils.text import slugify

from services.models import Service


# Font Awesome icon choices for construction services
# Values are full FA6 classes (style + icon). Templates render the value
# directly into the <i class="..."> attribute, so a missing prefix would
# produce an empty square.
ICON_CHOICES = [
    ('fas fa-drafting-compass', 'Drafting Compass'),
    ('fas fa-ruler-combined', 'Ruler Combined'),
    ('fas fa-pencil-ruler', 'Pencil Ruler'),
    ('fas fa-tools', 'Tools'),
    ('fas fa-hard-hat', 'Hard Hat'),
    ('fas fa-hammer', 'Hammer'),
    ('fas fa-wrench', 'Wrench'),
    ('fas fa-paint-roller', 'Paint Roller'),
    ('fas fa-palette', 'Palette'),
    ('fas fa-couch', 'Couch'),
    ('fas fa-building', 'Building'),
    ('fas fa-industry', 'Industry'),
    ('fas fa-warehouse', 'Warehouse'),
    ('fas fa-water', 'Water'),
    ('fas fa-road', 'Road'),
    ('fas fa-bridge', 'Bridge'),
    ('fas fa-city', 'City'),
    ('fas fa-flask', 'Flask'),
    ('fas fa-cogs', 'Cogs'),
    ('fas fa-cube', 'Cube'),
    ('fas fa-star', 'Star'),
    ('fas fa-check-circle', 'Check Circle'),
    ('fas fa-info-circle', 'Info Circle'),
]


class ServiceForm(forms.ModelForm):
    """
    Form for creating and editing services.
    """

    class Meta:
        model = Service
        fields = [
            'name',
            'category',
            'slug',
            'description',
            'long_description',
            'icon',
            'image',
            'features',
            'display_order',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Design & Construction'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'auto-generated from name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'long_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'icon': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'features': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter each feature on a new line...'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Service Name',
            'category': 'Category',
            'slug': 'Slug',
            'description': 'Short Description',
            'long_description': 'Detailed Description',
            'icon': 'Icon',
            'image': 'Service Image',
            'features': 'Key Features',
            'display_order': 'Display Order',
            'is_active': 'Active',
        }
        help_texts = {
            'slug': 'URL-friendly name. Leave blank to auto-generate.',
            'icon': 'Choose an icon that represents this service',
            'image': 'Recommended: 800x600px, max 5MB',
            'features': 'Enter one feature per line',
            'display_order': 'Lower numbers appear first',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['icon'].choices = ICON_CHOICES

    def clean_slug(self):
        """Auto-generate slug if not provided."""
        slug = self.cleaned_data.get('slug')
        name = self.cleaned_data.get('name')
        if not slug and name:
            slug = slugify(name)
        return slug

    def clean_features(self):
        """Convert features textarea to list."""
        features_text = self.cleaned_data.get('features', '')
        if features_text and isinstance(features_text, str):
            features = [line.strip() for line in features_text.split('\n') if line.strip()]
            return features
        return []

    def clean_image(self):
        """Validate image upload."""
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image size must be under 5MB')
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            ext = '.' + image.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError('Only JPG, PNG, GIF, and WEBP images are allowed')
        return image
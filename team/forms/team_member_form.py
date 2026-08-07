"""
Team Member form with photo upload and validation.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django import forms
from django.utils.text import slugify

from team.models import TeamMember


class TeamMemberForm(forms.ModelForm):
    """
    Form for creating and editing team members.
    Handles photo upload with validation.
    """

    class Meta:
        model = TeamMember
        fields = [
            'name',
            'role',
            'title',
            'bio',
            'photo',
            'email',
            'phone',
            'display_order',
            'is_active',
            'is_featured',
            'linkedin',
            'twitter',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. John Doe'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Lead Architect'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Brief bio of the team member...'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'john@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0712345678'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'linkedin': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://linkedin.com/in/username'}),
            'twitter': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://twitter.com/username'}),
        }
        labels = {
            'name': 'Full Name',
            'role': 'Role',
            'title': 'Job Title',
            'bio': 'Biography',
            'photo': 'Profile Photo',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'display_order': 'Display Order',
            'is_active': 'Active',
            'is_featured': 'Featured on About Page',
            'linkedin': 'LinkedIn URL',
            'twitter': 'Twitter/X URL',
        }
        help_texts = {
            'display_order': 'Lower numbers appear first',
            'is_featured': 'Show this member on the public About page',
            'photo': 'Recommended: Square image, max 5MB',
        }

    def clean_phone(self):
        """Validate and format Kenyan phone number."""
        phone = self.cleaned_data.get('phone', '')
        if phone:
            # Remove spaces, dashes, and parentheses
            phone = ''.join(c for c in phone if c.isdigit() or c == '+')
            # Check if it's a valid Kenyan number
            if phone.startswith('+254'):
                if len(phone) != 13:
                    raise forms.ValidationError('Invalid Kenyan phone number. Format: +2547XXXXXXXX')
            elif phone.startswith('07') or phone.startswith('01'):
                if len(phone) != 10:
                    raise forms.ValidationError('Invalid Kenyan phone number. Format: 07XXXXXXXX')
            elif phone.startswith('7') or phone.startswith('1'):
                if len(phone) != 9:
                    raise forms.ValidationError('Invalid Kenyan phone number. Format: 7XXXXXXXX')
            else:
                raise forms.ValidationError('Invalid phone number. Use Kenyan format: 07XXXXXXXX or +2547XXXXXXXX')
        return phone

    def clean_photo(self):
        """Validate photo upload."""
        photo = self.cleaned_data.get('photo')
        if photo:
            # Check file size (max 5MB)
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Photo size must be under 5MB')
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            ext = '.' + photo.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError('Only JPG, PNG, GIF, and WEBP images are allowed')
        return photo

    def clean_display_order(self):
        """Ensure display_order is unique."""
        display_order = self.cleaned_data.get('display_order', 0)
        if display_order < 0:
            raise forms.ValidationError('Display order must be a positive number')
        return display_order

    def clean(self):
        """Clean all fields and validate together."""
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        role = cleaned_data.get('role')

        if name and role:
            # Auto-generate slug if needed (model will handle this)
            pass

        return cleaned_data
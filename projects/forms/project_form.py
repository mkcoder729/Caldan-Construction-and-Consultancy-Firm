# Project Form - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django import forms
from django.utils import timezone
from projects.models.project import Project


class ProjectForm(forms.ModelForm):
    """Form for creating and editing projects."""

    class Meta:
        model = Project
        fields = [
            'name',
            'description',
            'location',
            'county',
            'town',
            'estate',
            'start_date',
            'end_date',
            'estimated_completion',
            'actual_completion',
            'budget',
            'spent',
            'status',
            'is_featured',
            'cover_photo',
            'latitude',
            'longitude',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'estimated_completion': forms.DateInput(attrs={'type': 'date'}),
            'actual_completion': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'budget': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'spent': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'latitude': forms.NumberInput(attrs={'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'step': '0.000001'}),
        }
        labels = {
            'name': 'Project Name',
            'county': 'County',
            'town': 'Town/City',
            'start_date': 'Start Date',
            'estimated_completion': 'Estimated Completion',
            'actual_completion': 'Actual Completion',
            'cover_photo': 'Cover Photo',
        }
        help_texts = {
            'budget': 'Total allocated budget in Kenyan Shillings (KES)',
            'spent': 'Total spent to date in Kenyan Shillings (KES)',
            'latitude': 'Latitude for map display (optional)',
            'longitude': 'Longitude for map display (optional)',
        }

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        estimated_completion = cleaned_data.get('estimated_completion')
        actual_completion = cleaned_data.get('actual_completion')
        budget = cleaned_data.get('budget')
        spent = cleaned_data.get('spent')

        # Validate dates
        if start_date and end_date and end_date < start_date:
            self.add_error(
                'end_date',
                'End date cannot be before start date.'
            )

        if start_date and estimated_completion and estimated_completion < start_date:
            self.add_error(
                'estimated_completion',
                'Estimated completion cannot be before start date.'
            )

        if start_date and actual_completion and actual_completion < start_date:
            self.add_error(
                'actual_completion',
                'Actual completion cannot be before start date.'
            )

        # Validate budget
        if budget is not None and budget < 0:
            self.add_error('budget', 'Budget cannot be negative.')

        if spent is not None and spent < 0:
            self.add_error('spent', 'Spent amount cannot be negative.')

        if budget is not None and spent is not None and spent > budget:
            self.add_error(
                'spent',
                'Spent amount cannot exceed total budget.'
            )

        return cleaned_data

    def clean_name(self):
        """Validate project name."""
        name = self.cleaned_data.get('name')
        if name and len(name.strip()) < 3:
            raise forms.ValidationError(
                'Project name must be at least 3 characters.'
            )
        return name.strip()

    def clean_county(self):
        """Validate county."""
        county = self.cleaned_data.get('county')
        if county and len(county.strip()) < 2:
            raise forms.ValidationError(
                'County name must be at least 2 characters.'
            )
        return county.strip()
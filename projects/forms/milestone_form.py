# Milestone Form - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django import forms
from django.utils import timezone
from projects.models.milestone import Milestone


class MilestoneForm(forms.ModelForm):
    """Form for creating and editing milestones."""

    class Meta:
        model = Milestone
        fields = [
            'title',
            'description',
            'target_date',
            'completed_date',
            'completion_percentage',
            'status',
            'photo',
            'notes',
            'order',
        ]
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}),
            'completed_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'completion_percentage': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
        }
        labels = {
            'title': 'Milestone Title',
            'target_date': 'Target Date',
            'completed_date': 'Completed Date',
            'completion_percentage': 'Completion Percentage',
        }
        help_texts = {
            'completion_percentage': 'Enter a value between 0 and 100',
            'order': 'Lower numbers appear first',
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with project context."""
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

        # Auto-set status based on completion if editing
        if self.instance and self.instance.pk:
            pass

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        target_date = cleaned_data.get('target_date')
        completed_date = cleaned_data.get('completed_date')
        completion_percentage = cleaned_data.get('completion_percentage')

        # Validate dates
        if target_date and completed_date and completed_date < target_date:
            self.add_error(
                'completed_date',
                'Completed date cannot be before target date.'
            )

        # Validate completion percentage
        if completion_percentage is not None:
            if completion_percentage < 0 or completion_percentage > 100:
                self.add_error(
                    'completion_percentage',
                    'Completion percentage must be between 0 and 100.'
                )

            # If 100%, completed_date should be set
            if completion_percentage >= 100 and not completed_date:
                self.add_error(
                    'completed_date',
                    'Please set a completed date for 100% complete milestones.'
                )

            # If completed_date is set, percentage should be 100
            if completed_date and completion_percentage < 100:
                self.add_error(
                    'completion_percentage',
                    'Completed date is set but completion is not 100%.'
                )

        return cleaned_data

    def clean_title(self):
        """Validate milestone title."""
        title = self.cleaned_data.get('title')
        if title and len(title.strip()) < 2:
            raise forms.ValidationError(
                'Title must be at least 2 characters.'
            )
        return title.strip()

    def clean_target_date(self):
        """Validate target date."""
        target_date = self.cleaned_data.get('target_date')
        if target_date:
            # Check if project has start date
            if self.project and self.project.start_date:
                if target_date < self.project.start_date:
                    raise forms.ValidationError(
                        'Target date cannot be before project start date.'
                    )

            # Don't allow dates more than 10 years in the future
            if target_date > timezone.now().date() + timezone.timedelta(days=3650):
                raise forms.ValidationError(
                    'Target date is too far in the future.'
                )

        return target_date
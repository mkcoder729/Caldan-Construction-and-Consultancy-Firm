"""
Backup form for creating and managing project backups.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django import forms

from projects.models import Project


class BackupForm(forms.Form):
    """
    Form for creating a project backup.
    Allows selection of project and related data to include.
    """

    # Project selection
    project = forms.ModelChoiceField(
        queryset=Project.objects.filter(is_archived=False).order_by('-created_at'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Project to Backup',
        help_text='Select the project you want to back up'
    )

    # Include related data
    include_milestones = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Include Milestones',
        initial=True
    )

    include_payments = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Include Payments',
        initial=True
    )

    include_expenses = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Include Expenses',
        initial=True
    )

    include_materials = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Include Materials',
        initial=True
    )

    include_gallery = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Include Gallery Images',
        initial=False,
        help_text='Warning: This may increase backup size significantly'
    )

    # Notes
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes about this backup...'
        }),
        label='Notes'
    )

    def clean(self):
        """Validate at least one related data type is selected."""
        cleaned_data = super().clean()

        # Ensure at least one related data type is selected
        related_fields = [
            'include_milestones',
            'include_payments',
            'include_expenses',
            'include_materials',
        ]

        has_related = any(cleaned_data.get(field, False) for field in related_fields)

        if not has_related:
            self.add_error(
                None,
                'Please select at least one related data type to include in the backup.'
            )

        return cleaned_data

    def get_includes(self):
        """Get dictionary of included data types."""
        return {
            'milestones': self.cleaned_data.get('include_milestones', False),
            'payments': self.cleaned_data.get('include_payments', False),
            'expenses': self.cleaned_data.get('include_expenses', False),
            'materials': self.cleaned_data.get('include_materials', False),
            'gallery': self.cleaned_data.get('include_gallery', False),
        }
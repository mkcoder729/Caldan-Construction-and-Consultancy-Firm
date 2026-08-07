"""
Export form for generating reports in various formats.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django import forms
from django.utils import timezone

from projects.models import Project


class ExportForm(forms.Form):
    """
    Form for exporting reports.
    Allows selection of report type, format, date range, and optional project.

    Choice keys match ExportService method-name suffixes so the same
    value drives both the form POST and the GET handler at
    ``reports:export?type=<key>&format=<format>``.
    """

    # ------------------------------------------------------------------
    # Choice catalogues — kept as class attrs so views + templates can
    # reference them without re-typing the list.
    # ------------------------------------------------------------------

    REPORT_TYPES = [
        ('projects',      'Projects'),
        ('project',       'Single Project Report'),
        ('clients',       'Clients'),
        ('orders',        'Orders'),
        ('payments',      'Payments'),
        ('expenses',      'Expenses'),
        ('inventory',     'Inventory'),
        ('team',          'Team'),
        ('blog',          'Blog Posts'),
        ('notifications', 'Notifications & Audit Log'),
        ('audit',         'Audit Log'),
    ]

    FORMAT_CHOICES = [
        ('csv',   'CSV'),
        ('excel', 'Excel (.xlsx)'),
        ('pdf',   'PDF'),
    ]

    # Icon + short description used by the template.  Avoids an if/elif
    # ladder in markup when a new report type is added.
    REPORT_META = {
        'projects':      {'icon': 'fa-diagram-project', 'desc': 'All projects with budget & progress'},
        'project':       {'icon': 'fa-file-alt',        'desc': 'One project — milestones, budget, timeline'},
        'clients':       {'icon': 'fa-users',           'desc': 'Client directory with contact details'},
        'orders':        {'icon': 'fa-shopping-bag',    'desc': 'Shop orders with status and revenue'},
        'payments':      {'icon': 'fa-money-bill',      'desc': 'All recorded payments'},
        'expenses':      {'icon': 'fa-receipt',         'desc': 'All recorded expenses'},
        'inventory':     {'icon': 'fa-boxes-stacked',   'desc': 'Materials, suppliers, transactions'},
        'team':          {'icon': 'fa-people-group',    'desc': 'Team members and roles'},
        'blog':          {'icon': 'fa-newspaper',       'desc': 'Articles — drafts and published'},
        'notifications': {'icon': 'fa-bell',            'desc': 'In-app notifications and audit log'},
        'audit':         {'icon': 'fa-history',         'desc': 'Full audit trail with cryptographic hash chain'},
    }

    # Report types that need a specific project picked.
    REQUIRES_PROJECT = {'project'}

    # Report types where "include archived" is meaningful.
    SUPPORTS_ARCHIVED = {'projects', 'project'}

    DEFAULT_REPORT_TYPE = 'projects'
    DEFAULT_FORMAT = 'csv'

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_report_type',
            'data-requires-project-group': 'projectFieldGroup',
            'data-supports-archived-group': 'includeArchivedGroup',
            'data-requires-project-value': 'project',
            'data-supports-archived-value': 'projects,project',
        }),
        label='Report Type',
        initial=DEFAULT_REPORT_TYPE,
    )

    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_format'}),
        label='Export Format',
        initial=DEFAULT_FORMAT,
    )

    project = forms.ModelChoiceField(
        queryset=Project.objects.filter(is_archived=False).order_by('-created_at'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_project'}),
        label='Specific Project',
        help_text='Required for "Single Project Report".',
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 'class': 'form-control', 'id': 'id_date_from'
        }),
        label='Date From',
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 'class': 'form-control', 'id': 'id_date_to'
        }),
        label='Date To',
    )

    include_archived = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input', 'id': 'id_include_archived'
        }),
        label='Include Archived Projects',
        initial=False,
    )

    # ------------------------------------------------------------------
    # Init — seed defaults so date inputs render with values on first GET.
    # ------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Default date range: last 30 days.  Pre-populating ``initial``
        # means the inputs show values even on a plain GET (no POST data).
        if not self.is_bound:
            today = timezone.now().date()
            self.fields['date_from'].initial = today - timezone.timedelta(days=30)
            self.fields['date_to'].initial = today

        # Make sure the queryset is fresh (avoids stale cached lists
        # when projects are created/archived mid-session).
        self.fields['project'].queryset = Project.objects.filter(
            is_archived=False
        ).order_by('-created_at')

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')

        if date_from and date_to and date_from > date_to:
            self.add_error('date_to', '“Date To” must be on or after “Date From”.')

        # Single-project report MUST have a project picked.
        if cleaned_data.get('report_type') == 'project' and not cleaned_data.get('project'):
            self.add_error(
                'project',
                'Pick a specific project for a Single Project Report.',
            )

        return cleaned_data

    # ------------------------------------------------------------------
    # Helpers used by the view layer
    # ------------------------------------------------------------------

    def get_filters(self):
        """Return a dict of the optional filter values (no defaults)."""
        return {
            'project':          self.cleaned_data.get('project'),
            'date_from':        self.cleaned_data.get('date_from'),
            'date_to':          self.cleaned_data.get('date_to'),
            'include_archived': self.cleaned_data.get('include_archived', False),
        }

    @staticmethod
    def get_label_for(value):
        """Look up the human label for a report_type value."""
        for v, label in ExportForm.REPORT_TYPES:
            if v == value:
                return label
        return value

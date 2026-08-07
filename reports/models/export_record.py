"""
ExportRecord model — persists every export that has been generated.
Caldan Construction - "Building Kenya's Future, One Project at a Time."

Why store these:
- Lets the admin see "what did I export last week?" in the History panel.
- Re-downloads re-render the file from the same filters instead of
  serving a stored blob (queries are fast enough at this scale).
"""

from django.conf import settings
from django.db import models


class ExportRecord(models.Model):
    """A record of one download generated through the Export Center."""

    class Format(models.TextChoices):
        CSV   = 'csv',   'CSV'
        EXCEL = 'excel', 'Excel'
        PDF   = 'pdf',   'PDF'
        ZIP   = 'zip',   'ZIP Bundle'

    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED  = 'failed',  'Failed'

    # What was exported
    report_type = models.CharField(
        max_length=40,
        db_index=True,
        help_text='Section key (matches ExportService method suffix)',
    )
    report_label = models.CharField(
        max_length=120,
        help_text='Human-readable label for history display',
    )
    format = models.CharField(
        max_length=10,
        choices=Format.choices,
        db_index=True,
    )

    # Filters applied
    project = models.ForeignKey(
        'projects.Project',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='export_records',
    )
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    include_archived = models.BooleanField(default=False)

    # Outcome
    row_count = models.PositiveIntegerField(default=0)
    file_size = models.PositiveIntegerField(default=0, help_text='bytes')
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.SUCCESS,
        db_index=True,
    )
    error = models.TextField(blank=True, default='')

    # Audit
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='export_records',
    )

    class Meta:
        db_table = 'export_records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['report_type', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.report_label} ({self.format.upper()}) — {self.created_at:%Y-%m-%d %H:%M}"

    # --- Display helpers used directly in templates -------------------

    @property
    def is_success(self):
        return self.status == self.Status.SUCCESS

    @property
    def is_failed(self):
        return self.status == self.Status.FAILED

    @property
    def file_size_display(self):
        """Human-readable file size (e.g. '12.4 KB')."""
        n = self.file_size
        for unit in ('B', 'KB', 'MB', 'GB'):
            if n < 1024:
                return f"{n:.1f} {unit}" if unit != 'B' else f"{n} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    def to_query_dict(self):
        """Return the GET params needed to re-run this export."""
        params = {
            'type': self.report_type,
            'format': self.format,
        }
        if self.project_id:
            params['project'] = self.project_id
        if self.date_from:
            params['date_from'] = self.date_from.isoformat()
        if self.date_to:
            params['date_to'] = self.date_to.isoformat()
        if self.include_archived:
            params['include_archived'] = '1'
        return params

    def download_url(self):
        """Absolute URL to re-download this export. Ready to drop into
        an ``href`` — no nested ``{% for %}`` tag juggling required."""
        from urllib.parse import urlencode
        from django.urls import reverse
        base = reverse('reports:export')
        return f"{base}?{urlencode(self.to_query_dict())}"

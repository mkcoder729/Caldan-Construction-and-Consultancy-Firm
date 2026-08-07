from django.db import models
from django.utils import timezone


class Client(models.Model):
    """Client and lead tracking model."""

    class Type(models.TextChoices):
        INDIVIDUAL = 'INDIVIDUAL', 'Individual'
        COMPANY = 'COMPANY', 'Company'
        INSTITUTION = 'INSTITUTION', 'Institution'
        OTHER = 'OTHER', 'Other'

    class Status(models.TextChoices):
        LEAD = 'LEAD', 'Lead'
        ACTIVE = 'ACTIVE', 'Active Client'
        INACTIVE = 'INACTIVE', 'Inactive'
        CONVERTED = 'CONVERTED', 'Converted'

    # Identity
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.INDIVIDUAL)
    company_name = models.CharField(max_length=200, blank=True, default='')

    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    alternative_phone = models.CharField(max_length=15, blank=True, default='')

    # Address
    address = models.TextField(blank=True, default='')
    county = models.CharField(max_length=100, blank=True, default='')
    town = models.CharField(max_length=100, blank=True, default='')

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LEAD)

    # Source
    source = models.CharField(max_length=50, blank=True, default='')  # Website, Referral, Direct

    # Linked projects
    projects = models.ManyToManyField('projects.Project', related_name='clients', blank=True)

    # Linked orders
    orders = models.ManyToManyField('shop.Order', related_name='clients', blank=True)

    # Notes
    notes = models.TextField(blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_contact = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'clients'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def convert_to_active(self):
        """Convert lead to active client."""
        self.status = self.Status.ACTIVE
        self.save()

    def add_project(self, project):
        """Add project to client."""
        self.projects.add(project)
        self.last_contact = timezone.now()
        self.save()

    def add_order(self, order):
        """Add order to client."""
        self.orders.add(order)
        self.last_contact = timezone.now()
        self.save()
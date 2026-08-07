from django.db import models
from django.conf import settings


class Expense(models.Model):
    """Expense record model."""

    class Category(models.TextChoices):
        LABOUR = 'LABOUR', 'Labour'
        MATERIALS = 'MATERIALS', 'Materials'
        EQUIPMENT = 'EQUIPMENT', 'Equipment'
        TRANSPORT = 'TRANSPORT', 'Transport'
        UTILITIES = 'UTILITIES', 'Utilities'
        OFFICE = 'OFFICE', 'Office'
        OTHER = 'OTHER', 'Other'

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='expenses'
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField()
    expense_date = models.DateField()

    receipt = models.ImageField(upload_to='expenses/receipts/', blank=True, null=True)
    receipt_number = models.CharField(max_length=50, blank=True, default='')

    vendor_name = models.CharField(max_length=200, blank=True, default='')
    vendor_contact = models.CharField(max_length=100, blank=True, default='')

    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_expenses'
    )

    class Meta:
        db_table = 'expenses'
        ordering = ['-expense_date']
        indexes = [
            models.Index(fields=['project', '-expense_date']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - KES {self.amount} ({self.expense_date})"
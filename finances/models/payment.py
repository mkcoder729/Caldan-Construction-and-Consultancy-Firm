from django.db import models
from django.conf import settings
from django.utils import timezone


class Payment(models.Model):
    """Payment record model."""

    class Type(models.TextChoices):
        MATERIAL = 'MATERIAL', 'Material'
        SALARY = 'SALARY', 'Salary'
        EQUIPMENT = 'EQUIPMENT', 'Equipment'
        SUBCONTRACTOR = 'SUBCONTRACTOR', 'Subcontractor'
        OTHER = 'OTHER', 'Other'

    class Method(models.TextChoices):
        CASH = 'CASH', 'Cash'
        MPESA = 'MPESA', 'M-Pesa'
        BANK = 'BANK', 'Bank Transfer'
        CHEQUE = 'CHEQUE', 'Cheque'
        PAYSTACK = 'PAYSTACK', 'Paystack'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='payments'
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=20, choices=Type.choices)
    method = models.CharField(max_length=20, choices=Method.choices)
    description = models.TextField()

    paid_to = models.CharField(max_length=200)
    paid_to_contact = models.CharField(max_length=100, blank=True, default='')

    reference = models.CharField(max_length=100, blank=True, default='')
    receipt = models.ImageField(upload_to='payments/receipts/', blank=True, null=True)
    invoice_number = models.CharField(max_length=50, blank=True, default='')

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    payment_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['project', '-payment_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Payment #{self.id} - {self.get_type_display()} - KES {self.amount}"
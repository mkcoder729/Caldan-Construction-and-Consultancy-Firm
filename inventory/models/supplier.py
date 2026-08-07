"""
Supplier Model - Manages material vendors.

Tracks all supplier information including contact details,
payment terms, and relationship to materials.
"""

from django.db import models
from django.core.validators import MinValueValidator


class Supplier(models.Model):
    """Supplier/vendor for materials."""

    class PaymentTerms(models.TextChoices):
        CASH = 'CASH', 'Cash on Delivery'
        CREDIT_30 = 'CREDIT_30', '30 Days Credit'
        CREDIT_60 = 'CREDIT_60', '60 Days Credit'
        CREDIT_90 = 'CREDIT_90', '90 Days Credit'
        NEGOTIABLE = 'NEGOTIABLE', 'Negotiable'

    # =====================================================================
    # IDENTITY FIELDS
    # =====================================================================
    name = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Supplier company name"
    )
    contact_person = models.CharField(
        max_length=150,
        help_text="Primary contact person"
    )

    # =====================================================================
    # CONTACT DETAILS
    # =====================================================================
    phone = models.CharField(
        max_length=15,
        help_text="Primary phone number"
    )
    alternative_phone = models.CharField(
        max_length=15,
        blank=True,
        default='',
        help_text="Alternative phone number"
    )
    email = models.EmailField(
        help_text="Supplier email address"
    )

    # =====================================================================
    # ADDRESS
    # =====================================================================
    address = models.TextField(
        help_text="Physical address"
    )
    county = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="County in Kenya"
    )
    town = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Town/City"
    )

    # =====================================================================
    # BUSINESS DETAILS
    # =====================================================================
    payment_terms = models.CharField(
        max_length=20,
        choices=PaymentTerms.choices,
        default=PaymentTerms.NEGOTIABLE,
        help_text="Payment terms with this supplier"
    )
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Tax/PIN number"
    )
    business_registration = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Business registration number"
    )

    # =====================================================================
    # NOTES
    # =====================================================================
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Additional notes about this supplier"
    )

    # =====================================================================
    # STATUS
    # =====================================================================
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Is this supplier still active?"
    )
    is_preferred = models.BooleanField(
        default=False,
        help_text="Is this a preferred supplier?"
    )

    # =====================================================================
    # TIMESTAMPS
    # =====================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_suppliers',
        help_text="Admin who created this supplier"
    )

    class Meta:
        db_table = 'suppliers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='supplier_name_idx'),
            models.Index(fields=['is_active'], name='supplier_active_idx'),
            models.Index(fields=['-created_at'], name='supplier_created_idx'),
        ]

    def __str__(self):
        return self.name

    def get_full_contact(self) -> str:
        """Get full contact details as a string."""
        return f"{self.contact_person} - {self.phone} ({self.email})"

    @property
    def material_count(self) -> int:
        """Count of materials supplied by this supplier."""
        return self.materials.filter(is_active=True).count()
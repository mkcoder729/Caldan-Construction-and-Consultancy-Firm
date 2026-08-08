"""
InKindDonation model — pledges of food, clothing, medical supplies,
or anything physical. Admin moves them through a workflow:
PLEDGED → SCHEDULED → RECEIVED → DELIVERED.
"""

from django.db import models
from django.utils import timezone


class InKindDonation(models.Model):
    """An in-kind pledge (food / clothing / medical / other)."""

    class ItemType(models.TextChoices):
        FOOD = "FOOD", "Food"
        CLOTHING = "CLOTHING", "Clothing"
        MEDICAL = "MEDICAL", "Medical supplies"
        OTHER = "OTHER", "Other (describe)"

    class DeliveryMode(models.TextChoices):
        PICKUP = "PICKUP", "You pick up from me"
        DROPOFF = "DROPOFF", "I will drop off"
        ARRANGE = "ARRANGE", "Let's arrange together"

    class Status(models.TextChoices):
        PLEDGED = "PLEDGED", "Pledged"
        SCHEDULED = "SCHEDULED", "Pickup/dropoff scheduled"
        RECEIVED = "RECEIVED", "Received"
        DELIVERED = "DELIVERED", "Delivered to outreach"
        CANCELLED = "CANCELLED", "Cancelled"

    # ───── Donor info ─────
    donor_name = models.CharField(max_length=150, verbose_name="Full name")
    donor_email = models.EmailField(verbose_name="Email address")
    donor_phone = models.CharField(max_length=15, verbose_name="Phone number")

    # ───── Item details ─────
    item_type = models.CharField(
        max_length=12,
        choices=ItemType.choices,
        default=ItemType.FOOD,
        db_index=True,
        verbose_name="Item type",
    )
    item_description = models.TextField(verbose_name="Item description")
    quantity_estimate = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Quantity estimate",
        help_text="e.g. '20kg maize', '2 boxes', '50 pieces'",
    )

    # ───── Logistics ─────
    delivery_mode = models.CharField(
        max_length=10,
        choices=DeliveryMode.choices,
        default=DeliveryMode.ARRANGE,
        verbose_name="Delivery / pickup",
    )
    preferred_date = models.DateField(null=True, blank=True, verbose_name="Preferred date")
    address = models.TextField(blank=True, default="", verbose_name="Address (for pickup)")
    notes = models.TextField(blank=True, default="", verbose_name="Notes")

    # ───── Workflow ─────
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PLEDGED,
        db_index=True,
        verbose_name="Status",
    )
    status_changed_at = models.DateTimeField(null=True, blank=True)

    # ───── Audit metadata ─────
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compassion_inkind_donations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["item_type", "-created_at"]),
            models.Index(fields=["donor_email", "-created_at"]),
        ]
        verbose_name = "In-Kind Donation"
        verbose_name_plural = "In-Kind Donations"

    def __str__(self) -> str:
        return f"{self.donor_name} — {self.get_item_type_display()} — {self.get_status_display()}"

    # ───── Workflow helper ─────
    def advance_to(self, new_status: str) -> None:
        """Move the pledge to a new workflow state. Idempotent."""
        if new_status not in self.Status.values:
            raise ValueError(f"Invalid status: {new_status}")
        if self.status == new_status:
            return
        self.status = new_status
        self.status_changed_at = timezone.now()
        self.save(update_fields=["status", "status_changed_at", "updated_at"])

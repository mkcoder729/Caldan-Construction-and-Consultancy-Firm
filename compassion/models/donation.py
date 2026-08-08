"""
Donation model — monetary donations backed by Paystack.

Mirrors the canonical pattern from website/models/contact.py and
website/models/quote.py (status flag + timestamps + indexes + helper
method). Reference format is auto-generated on save so the row
always carries a human-recognisable, unique identifier.

The model is intentionally isolated from shop.Order — donations are
not orders (no shipping, no fulfilment), and we want admin/audit
chains that are easy to query for 'compassion' alone.
"""

from decimal import Decimal

from django.db import models
from django.utils import timezone


class Donation(models.Model):
    """A monetary donation to Caldan Compassionate Ministry."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Successful"
        FAILED = "FAILED", "Failed"
        ABANDONED = "ABANDONED", "Abandoned"

    class Purpose(models.TextChoices):
        GENERAL = "GENERAL", "Where most needed"
        HOSPITAL = "HOSPITAL", "Hospital outreach"
        PRISON = "PRISON", "Prison ministry"
        NEIGHBOURHOOD = "NEIGHBOURHOOD", "Neighbourhood outreach"

    # ───── Identity ─────
    reference = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Donation reference",
        help_text="Auto-generated unique reference, e.g. DON-12-20260808143022",
    )
    paystack_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Paystack reference",
        help_text="Reference returned by Paystack on charge.success",
    )

    # ───── Donor info ─────
    donor_name = models.CharField(max_length=150, verbose_name="Full name")
    donor_email = models.EmailField(verbose_name="Email address")
    donor_phone = models.CharField(max_length=15, verbose_name="Phone number")

    # ───── Money ─────
    amount_ksh = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_index=True,
        verbose_name="Amount (KES)",
        help_text="Donation amount in Kenyan Shillings",
    )

    # ───── Routing / intent ─────
    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.GENERAL,
        db_index=True,
        verbose_name="Donation purpose",
    )
    note = models.TextField(blank=True, default="", verbose_name="Note")

    # ───── Paystack state ─────
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name="Status",
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Verified at",
    )

    # ───── Audit-trail metadata ─────
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default="")

    # ───── Timestamps ─────
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compassion_donations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["purpose", "-created_at"]),
            models.Index(fields=["donor_email", "-created_at"]),
        ]
        verbose_name = "Donation"
        verbose_name_plural = "Donations"

    def __str__(self) -> str:
        return f"{self.reference} — KES {self.amount_ksh} — {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Auto-generate a stable, human-readable reference if missing. We
        # only assign on first save (when pk is None) so re-saves never
        # mutate an existing reference (which would break Paystack lookups).
        if not self.reference:
            ts = timezone.now().strftime("%Y%m%d%H%M%S")
            # We can't use self.id yet (it doesn't exist before insert),
            # so use the timestamp + a 4-char random suffix to guarantee
            # uniqueness. After insert, callers should NOT rely on the
            # timestamp being identical to the pk — it's a stable opaque
            # token, not a sequence number.
            import secrets
            suffix = secrets.token_hex(2).upper()
            self.reference = f"DON-{ts}-{suffix}"
        super().save(*args, **kwargs)

    # ───── State transitions ─────
    def mark_paid(self, paystack_reference: str) -> None:
        """Flip to SUCCESS and record the Paystack reference. Idempotent."""
        if self.status == self.Status.SUCCESS:
            return
        self.status = self.Status.SUCCESS
        self.paystack_reference = paystack_reference
        self.verified_at = timezone.now()
        self.save(update_fields=["status", "paystack_reference", "verified_at", "updated_at"])

    def mark_failed(self) -> None:
        if self.status == self.Status.FAILED:
            return
        self.status = self.Status.FAILED
        self.save(update_fields=["status", "updated_at"])

    @property
    def amount_in_kobo(self) -> int:
        """Paystack expects integer kobo (1 KES = 100 kobo)."""
        return int((self.amount_ksh or Decimal("0")) * 100)

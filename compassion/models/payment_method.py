"""
PaymentMethod — admin-managed, fully dynamic list of how to give.

No hardcoded paybill/bank numbers anywhere in code. The chief admin
adds PaymentMethod rows via /admin/ and they appear on the public
page (rendered only when is_active=True, ordered by display_order).

Supports the methods a Kenyan donor would actually use:
PAYBILL, BUY_GOODS, TILL, POCHI, SEND_MONEY, BANK, CARD.
"""

from django.db import models
from django.utils import timezone


class PaymentMethod(models.Model):
    """A way to give — admin-managed. Multiple rows allowed."""

    class Method(models.TextChoices):
        PAYBILL = "PAYBILL", "M-Pesa Paybill"
        BUY_GOODS = "BUY_GOODS", "Buy Goods & Services (Till)"
        TILL = "TILL", "Till Number"
        POCHI = "POCHI", "Pochi la Biashara"
        SEND_MONEY = "SEND_MONEY", "Send Money (phone number)"
        BANK = "BANK", "Bank transfer"
        CARD = "CARD", "Card payment"

    # ───── Identity ─────
    method = models.CharField(
        max_length=14,
        choices=Method.choices,
        db_index=True,
        verbose_name="Method type",
    )
    label = models.CharField(
        max_length=120,
        verbose_name="Label",
        help_text="What donors see, e.g. 'M-Pesa Paybill — Donations'",
    )

    # ───── Account info ─────
    account_number = models.CharField(max_length=80, verbose_name="Account / phone / card number")
    account_name = models.CharField(max_length=200, verbose_name="Account name")
    bank_name = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Bank name",
        help_text="Only required for bank transfers.",
    )
    instructions = models.TextField(
        blank=True,
        default="",
        verbose_name="Instructions",
        help_text="Free-text step-by-step, e.g. 'Paybill → Account: CALDAN'.",
    )

    # ───── Display ─────
    display_order = models.PositiveIntegerField(default=0, db_index=True, verbose_name="Display order")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Active")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compassion_payment_methods"
        ordering = ["display_order", "method", "label"]
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"

    def __str__(self) -> str:
        return f"{self.label} — {self.account_number}"

    # ───── Icon helper for templates ─────
    @property
    def icon_class(self) -> str:
        """FontAwesome class per method, for the template."""
        return {
            self.Method.PAYBILL: "fa-mobile-screen",
            self.Method.BUY_GOODS: "fa-store",
            self.Method.TILL: "fa-cash-register",
            self.Method.POCHI: "fa-wallet",
            self.Method.SEND_MONEY: "fa-paper-plane",
            self.Method.BANK: "fa-building-columns",
            self.Method.CARD: "fa-credit-card",
        }.get(self.method, "fa-circle")

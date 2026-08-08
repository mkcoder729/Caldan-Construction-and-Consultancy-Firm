"""
MinistrySettings — singleton holding the public hero copy and
ministry-level contact information. Exactly one row exists; the
`get_solo()` classmethod on `MinistryService` guarantees this.
"""

from django.db import models
from django.utils import timezone


class MinistrySettings(models.Model):
    """Singleton row carrying hero copy, mission, and contact details."""

    # ───── Hero ─────
    hero_title = models.CharField(
        max_length=200,
        default="Caldan Compassionate Ministry",
        verbose_name="Hero title",
    )
    hero_subtitle = models.CharField(
        max_length=300,
        default="Reaching hospitals, prisons, and neighbourhoods with practical love.",
        verbose_name="Hero subtitle",
    )
    hero_cta_label = models.CharField(
        max_length=40,
        default="Donate Now",
        verbose_name="Primary CTA label",
    )
    mission_statement = models.TextField(
        blank=True,
        default=(
            "We step into places others avoid — hospital wards, prison cells, "
            "neglected neighbourhoods — with food, clothing, prayer, and a "
            "listening ear. Every gift, big or small, fuels that work."
        ),
        verbose_name="Mission statement",
    )

    # ───── Contact ─────
    contact_phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Contact phone",
    )
    contact_email = models.EmailField(blank=True, default="", verbose_name="Contact email")

    # ───── Misc ─────
    default_currency = models.CharField(max_length=8, default="KES", verbose_name="Default currency")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compassion_ministry_settings"
        verbose_name = "Ministry Settings"
        verbose_name_plural = "Ministry Settings"

    def __str__(self) -> str:
        return f"Ministry Settings (updated {self.updated_at:%Y-%m-%d %H:%M})"

    @classmethod
    def get_solo(cls):
        """Return the singleton row, creating it if necessary.

        We don't use `get_or_create` directly because the default values
        live on field defaults and Django will only persist them on
        create; this method also tolerates a brand-new database where
        the table is empty.
        """
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj

    def save(self, *args, **kwargs):
        # Defensive: enforce singleton. If a row already exists and we're
        # inserting a new one, re-use the existing PK instead.
        if not self.pk:
            existing = self.__class__.objects.first()
            if existing:
                self.pk = existing.pk
        super().save(*args, **kwargs)

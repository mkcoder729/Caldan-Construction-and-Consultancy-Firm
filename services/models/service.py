"""
Service model for construction services catalog.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.db import models
from django.utils.text import slugify


class Service(models.Model):
    """
    Construction services offered by Caldan.
    """

    class Category(models.TextChoices):
        DESIGN = 'DESIGN', 'Design & Construction'
        RENOVATION = 'RENOVATION', 'Renovations'
        INTERIOR = 'INTERIOR', 'Interior Design'
        WELDING = 'WELDING', 'Welding & Fabrication'
        CONCRETE = 'CONCRETE', 'Concrete Products'
        INDUSTRIAL = 'INDUSTRIAL', 'Industrial Floor Solutions'
        WATERPROOFING = 'WATERPROOFING', 'Waterproofing Works'
        INFRASTRUCTURE = 'INFRASTRUCTURE', 'Roads & Stormwater Infrastructure'
        CHEMICALS = 'CHEMICALS', 'Construction Chemicals'

    name = models.CharField(max_length=200, db_index=True)
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    slug = models.SlugField(unique=True, max_length=200)
    description = models.TextField()
    long_description = models.TextField(blank=True, default='')
    icon = models.CharField(
        max_length=50,
        default='fas fa-tools',
        help_text="Full FA6 class, e.g. 'fas fa-tools' (style + icon, both required)",
    )
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'services'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
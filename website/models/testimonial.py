from django.db import models


class Testimonial(models.Model):
    """Client testimonial model."""

    author_name = models.CharField(max_length=100)
    author_title = models.CharField(max_length=100, blank=True, default="")
    content = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    author_photo = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'testimonials'
        ordering = ['display_order', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'display_order']),
        ]

    def __str__(self):
        return f"{self.author_name} - {self.rating}★"
from django.db import models
from django.db.models import Sum


class Budget(models.Model):
    """Project budget model."""

    class Category(models.TextChoices):
        MATERIALS = 'MATERIALS', 'Materials'
        LABOUR = 'LABOUR', 'Labour'
        EQUIPMENT = 'EQUIPMENT', 'Equipment'
        SUBCONTRACTOR = 'SUBCONTRACTOR', 'Subcontractor'
        TRANSPORT = 'TRANSPORT', 'Transport'
        CONTINGENCY = 'CONTINGENCY', 'Contingency'
        OTHER = 'OTHER', 'Other'

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='budgets'
    )

    category = models.CharField(max_length=20, choices=Category.choices)
    allocated = models.DecimalField(max_digits=15, decimal_places=2)
    spent = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    committed = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    description = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budgets'
        unique_together = ['project', 'category']

    def __str__(self):
        return f"{self.project.name} - {self.get_category_display()}: KES {self.allocated}"

    @property
    def remaining(self):
        return self.allocated - self.spent - self.committed

    @property
    def spent_percentage(self):
        if self.allocated == 0:
            return 0
        return round((self.spent / self.allocated) * 100, 2)

    @property
    def is_over_budget(self):
        return self.spent > self.allocated

    def update_spent(self):
        """Update spent amount from expenses."""
        from finances.models.expense import Expense
        total = Expense.objects.filter(
            project=self.project,
            category=self.category
        ).aggregate(total=Sum('amount'))['total'] or 0
        self.spent = total
        self.save()
# Projects Signals - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum

from projects.models import Project
from finances.models import Budget, Expense, Payment

logger = logging.getLogger(__name__)


# =====================================================================
# PROJECT BUDGET AUTO-UPDATE SIGNALS
# =====================================================================

@receiver(post_save, sender=Budget)
def update_project_budget_from_budget(sender, instance, created, **kwargs):
    """
    Update Project.budget when Budget entries are created/updated.
    Project.budget = sum of all allocated amounts for that project.
    """
    try:
        project = instance.project
        total_budget = Budget.objects.filter(project=project).aggregate(
            total=Sum('allocated')
        )['total'] or 0

        project.budget = total_budget
        project.save(update_fields=['budget'])

        logger.debug(
            f"Project budget updated: {project.project_code} = KES {total_budget}"
        )
    except Exception as e:
        logger.error(f"Failed to update project budget: {str(e)}")


@receiver(post_delete, sender=Budget)
def update_project_budget_on_budget_delete(sender, instance, **kwargs):
    """
    Update Project.budget when Budget entries are deleted.
    """
    try:
        project = instance.project
        total_budget = Budget.objects.filter(project=project).aggregate(
            total=Sum('allocated')
        )['total'] or 0

        project.budget = total_budget
        project.save(update_fields=['budget'])

        logger.debug(
            f"Project budget updated after delete: {project.project_code} = KES {total_budget}"
        )
    except Exception as e:
        logger.error(f"Failed to update project budget on delete: {str(e)}")


# =====================================================================
# PROJECT SPENT AUTO-UPDATE SIGNALS
# =====================================================================

@receiver(post_save, sender=Expense)
def update_project_spent_from_expense(sender, instance, created, **kwargs):
    """
    Update Project.spent when Expense entries are created/updated.
    Project.spent = sum of all expenses for that project.
    """
    try:
        project = instance.project
        total_spent = Expense.objects.filter(project=project).aggregate(
            total=Sum('amount')
        )['total'] or 0

        project.spent = total_spent
        project.save(update_fields=['spent'])

        logger.debug(
            f"Project spent updated: {project.project_code} = KES {total_spent}"
        )
    except Exception as e:
        logger.error(f"Failed to update project spent: {str(e)}")


@receiver(post_delete, sender=Expense)
def update_project_spent_on_expense_delete(sender, instance, **kwargs):
    """
    Update Project.spent when Expense entries are deleted.
    """
    try:
        project = instance.project
        total_spent = Expense.objects.filter(project=project).aggregate(
            total=Sum('amount')
        )['total'] or 0

        project.spent = total_spent
        project.save(update_fields=['spent'])

        logger.debug(
            f"Project spent updated after delete: {project.project_code} = KES {total_spent}"
        )
    except Exception as e:
        logger.error(f"Failed to update project spent on delete: {str(e)}")


# =====================================================================
# PROJECT SPENT FROM PAYMENTS (Optional - if payments are considered spent)
# =====================================================================

@receiver(post_save, sender=Payment)
def update_project_spent_from_payment(sender, instance, created, **kwargs):
    """
    Optionally update Project.spent from completed payments.
    This is alternative to using Expenses for spent tracking.
    """
    try:
        # Only count completed payments
        if instance.status != 'COMPLETED':
            return

        project = instance.project
        # Sum of completed payments for this project
        total_payments = Payment.objects.filter(
            project=project,
            status='COMPLETED'
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0

        # Alternatively, use expenses (more common for construction)
        # If you want to use payments instead of expenses, uncomment:
        # project.spent = total_payments
        # project.save(update_fields=['spent'])

        logger.debug(
            f"Project payments total: {project.project_code} = KES {total_payments}"
        )
    except Exception as e:
        logger.error(f"Failed to update project from payment: {str(e)}")
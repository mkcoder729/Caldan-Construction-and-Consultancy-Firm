"""
Deletion Service - Safe deletion with audit logging.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from accounts.services.audit_service import AuditService
from projects.models import Project

logger = logging.getLogger('caldan.reports')


class DeletionService:
    """
    Service for safe project deletion with audit logging.
    Supports soft delete (archive) and hard delete (permanent).
    """

    @classmethod
    def soft_delete_project(cls, project_id, user, reason=None):
        """
        Soft delete a project (archive it).
        Can be restored later.
        """
        project = Project.objects.get(id=project_id)

        if project.status == 'ARCHIVED':
            raise ValueError("Project is already archived")

        # Store project info for audit
        project_name = project.name
        project_code = project.project_code

        # Archive the project
        project.status = Project.Status.ARCHIVED
        project.is_archived = True
        project.archived_at = timezone.now()
        project.save(update_fields=['status', 'is_archived', 'archived_at'])

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECT_ARCHIVED',
            entity_type='Project',
            entity_id=str(project.id),
            details={
                'project_name': project_name,
                'project_code': project_code,
                'reason': reason or 'No reason provided',
                'archived_at': timezone.now().isoformat(),
            }
        )

        logger.info(f"Project {project_code} archived by {user.email}")
        return project

    @classmethod
    def restore_project(cls, project_id, user):
        """
        Restore a soft-deleted project.
        """
        project = Project.objects.get(id=project_id, is_archived=True)

        # Store project info for audit
        project_name = project.name
        project_code = project.project_code

        # Restore the project
        project.status = Project.Status.ACTIVE
        project.is_archived = False
        project.archived_at = None
        project.save(update_fields=['status', 'is_archived', 'archived_at'])

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECT_RESTORED',
            entity_type='Project',
            entity_id=str(project.id),
            details={
                'project_name': project_name,
                'project_code': project_code,
                'restored_at': timezone.now().isoformat(),
            }
        )

        logger.info(f"Project {project_code} restored by {user.email}")
        return project

    @classmethod
    @transaction.atomic
    def hard_delete_project(cls, project_id, user, confirm_backup=True):
        """
        Permanently delete a project (IRREVERSIBLE).
        Requires backup confirmation for safety.
        """
        project = Project.objects.get(id=project_id)

        # Check if backup exists (safety)
        if confirm_backup:
            import os
            from django.conf import settings
            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups', project.project_code)
            backup_file = os.path.join(backup_dir, f"{project.project_code}.data.json")

            if not os.path.exists(backup_file):
                raise ValueError(
                    "Please create a backup before permanent deletion. "
                    f"Run: python manage.py backup_project {project.id}"
                )

        # Store project info for audit
        project_name = project.name
        project_code = project.project_code
        project_id_str = str(project.id)

        # Count related records for audit
        milestone_count = project.milestones.count()
        payment_count = project.payments.count()
        expense_count = project.expenses.count()
        material_count = project.materials.count()

        # Delete all related data
        project.milestones.all().delete()
        project.payments.all().delete()
        project.expenses.all().delete()
        project.materials.all().delete()
        project.budgets.all().delete()

        # Delete the project itself
        project.delete()

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECT_HARD_DELETED',
            entity_type='Project',
            entity_id=project_id_str,
            details={
                'project_name': project_name,
                'project_code': project_code,
                'related_records': {
                    'milestones': milestone_count,
                    'payments': payment_count,
                    'expenses': expense_count,
                    'materials': material_count,
                },
                'deleted_at': timezone.now().isoformat(),
            }
        )

        logger.warning(f"Project {project_code} PERMANENTLY DELETED by {user.email}")
        return True

    @classmethod
    @transaction.atomic
    def hard_delete_projects_bulk(cls, project_ids, user):
        """
        Permanently delete multiple projects (IRREVERSIBLE).
        """
        deleted_count = 0
        project_codes = []

        for project_id in project_ids:
            try:
                project = Project.objects.get(id=project_id)
                project_codes.append(project.project_code)

                # Delete related data
                project.milestones.all().delete()
                project.payments.all().delete()
                project.expenses.all().delete()
                project.materials.all().delete()
                project.budgets.all().delete()

                project.delete()
                deleted_count += 1

            except Project.DoesNotExist:
                logger.warning(f"Project {project_id} not found for bulk deletion")

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECTS_BULK_DELETED',
            entity_type='Project',
            details={
                'count': deleted_count,
                'project_codes': project_codes,
                'deleted_at': timezone.now().isoformat(),
            }
        )

        logger.warning(f"Bulk deleted {deleted_count} projects by {user.email}")
        return deleted_count

    @classmethod
    def get_deleted_projects(cls):
        """
        Get all soft-deleted (archived) projects.
        """
        return Project.objects.filter(is_archived=True)

    @classmethod
    def purge_old_projects(cls, days=90, user=None):
        """
        Permanently delete projects that have been archived for more than X days.
        """
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        old_projects = Project.objects.filter(
            is_archived=True,
            archived_at__lte=cutoff_date
        )

        deleted_count = 0
        for project in old_projects:
            try:
                # Hard delete without backup check (they're old)
                cls.hard_delete_project(project.id, user, confirm_backup=False)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to purge project {project.id}: {str(e)}")

        if deleted_count > 0 and user:
            AuditService.log_action(
                user=user,
                action='PROJECTS_PURGED',
                entity_type='Project',
                details={
                    'count': deleted_count,
                    'days_old': days,
                    'purged_at': timezone.now().isoformat(),
                }
            )

        logger.info(f"Purged {deleted_count} old projects")
        return deleted_count
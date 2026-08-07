# Project Service - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

import logging
from decimal import Decimal
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404

from projects.models.project import Project
from projects.models.milestone import Milestone
from accounts.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for all project-related business logic."""

    # =====================================================================
    # CREATE OPERATIONS
    # =====================================================================

    @classmethod
    @transaction.atomic
    def create_project(cls, data, user):
        """
        Create a new project with audit logging.

        Args:
            data: dict with project fields
            user: User creating the project

        Returns:
            Project instance
        """
        # Remove any project_code if provided (we auto-generate)
        data.pop('project_code', None)

        # Create project
        project = Project.objects.create(
            **data,
            created_by=user
        )

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECT_CREATED',
            entity_type='Project',
            entity_id=project.id,
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'budget': float(project.budget),
                'status': project.status,
            }
        )

        logger.info(f"Project created: {project.project_code} by {user.email}")
        return project

    # =====================================================================
    # READ OPERATIONS
    # =====================================================================

    @classmethod
    def get_project(cls, project_id, user=None):
        """
        Get a single project with related data.

        Args:
            project_id: Project ID
            user: User requesting (for permission checks)

        Returns:
            Project instance with prefetched relations
        """
        project = get_object_or_404(
            Project.objects.select_related('created_by')
            .prefetch_related('milestones', 'gallery_images', 'service_links'),
            id=project_id
        )
        return project

    @classmethod
    def get_project_summary(cls, project_id, user=None):
        """
        Get comprehensive project summary with all related data.

        Args:
            project_id: Project ID
            user: User requesting

        Returns:
            dict with project, milestones, financials, stats
        """
        project = cls.get_project(project_id, user)

        # Get milestone stats
        milestones = project.milestones.all()
        total_milestones = milestones.count()
        completed_milestones = milestones.filter(status='COMPLETED').count()
        overdue_milestones = milestones.filter(status='OVERDUE').count()
        in_progress_milestones = milestones.filter(status='IN_PROGRESS').count()

        # Get financial summary (from finances app via service)
        from finances.services.financial_service import FinancialService
        financial_summary = FinancialService.get_project_financial_summary(project.id)

        return {
            'project': project,
            'milestones': milestones,
            'stats': {
                'total_milestones': total_milestones,
                'completed_milestones': completed_milestones,
                'overdue_milestones': overdue_milestones,
                'in_progress_milestones': in_progress_milestones,
                'completion_rate': round(
                    (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0,
                    1
                ),
            },
            'financial': financial_summary,
            'gallery': project.gallery_images.all(),
            'services': project.services.all(),
        }

    @classmethod
    def get_all_projects(cls, filters=None, page=1, per_page=20, user=None):
        """
        Get all projects with filtering and pagination.

        Args:
            filters: dict with status, search, county, is_archived
            page: Page number
            per_page: Items per page
            user: User requesting

        Returns:
            dict with projects, pagination info, status counts
        """
        queryset = Project.objects.select_related('created_by')

        # Apply filters
        if filters:
            status = filters.get('status')
            if status:
                queryset = queryset.filter(status=status)

            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(project_code__icontains=search) |
                    Q(location__icontains=search) |
                    Q(county__icontains=search) |
                    Q(town__icontains=search)
                )

            county = filters.get('county')
            if county:
                queryset = queryset.filter(county__iexact=county)

            is_archived = filters.get('is_archived')
            if is_archived is not None:
                queryset = queryset.filter(is_archived=is_archived)
            else:
                # Default: exclude archived unless specifically requested
                queryset = queryset.filter(is_archived=False)

        # Order by created_at descending
        queryset = queryset.order_by('-created_at')

        # Get status counts
        status_counts = {
            'total': Project.objects.filter(is_archived=False).count(),
            'planning': Project.objects.filter(status='PLANNING', is_archived=False).count(),
            'active': Project.objects.filter(status='ACTIVE', is_archived=False).count(),
            'on_hold': Project.objects.filter(status='ON_HOLD', is_archived=False).count(),
            'completed': Project.objects.filter(status='COMPLETED', is_archived=False).count(),
            'archived': Project.objects.filter(is_archived=True).count(),
        }

        # Paginate
        paginator = Paginator(queryset, per_page)
        projects = paginator.get_page(page)

        return {
            'projects': projects,
            'paginator': paginator,
            'status_counts': status_counts,
            'total_count': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages,
        }

    @classmethod
    def get_counties(cls):
        """Get list of all counties with projects."""
        return list(
            Project.objects.filter(is_archived=False)
            .values_list('county', flat=True)
            .distinct()
            .order_by('county')
        )

    # =====================================================================
    # UPDATE OPERATIONS
    # =====================================================================

    @classmethod
    @transaction.atomic
    def update_project(cls, project_id, data, user):
        """
        Update an existing project with audit logging.

        Args:
            project_id: Project ID
            data: dict with fields to update
            user: User performing update

        Returns:
            Updated Project instance
        """
        project = get_object_or_404(Project, id=project_id)

        # Track changes for audit
        old_values = {
            'name': project.name,
            'status': project.status,
            'budget': float(project.budget),
        }

        # Update fields
        for key, value in data.items():
            if hasattr(project, key):
                setattr(project, key, value)

        project.save()

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECT_UPDATED',
            entity_type='Project',
            entity_id=project.id,
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'old_values': old_values,
                'updated_fields': list(data.keys()),
            }
        )

        logger.info(f"Project updated: {project.project_code} by {user.email}")
        return project

    @classmethod
    @transaction.atomic
    def update_progress(cls, project_id, progress, notes, user):
        """
        Manually update project progress.

        Args:
            project_id: Project ID
            progress: New progress percentage (0-100)
            notes: Update notes
            user: User performing update

        Returns:
            Updated Project instance
        """
        project = get_object_or_404(Project, id=project_id)
        old_progress = project.progress

        progress = min(max(float(progress), 0), 100)
        project.progress = progress
        project.save(update_fields=['progress'])

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECT_PROGRESS_UPDATED',
            entity_type='Project',
            entity_id=project.id,
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'old_progress': float(old_progress),
                'new_progress': float(progress),
                'notes': notes,
            }
        )

        logger.info(
            f"Project progress updated: {project.project_code} "
            f"{old_progress}% -> {progress}% by {user.email}"
        )
        return project

    @classmethod
    @transaction.atomic
    def archive_project(cls, project_id, user):
        """
        Soft delete - archive a project.

        Args:
            project_id: Project ID
            user: User performing archive

        Returns:
            Archived Project instance
        """
        project = get_object_or_404(Project, id=project_id)

        if project.is_archived:
            raise ValueError("Project is already archived.")

        project.archive(user)

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECT_ARCHIVED',
            entity_type='Project',
            entity_id=project.id,
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'archived_at': project.archived_at.isoformat() if project.archived_at else None,
            }
        )

        logger.info(f"Project archived: {project.project_code} by {user.email}")
        return project

    @classmethod
    @transaction.atomic
    def restore_project(cls, project_id, user):
        """
        Restore an archived project.

        Args:
            project_id: Project ID
            user: User performing restore

        Returns:
            Restored Project instance
        """
        project = get_object_or_404(Project, id=project_id, is_archived=True)

        project.restore()

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECT_RESTORED',
            entity_type='Project',
            entity_id=project.id,
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'restored_at': timezone.now().isoformat(),
            }
        )

        logger.info(f"Project restored: {project.project_code} by {user.email}")
        return project

    # =====================================================================
    # DELETE OPERATIONS
    # =====================================================================

    @classmethod
    @transaction.atomic
    def hard_delete_project(cls, project_id, user, confirm_backup=True):
        """
        Permanently delete a project (IRREVERSIBLE).

        Args:
            project_id: Project ID
            user: User performing deletion
            confirm_backup: Must confirm backup exists

        Returns:
            bool indicating success

        Raises:
            ValueError: If backup confirmation is required but missing
        """
        project = get_object_or_404(Project, id=project_id)

        # Check if backup exists (safety)
        if confirm_backup:
            import os
            from django.conf import settings

            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
            backup_file = os.path.join(backup_dir, f"{project.project_code}.zip")

            if not os.path.exists(backup_file):
                raise ValueError(
                    "Please create a backup before permanent deletion. "
                    f"Project: {project.project_code}"
                )

        # Store project info for audit
        project_name = project.name
        project_code = project.project_code

        # Delete all related data
        project.milestones.all().delete()
        project.gallery_images.all().delete()
        project.service_links.all().delete()

        # Delete the project
        project.delete()

        # Log audit
        AuditService.log_action(
            user=user,
            action='PROJECT_HARD_DELETED',
            entity_type='Project',
            entity_id=str(project_id),
            details={
                'project_name': project_name,
                'project_code': project_code,
                'deleted_at': timezone.now().isoformat(),
                'backup_confirmed': confirm_backup,
            }
        )

        logger.warning(
            f"Project PERMANENTLY DELETED: {project_code} by {user.email}"
        )
        return True
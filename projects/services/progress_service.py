# Progress Service - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

import logging
import math
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from projects.models.project import Project
from projects.models.milestone import Milestone
from accounts.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ProgressService:
    """Service for all project progress-related business logic."""

    # =====================================================================
    # PROGRESS CALCULATION
    # =====================================================================

    @classmethod
    def get_project_progress(cls, project, radius=52):
        """
        Get comprehensive progress data for a project.

        Args:
            project: Project instance
            radius: Radius of the SVG progress ring the values feed into
                    (default 52 matches the small ring on progress.html;
                    detail.html uses radius=85 for its larger ring).

        Returns:
            dict with progress data including circumference and offset
            for the chosen ring radius.
        """
        milestones = project.milestones.all()
        total_milestones = milestones.count()

        if total_milestones == 0:
            return {
                'overall_progress': 0,
                'total_milestones': 0,
                'completed_milestones': 0,
                'in_progress_milestones': 0,
                'pending_milestones': 0,
                'overdue_milestones': 0,
                'circumference': 2 * math.pi * radius,
                'offset': 2 * math.pi * radius,
            }

        # Count by status
        completed = milestones.filter(status='COMPLETED').count()
        in_progress = milestones.filter(status='IN_PROGRESS').count()
        pending = milestones.filter(status='PENDING').count()
        overdue = milestones.filter(status='OVERDUE').count()

        # Calculate overall progress
        total_progress = sum(float(m.completion_percentage) for m in milestones)
        overall = round(total_progress / total_milestones, 2)

        # Calculate circumference for the requested ring radius
        circumference = 2 * math.pi * radius
        offset = circumference - (overall / 100) * circumference

        return {
            'overall_progress': overall,
            'total_milestones': total_milestones,
            'completed_milestones': completed,
            'in_progress_milestones': in_progress,
            'pending_milestones': pending,
            'overdue_milestones': overdue,
            'circumference': circumference,
            'offset': offset,
        }

    @classmethod
    def get_milestone_progress(cls, milestone):
        """
        Get progress data for a single milestone.

        Args:
            milestone: Milestone instance

        Returns:
            dict with milestone progress data
        """
        return {
            'id': milestone.id,
            'title': milestone.title,
            'status': milestone.status,
            'completion_percentage': float(milestone.completion_percentage),
            'target_date': milestone.target_date,
            'completed_date': milestone.completed_date,
            'is_overdue': milestone.is_overdue,
            'days_until_target': milestone.days_until_target,
            'days_overdue': milestone.days_overdue,
        }

    @classmethod
    def update_project_progress(cls, project):
        """
        Recalculate and update overall project progress from milestones.

        Args:
            project: Project instance

        Returns:
            Updated progress percentage
        """
        return project.update_progress()

    # =====================================================================
    # CHART DATA
    # =====================================================================

    @classmethod
    def get_progress_chart_data(cls, project):
        """
        Get data for progress visualization charts.

        Args:
            project: Project instance

        Returns:
            dict with chart data
        """
        milestones = project.milestones.all().order_by('target_date')

        # Status distribution for pie chart
        status_counts = milestones.values('status').annotate(
            count=Count('id')
        )

        status_labels = []
        status_data = []
        status_colors = {
            'COMPLETED': '#27AE60',
            'IN_PROGRESS': '#F39C12',
            'PENDING': '#95A5A6',
            'OVERDUE': '#E74C3C',
        }

        for item in status_counts:
            status_labels.append(item['status'])
            status_data.append(item['count'])

        # Progress trend for line chart
        timeline_data = []
        cumulative_progress = 0
        total_milestones = milestones.count()

        for idx, milestone in enumerate(milestones, 1):
            cumulative_progress += float(milestone.completion_percentage)
            timeline_data.append({
                'milestone': milestone.title,
                'progress': round(cumulative_progress / idx if idx > 0 else 0, 1),
                'target_date': milestone.target_date.strftime('%Y-%m-%d'),
                'status': milestone.status,
            })

        return {
            'status_distribution': {
                'labels': status_labels,
                'data': status_data,
                'colors': [status_colors.get(s, '#95A5A6') for s in status_labels],
            },
            'progress_timeline': timeline_data,
            'overall': cls.get_project_progress(project),
            # Flat keys the progress.html line chart reads directly.
            'labels': [item['milestone'] for item in timeline_data],
            'data':   [item['progress'] for item in timeline_data],
        }

    # =====================================================================
    # MILESTONE OPERATIONS
    # =====================================================================

    @classmethod
    @transaction.atomic
    def create_milestone(cls, project, data, user):
        """
        Create a new milestone for a project.

        Args:
            project: Project instance
            data: dict with milestone fields
            user: User creating milestone

        Returns:
            Milestone instance
        """
        milestone = Milestone.objects.create(
            project=project,
            created_by=user,
            **data
        )

        # Update project progress
        project.update_progress()

        # Log audit
        AuditService.log_action(
            user=user,
            action='MILESTONE_CREATED',
            entity_type='Milestone',
            entity_id=milestone.id,
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'milestone_title': milestone.title,
                'target_date': milestone.target_date.isoformat(),
            }
        )

        logger.info(
            f"Milestone created: {milestone.title} for {project.project_code} "
            f"by {user.email}"
        )
        return milestone

    @classmethod
    @transaction.atomic
    def update_milestone(cls, milestone_id, data, user):
        """
        Update an existing milestone.

        Args:
            milestone_id: Milestone ID
            data: dict with fields to update
            user: User performing update

        Returns:
            Updated Milestone instance
        """
        milestone = get_object_or_404(Milestone, id=milestone_id)
        project = milestone.project

        # Track old values for audit
        old_status = milestone.status
        old_completion = milestone.completion_percentage

        # Update fields
        for key, value in data.items():
            if hasattr(milestone, key):
                setattr(milestone, key, value)

        milestone.save()

        # Update project progress
        project.update_progress()

        # Log audit
        AuditService.log_action(
            user=user,
            action='MILESTONE_UPDATED',
            entity_type='Milestone',
            entity_id=milestone.id,
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'milestone_title': milestone.title,
                'old_status': old_status,
                'new_status': milestone.status,
                'old_completion': float(old_completion),
                'new_completion': float(milestone.completion_percentage),
            }
        )

        logger.info(
            f"Milestone updated: {milestone.title} for {project.project_code} "
            f"by {user.email}"
        )
        return milestone

    @classmethod
    @transaction.atomic
    def complete_milestone(cls, milestone_id, user):
        """
        Mark a milestone as complete.

        Args:
            milestone_id: Milestone ID
            user: User performing action

        Returns:
            Completed Milestone instance
        """
        milestone = get_object_or_404(Milestone, id=milestone_id)
        project = milestone.project

        milestone.mark_complete(user)

        # Log audit
        AuditService.log_action(
            user=user,
            action='MILESTONE_COMPLETED',
            entity_type='Milestone',
            entity_id=milestone.id,
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'milestone_title': milestone.title,
                'completed_date': milestone.completed_date.isoformat(),
            }
        )

        logger.info(
            f"Milestone completed: {milestone.title} for {project.project_code} "
            f"by {user.email}"
        )
        return milestone

    @classmethod
    @transaction.atomic
    def delete_milestone(cls, milestone_id, user):
        """
        Delete a milestone.

        Args:
            milestone_id: Milestone ID
            user: User performing deletion

        Returns:
            bool indicating success
        """
        milestone = get_object_or_404(Milestone, id=milestone_id)
        project = milestone.project
        milestone_title = milestone.title

        milestone.delete()

        # Update project progress
        project.update_progress()

        # Log audit
        AuditService.log_action(
            user=user,
            action='MILESTONE_DELETED',
            entity_type='Milestone',
            entity_id=str(milestone_id),
            details={
                'project_name': project.name,
                'project_code': project.project_code,
                'milestone_title': milestone_title,
            }
        )

        logger.info(
            f"Milestone deleted: {milestone_title} for {project.project_code} "
            f"by {user.email}"
        )
        return True

    # =====================================================================
    # MILESTONE STATUS COUNTS
    # =====================================================================

    @classmethod
    def get_milestone_status_counts(cls, project):
        """
        Numeric counts per milestone status for a project.

        Used by the milestones.html page to populate the four status
        summary cards (Completed / In Progress / Overdue / Pending).

        Args:
            project: Project instance

        Returns:
            dict with completed_count, in_progress_count, overdue_count,
            pending_count
        """
        milestones = project.milestones.all()
        return {
            'completed_count':   milestones.filter(status=Milestone.Status.COMPLETED).count(),
            'in_progress_count': milestones.filter(status=Milestone.Status.IN_PROGRESS).count(),
            'overdue_count':     milestones.filter(status=Milestone.Status.OVERDUE).count(),
            'pending_count':     milestones.filter(status=Milestone.Status.PENDING).count(),
        }

    # =====================================================================
    # PROJECT TIMELINE
    # =====================================================================

    @classmethod
    def get_project_timeline(cls, project):
        """
        Build a chronological event list plus total_days / days_remaining
        for the project timeline view.

        Args:
            project: Project instance

        Returns:
            dict with total_days, days_remaining, events (sorted by date)
        """
        today = timezone.now().date()
        start = project.start_date
        end = project.estimated_completion or project.end_date

        if start and end:
            total_days = (end - start).days
        elif start:
            total_days = (today - start).days
        else:
            total_days = 0

        if end:
            days_remaining = max((end - today).days, 0)
        else:
            days_remaining = 0

        events = []
        if start:
            events.append({
                'title': 'Project Started',
                'date': start,
                'type': 'start',
                'description': f'Project {project.project_code} kicked off.',
            })

        for m in project.milestones.all().order_by('target_date'):
            if not m.target_date:
                continue
            if m.status == Milestone.Status.COMPLETED:
                label = 'Completed'
                description = (
                    f'Completed at {m.completion_percentage}%'
                    if m.completed_date
                    else f'Completed at {m.completion_percentage}%'
                )
            else:
                label = 'Deadline'
                description = f'Target {m.completion_percentage}% complete'
            events.append({
                'title': f'{label}: {m.title}',
                'date': m.target_date,
                'type': 'deadline',
                'description': description,
            })

        if end:
            events.append({
                'title': 'Target Completion',
                'date': end,
                'type': 'end',
                'description': 'Estimated completion date.',
            })

        events.sort(key=lambda e: e['date'])
        return {
            'total_days': total_days,
            'days_remaining': days_remaining,
            'events': events,
        }

    # =====================================================================
    # OVERDUE DETECTION
    # =====================================================================

    @classmethod
    def get_overdue_milestones(cls, project=None):
        """
        Get all overdue milestones, optionally filtered by project.

        Args:
            project: Optional Project instance

        Returns:
            QuerySet of overdue milestones
        """
        queryset = Milestone.objects.filter(
            status__in=['PENDING', 'IN_PROGRESS'],
            target_date__lt=timezone.now().date()
        )

        if project:
            queryset = queryset.filter(project=project)

        return queryset.select_related('project')

    @classmethod
    def get_upcoming_milestones(cls, project=None, days=7):
        """
        Get milestones due in the next N days.

        Args:
            project: Optional Project instance
            days: Number of days ahead

        Returns:
            QuerySet of upcoming milestones
        """
        today = timezone.now().date()
        future_date = today + timezone.timedelta(days=days)

        queryset = Milestone.objects.filter(
            status__in=['PENDING', 'IN_PROGRESS'],
            target_date__gte=today,
            target_date__lte=future_date
        ).order_by('target_date')

        if project:
            queryset = queryset.filter(project=project)

        return queryset.select_related('project')
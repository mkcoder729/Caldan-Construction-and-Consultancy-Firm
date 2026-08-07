"""
Team Service - CRUD operations and featured member management.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.services.audit_service import AuditService
from team.models import TeamMember

logger = logging.getLogger('caldan.team')


class TeamService:
    """
    Service for team member management operations.
    All methods are class methods following the service-oriented architecture.
    """

    @classmethod
    def get_all_members(cls, filters=None, page=1, per_page=20):
        """
        Get all team members with optional filters.
        """
        queryset = TeamMember.objects.all()

        if filters:
            # Search filter
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(title__icontains=search) |
                    Q(email__icontains=search) |
                    Q(role__icontains=search)
                )

            # Role filter
            role = filters.get('role')
            if role:
                queryset = queryset.filter(role=role)

            # Active filter
            is_active = filters.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active)

            # Featured filter
            is_featured = filters.get('is_featured')
            if is_featured is not None:
                queryset = queryset.filter(is_featured=is_featured)

        # Order by display_order, then name
        queryset = queryset.order_by('display_order', 'name')

        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        total = queryset.count()

        return {
            'members': queryset[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        }

    @classmethod
    def get_member(cls, member_id):
        """
        Get a single team member by ID.
        """
        return get_object_or_404(TeamMember, id=member_id)

    @classmethod
    def create_member(cls, data, user):
        """
        Create a new team member.
        """
        # Check if display_order is already taken
        display_order = data.get('display_order', 0)
        if TeamMember.objects.filter(display_order=display_order).exists():
            # Shift existing members down
            TeamMember.objects.filter(display_order__gte=display_order).update(
                display_order=models.F('display_order') + 1
            )

        member = TeamMember.objects.create(**data)

        # Log audit
        AuditService.log_action(
            user=user,
            action='TEAM_MEMBER_CREATED',
            entity_type='TeamMember',
            entity_id=str(member.id),
            details={
                'name': member.name,
                'role': member.role,
                'is_featured': member.is_featured,
            }
        )

        logger.info(f"Team member created: {member.name} by {user.email}")
        return member

    @classmethod
    def update_member(cls, member_id, data, user):
        """
        Update an existing team member.
        """
        member = cls.get_member(member_id)

        # Handle display_order changes
        old_order = member.display_order
        new_order = data.get('display_order', old_order)

        if new_order != old_order:
            if new_order > old_order:
                # Moving down: shift others up
                TeamMember.objects.filter(
                    display_order__gt=old_order,
                    display_order__lte=new_order
                ).exclude(id=member_id).update(
                    display_order=models.F('display_order') - 1
                )
            else:
                # Moving up: shift others down
                TeamMember.objects.filter(
                    display_order__gte=new_order,
                    display_order__lt=old_order
                ).exclude(id=member_id).update(
                    display_order=models.F('display_order') + 1
                )

        # Update fields
        for key, value in data.items():
            setattr(member, key, value)
        member.save()

        # Log audit
        AuditService.log_action(
            user=user,
            action='TEAM_MEMBER_UPDATED',
            entity_type='TeamMember',
            entity_id=str(member.id),
            details={
                'name': member.name,
                'role': member.role,
                'is_featured': member.is_featured,
            }
        )

        logger.info(f"Team member updated: {member.name} by {user.email}")
        return member

    @classmethod
    def delete_member(cls, member_id, user):
        """
        Delete a team member.
        """
        member = cls.get_member(member_id)
        member_name = member.name

        # Log audit before deletion
        AuditService.log_action(
            user=user,
            action='TEAM_MEMBER_DELETED',
            entity_type='TeamMember',
            entity_id=str(member.id),
            details={
                'name': member.name,
                'role': member.role,
            }
        )

        member.delete()

        # Reorder remaining members
        cls._reorder_members()

        logger.info(f"Team member deleted: {member_name} by {user.email}")
        return True

    @classmethod
    def toggle_featured(cls, member_id, user):
        """
        Toggle the featured status of a team member.
        """
        member = cls.get_member(member_id)
        member.is_featured = not member.is_featured
        member.save(update_fields=['is_featured'])

        # Log audit
        AuditService.log_action(
            user=user,
            action='TEAM_MEMBER_TOGGLED_FEATURED',
            entity_type='TeamMember',
            entity_id=str(member.id),
            details={
                'name': member.name,
                'is_featured': member.is_featured,
            }
        )

        logger.info(f"Team member {member.name} featured toggled to {member.is_featured}")
        return member

    @classmethod
    def get_featured_members(cls, limit=None):
        """
        Get featured team members for public display.
        """
        queryset = TeamMember.objects.filter(is_active=True, is_featured=True)
        queryset = queryset.order_by('display_order', 'name')

        if limit:
            queryset = queryset[:limit]

        return queryset

    @classmethod
    def get_active_members(cls, limit=None):
        """
        Get all active team members for public display.
        """
        queryset = TeamMember.objects.filter(is_active=True)
        queryset = queryset.order_by('display_order', 'name')

        if limit:
            queryset = queryset[:limit]

        return queryset

    @classmethod
    def _reorder_members(cls):
        """
        Reorder all team members sequentially after deletion.
        """
        members = TeamMember.objects.order_by('display_order', 'name')
        for idx, member in enumerate(members):
            if member.display_order != idx:
                member.display_order = idx
                member.save(update_fields=['display_order'])

    @classmethod
    def get_stats(cls):
        """
        Get team statistics for dashboard.
        """
        total = TeamMember.objects.count()
        active = TeamMember.objects.filter(is_active=True).count()
        featured = TeamMember.objects.filter(is_featured=True, is_active=True).count()

        # Role breakdown
        role_counts = {}
        for role_code, role_label in TeamMember.Role.choices:
            count = TeamMember.objects.filter(role=role_code, is_active=True).count()
            if count > 0:
                role_counts[role_label] = count

        return {
            'total': total,
            'active': active,
            'featured': featured,
            'role_counts': role_counts,
        }
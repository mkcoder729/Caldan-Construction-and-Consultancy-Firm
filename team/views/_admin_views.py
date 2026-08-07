"""
Admin Views - Team App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from accounts.permissions.decorators import admin_required, chief_admin_required
from team.forms import TeamMemberForm
from team.services import TeamService
from team.models import TeamMember

logger = logging.getLogger('caldan.team')


# =====================================================================
# TEAM MEMBERS LIST
# =====================================================================

@login_required
@admin_required
def member_list(request):
    """
    List all team members with filters and pagination.
    Sidebar Page: Team > Team Members
    """
    # Get filters
    search = request.GET.get('search')
    role = request.GET.get('role')
    is_active = request.GET.get('is_active')
    page = int(request.GET.get('page', 1))

    # Parse is_active filter
    if is_active == 'true':
        is_active = True
    elif is_active == 'false':
        is_active = False
    else:
        is_active = None

    filters = {
        'search': search,
        'role': role,
        'is_active': is_active,
    }

    # Get members
    result = TeamService.get_all_members(
        filters=filters,
        page=page,
        per_page=20
    )

    # Get role choices for filter
    role_choices = TeamMember.Role.choices

    # Get stats
    stats = TeamService.get_stats()

    context = {
        'members': result['members'],
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages'],
        'search': search,
        'current_role': role,
        'current_active': is_active,
        'role_choices': role_choices,
        'stats': stats,
        'page_title': 'Team Members',
    }

    return render(request, 'team/dashboard/admin/team/list.html', context)


# =====================================================================
# TEAM MEMBER CREATE
# =====================================================================

@login_required
@admin_required
def member_create(request):
    """
    Create a new team member.
    Sidebar Page: Team > Add Member
    """
    if request.method == 'POST':
        form = TeamMemberForm(request.POST, request.FILES)

        if form.is_valid():
            # Create member via service
            member = TeamService.create_member(
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Team member "{member.name}" created successfully!'
            )

            return redirect('team:member_detail', member_id=member.id)

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = TeamMemberForm()

    context = {
        'form': form,
        'page_title': 'Add Team Member',
    }

    return render(request, 'team/dashboard/admin/team/create.html', context)


# =====================================================================
# TEAM MEMBER DETAIL
# =====================================================================

@login_required
@admin_required
def member_detail(request, member_id):
    """
    Team member detail page.
    Sidebar Page: Team > Member Detail
    """
    member = TeamService.get_member(member_id)

    context = {
        'member': member,
        'page_title': member.name,
    }

    return render(request, 'team/dashboard/admin/team/detail.html', context)


# =====================================================================
# TEAM MEMBER EDIT
# =====================================================================

@login_required
@admin_required
def member_edit(request, member_id):
    """
    Edit an existing team member.
    Sidebar Page: Team > Edit Member
    """
    member = TeamService.get_member(member_id)

    if request.method == 'POST':
        form = TeamMemberForm(request.POST, request.FILES, instance=member)

        if form.is_valid():
            # Update via service
            member = TeamService.update_member(
                member_id=member.id,
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Team member "{member.name}" updated successfully!'
            )

            return redirect('team:member_detail', member_id=member.id)

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = TeamMemberForm(instance=member)

    context = {
        'form': form,
        'member': member,
        'page_title': f'Edit {member.name}',
    }

    return render(request, 'team/dashboard/admin/team/edit.html', context)


# =====================================================================
# TEAM MEMBER DELETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def member_delete(request, member_id):
    """
    Delete a team member.
    """
    try:
        member = TeamService.delete_member(member_id, request.user)

        messages.success(request, 'Team member deleted successfully.')

    except Exception as e:
        logger.error(f"Team member deletion failed: {str(e)}")
        messages.error(request, f'Deletion failed: {str(e)}')

    return redirect('team:member_list')


# =====================================================================
# TEAM MEMBER TOGGLE FEATURED
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def member_toggle_featured(request, member_id):
    """
    Toggle featured status of a team member (AJAX).
    """
    try:
        member = TeamService.toggle_featured(member_id, request.user)

        return JsonResponse({
            'success': True,
            'is_featured': member.is_featured,
            'message': f'"{member.name}" {"featured" if member.is_featured else "unfeatured"} successfully.',
        })

    except Exception as e:
        logger.error(f"Toggle featured failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=400)
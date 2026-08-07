# Admin Views - Projects - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone

# Import decorators from the new location
from accounts.permissions.decorators import admin_required, chief_admin_required

from projects.forms import ProjectForm, MilestoneForm
from projects.services.project_service import ProjectService
from projects.services.progress_service import ProgressService
from projects.models import Project, Milestone


# =====================================================================
# PROJECT LIST VIEW
# =====================================================================

@login_required
@admin_required
def project_list(request):
    """
    List all projects with filters and pagination.
    Sidebar Page: Projects > All Projects
    """
    # Get filter parameters
    status = request.GET.get('status')
    search = request.GET.get('search')
    county = request.GET.get('county')
    page = request.GET.get('page', 1)

    filters = {
        'status': status,
        'search': search,
        'county': county,
        'is_archived': False,
    }

    # Get projects
    result = ProjectService.get_all_projects(
        filters=filters,
        page=page,
        per_page=20,
        user=request.user
    )

    # Get counties for filter
    counties = ProjectService.get_counties()

    context = {
        'projects': result['projects'],
        'status_counts': result['status_counts'],
        'current_status': status,
        'search': search,
        'current_county': county,
        'counties': counties,
        'page_title': 'Projects',
    }

    return render(request, 'projects/dashboard/admin/projects/list.html', context)


# =====================================================================
# PROJECT CREATE VIEW
# =====================================================================

@login_required
@admin_required
def project_create(request):
    """
    Create a new project.
    Sidebar Page: Projects > Create Project
    """
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)

        if form.is_valid():
            # Create project via service
            project = ProjectService.create_project(
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Project "{project.name}" created successfully!'
            )

            # Redirect to project detail
            return redirect('admin_projects:project_detail', project_id=project.id)

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = ProjectForm()

    context = {
        'form': form,
        'page_title': 'Create Project',
    }

    return render(request, 'projects/dashboard/admin/projects/create.html', context)


# =====================================================================
# PROJECT DETAIL VIEW
# =====================================================================

@login_required
@admin_required
def project_detail(request, project_id):
    """
    Project overview page.
    Sidebar Page: Projects > Project Detail
    """
    # Get project with summary
    summary = ProjectService.get_project_summary(project_id, request.user)

    # Get progress data — passing radius=85 because the SVG ring on
    # detail.html uses <circle r="85">; the default 52 would mismatch.
    progress = ProgressService.get_project_progress(summary['project'], radius=85)

    context = {
        'project': summary['project'],
        'milestones': summary['milestones'][:5],  # Show latest 5
        'stats': summary['stats'],
        'financial': summary['financial'],
        'gallery': summary['gallery'],
        'services': summary['services'],
        'progress': progress,
        'page_title': summary['project'].name,
    }

    return render(request, 'projects/dashboard/admin/projects/detail.html', context)


# =====================================================================
# PROJECT EDIT VIEW
# =====================================================================

@login_required
@admin_required
def project_edit(request, project_id):
    """
    Edit an existing project.
    Sidebar Page: Projects > Edit Project
    """
    project = get_object_or_404(Project, id=project_id)

    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)

        if form.is_valid():
            # Update via service
            project = ProjectService.update_project(
                project_id=project.id,
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Project "{project.name}" updated successfully!'
            )

            return redirect('admin_projects:project_detail', project_id=project.id)

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = ProjectForm(instance=project)

    context = {
        'form': form,
        'project': project,
        'page_title': f'Edit {project.name}',
    }

    return render(request, 'projects/dashboard/admin/projects/edit.html', context)


# =====================================================================
# PROJECT PROGRESS VIEW
# =====================================================================

@login_required
@admin_required
def project_progress(request, project_id):
    """
    Project progress tracking page.
    Sidebar Page: Projects > Project Progress
    """
    project = get_object_or_404(Project, id=project_id)
    milestones = project.milestones.all().order_by('order', 'target_date')

    # Get progress data
    progress = ProgressService.get_project_progress(project)
    chart_data = ProgressService.get_progress_chart_data(project)

    # JSON-encode the labels/data so the template can drop them straight
    # into data-* attributes and Chart.js can JSON.parse them.
    # Without json.dumps, Django renders Python list repr (single quotes)
    # which is NOT valid JSON and JSON.parse fails silently.
    chart_data_json = {
        'labels': json.dumps(chart_data['labels']),
        'data':   json.dumps(chart_data['data']),
        # Pass the rest through unchanged for any template usage.
        'status_distribution': chart_data['status_distribution'],
        'progress_timeline':  chart_data['progress_timeline'],
        'overall':            chart_data['overall'],
    }

    context = {
        'project': project,
        'milestones': milestones,
        'progress': progress,
        'chart_data': chart_data_json,
        'page_title': f'{project.name} - Progress',
    }

    return render(request, 'projects/dashboard/admin/projects/progress.html', context)


# =====================================================================
# PROJECT MILESTONES VIEW
# =====================================================================

@login_required
@admin_required
def project_milestones(request, project_id):
    """
    Manage project milestones.
    Sidebar Page: Projects > Milestones
    """
    project = get_object_or_404(Project, id=project_id)
    milestones = project.milestones.all().order_by('order', 'target_date')

    # Status counts power the four summary cards at the top of the page.
    status_counts = ProgressService.get_milestone_status_counts(project)

    # Handle milestone creation
    if request.method == 'POST':
        form = MilestoneForm(request.POST, project=project)

        if form.is_valid():
            # Create milestone via service
            milestone = ProgressService.create_milestone(
                project=project,
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Milestone "{milestone.title}" created successfully!'
            )

            return redirect('admin_projects:project_milestones', project_id=project.id)

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = MilestoneForm(project=project)

    context = {
        'project': project,
        'milestones': milestones,
        'form': form,
        # Spread the four scalars so the template can read them as
        # completed_count, in_progress_count, overdue_count, pending_count.
        **status_counts,
        'page_title': f'{project.name} - Milestones',
    }

    return render(request, 'projects/dashboard/admin/projects/milestones.html', context)


# =====================================================================
# PROJECT TIMELINE VIEW
# =====================================================================

@login_required
@admin_required
def project_timeline(request, project_id):
    """
    Visual project timeline.
    Sidebar Page: Projects > Timeline
    """
    project = get_object_or_404(Project, id=project_id)
    milestones = project.milestones.all().order_by('target_date')

    # Build the chronological event list + total/remaining days so the
    # timeline page renders real data instead of empty state.
    timeline_data = ProgressService.get_project_timeline(project)

    context = {
        'project': project,
        'milestones': milestones,
        'completed_milestones': milestones.filter(status='COMPLETED').count(),
        'total_days':     timeline_data['total_days'],
        'days_remaining': timeline_data['days_remaining'],
        'timeline':       timeline_data['events'],
        'page_title': f'{project.name} - Timeline',
    }

    return render(request, 'projects/dashboard/admin/projects/timeline.html', context)


# =====================================================================
# PROJECT BUDGET VIEW
# =====================================================================

@login_required
@admin_required
def project_budget(request, project_id):
    """
    Project budget tracking page.
    Sidebar Page: Projects > Budget
    """
    project = get_object_or_404(Project, id=project_id)

    # Get expenses linked to this project (newest first)
    try:
        from finances.models.expense import Expense
        expenses = Expense.objects.filter(project=project).order_by('-expense_date')
    except ImportError:
        expenses = []

    # Get financial summary - try to import, but handle if finances app not ready
    try:
        from finances.services.financial_service import FinancialService
        financial = FinancialService.get_project_financial_summary(project.id)
    except ImportError:
        # Fallback if finances app doesn't exist yet - compute from expenses
        total_spent = sum((e.amount for e in expenses), Decimal('0'))
        financial = {
            'total_budget': float(project.budget),
            'total_spent': float(total_spent),
            'remaining_budget': float(project.budget) - float(total_spent),
            'budget_used_percentage': (
                (float(total_spent) / float(project.budget) * 100)
                if project.budget else 0
            ),
            'recent_payments': [],
            'recent_expenses': [],
        }

    # Get budgets
    try:
        from finances.models.budget import Budget
        budgets = Budget.objects.filter(project=project)
    except ImportError:
        budgets = []

    # Flatten the values the template uses directly (total_spent, remaining,
    # budget_used_pct) so the page renders without needing to dig into
    # the finances dict at every callsite.
    context = {
        'project': project,
        'finances': financial,
        'expenses': expenses,
        'total_spent': financial.get('total_spent', 0),
        'remaining': financial.get('remaining_budget', 0),
        'budget_used_pct': financial.get('budget_used_percentage', 0),
        'budgets': budgets,
        'page_title': f'{project.name} - Budget',
    }

    return render(request, 'projects/dashboard/admin/projects/budget.html', context)


# =====================================================================
# PROJECT DELETE (AJAX)
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def project_delete(request, project_id):
    """
    Soft delete a project via AJAX.
    """
    try:
        project = ProjectService.archive_project(project_id, request.user)
        return JsonResponse({
            'success': True,
            'message': f'Project "{project.name}" archived successfully.',
        })
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred.',
        }, status=500)


# =====================================================================
# PROJECT RESTORE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def project_restore(request, project_id):
    """
    Restore an archived project.
    """
    try:
        project = ProjectService.restore_project(project_id, request.user)
        messages.success(
            request,
            f'Project "{project.name}" restored successfully!'
        )
        return redirect('admin_projects:project_detail', project_id=project.id)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('admin_projects:project_list')
    except Exception as e:
        messages.error(request, 'An unexpected error occurred.')
        return redirect('admin_projects:project_list')


# =====================================================================
# MILESTONE COMPLETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def milestone_complete(request, milestone_id):
    """
    Mark a milestone as complete.
    """
    try:
        milestone = ProgressService.complete_milestone(milestone_id, request.user)
        messages.success(
            request,
            f'Milestone "{milestone.title}" marked as complete!'
        )
        return redirect('admin_projects:project_milestones', project_id=milestone.project.id)
    except Exception as e:
        messages.error(request, 'Failed to complete milestone.')
        return redirect('admin_projects:project_list')


# =====================================================================
# MILESTONE DELETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def milestone_delete(request, milestone_id):
    """
    Delete a milestone.
    """
    try:
        milestone = get_object_or_404(Milestone, id=milestone_id)
        project_id = milestone.project.id

        ProgressService.delete_milestone(milestone_id, request.user)
        messages.success(request, 'Milestone deleted successfully!')

        return redirect('admin_projects:project_milestones', project_id=project_id)
    except Exception as e:
        messages.error(request, 'Failed to delete milestone.')
        return redirect('admin_projects:project_list')


# =====================================================================
# UPDATE PROJECT PROGRESS (AJAX)
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def update_progress(request, project_id):
    """
    Manually update project progress via AJAX.
    """
    try:
        progress = request.POST.get('progress')
        notes = request.POST.get('notes', '')

        if progress is None:
            return JsonResponse({
                'success': False,
                'error': 'Progress value is required.',
            }, status=400)

        project = ProjectService.update_progress(
            project_id=project_id,
            progress=float(progress),
            notes=notes,
            user=request.user
        )

        return JsonResponse({
            'success': True,
            'progress': float(project.progress),
            'message': 'Progress updated successfully!',
        })
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred.',
        }, status=500)


# Projects URLs - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.urls import path
from projects.views import (
    project_list,
    project_create,
    project_detail,
    project_edit,
    project_progress,
    project_milestones,
    project_timeline,
    project_budget,
)
from projects.views._admin_views import (
    project_delete,
    project_restore,
    milestone_complete,
    milestone_delete,
    update_progress,
)

app_name = 'projects'

urlpatterns = [
    # Dashboard Pages (8 views)
    path('', project_list, name='project_list'),
    path('create/', project_create, name='project_create'),
    path('<int:project_id>/', project_detail, name='project_detail'),
    path('<int:project_id>/edit/', project_edit, name='project_edit'),
    path('<int:project_id>/progress/', project_progress, name='project_progress'),
    path('<int:project_id>/milestones/', project_milestones, name='project_milestones'),
    path('<int:project_id>/timeline/', project_timeline, name='project_timeline'),
    path('<int:project_id>/budget/', project_budget, name='project_budget'),

    # AJAX/API Actions
    path('<int:project_id>/delete/', project_delete, name='project_delete'),
    path('<int:project_id>/restore/', project_restore, name='project_restore'),
    path('<int:project_id>/update-progress/', update_progress, name='update_progress'),

    # Milestone Actions
    path('milestone/<int:milestone_id>/complete/', milestone_complete, name='milestone_complete'),
    path('milestone/<int:milestone_id>/delete/', milestone_delete, name='milestone_delete'),
]
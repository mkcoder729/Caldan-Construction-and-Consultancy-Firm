# View Tests - Projects - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from projects.models import Project, Milestone
from projects.services.project_service import ProjectService

User = get_user_model()


class ProjectViewTests(TestCase):
    """Test cases for project views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create admin user
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            full_name='Test Admin',
            phone='0712345678',
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

        # Create test project
        self.project_data = {
            'name': 'Test Project',
            'description': 'Test description',
            'location': 'Westlands',
            'county': 'Nairobi',
            'town': 'Westlands',
            'start_date': timezone.now().date(),
            'budget': 1000000,
            'status': 'ACTIVE',
        }
        self.project = ProjectService.create_project(self.project_data, self.admin)

    def test_project_list_view_requires_login(self):
        """Test that project list requires authentication."""
        response = self.client.get(reverse('admin_projects:project_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_project_list_view_authenticated(self):
        """Test project list view with authenticated admin."""
        self.client.login(email='admin@test.com', password='testpass123')
        response = self.client.get(reverse('admin_projects:project_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/dashboard/admin/projects/list.html')
        self.assertContains(response, 'Test Project')

    def test_project_list_view_filters(self):
        """Test project list view with filters."""
        self.client.login(email='admin@test.com', password='testpass123')

        # Test status filter
        response = self.client.get(reverse('admin_projects:project_list') + '?status=ACTIVE')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')

        # Test search filter
        response = self.client.get(reverse('admin_projects:project_list') + '?search=Test')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')

    def test_project_create_view(self):
        """Test project creation view."""
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.get(reverse('admin_projects:project_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/dashboard/admin/projects/create.html')

        # Test POST
        post_data = {
            'name': 'New Project',
            'description': 'New project description',
            'location': 'Nairobi CBD',
            'county': 'Nairobi',
            'town': 'Nairobi',
            'start_date': timezone.now().date().isoformat(),
            'budget': 2000000,
            'status': 'PLANNING',
        }
        response = self.client.post(reverse('admin_projects:project_create'), post_data)

        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(name='New Project')
        self.assertIsNotNone(project)

    def test_project_detail_view(self):
        """Test project detail view."""
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.get(
            reverse('admin_projects:project_detail', kwargs={'project_id': self.project.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/dashboard/admin/projects/detail.html')
        self.assertContains(response, 'Test Project')

    def test_project_edit_view(self):
        """Test project edit view."""
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.get(
            reverse('admin_projects:project_edit', kwargs={'project_id': self.project.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/dashboard/admin/projects/edit.html')

        # Test POST
        post_data = {
            'name': 'Updated Project Name',
            'description': 'Updated description',
            'location': 'Westlands',
            'county': 'Nairobi',
            'town': 'Westlands',
            'start_date': timezone.now().date().isoformat(),
            'budget': 1500000,
            'status': 'ACTIVE',
        }
        response = self.client.post(
            reverse('admin_projects:project_edit', kwargs={'project_id': self.project.id}),
            post_data
        )

        # Should redirect to detail
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Updated Project Name')
        self.assertEqual(self.project.budget, 1500000)

    def test_project_progress_view(self):
        """Test project progress view."""
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.get(
            reverse('admin_projects:project_progress', kwargs={'project_id': self.project.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/dashboard/admin/projects/progress.html')
        self.assertContains(response, 'Overall Progress')

    def test_project_milestones_view(self):
        """Test project milestones view."""
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.get(
            reverse('admin_projects:project_milestones', kwargs={'project_id': self.project.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/dashboard/admin/projects/milestones.html')
        self.assertContains(response, 'Add Milestone')

        # Test adding a milestone via POST
        post_data = {
            'title': 'Test Milestone',
            'description': 'Test description',
            'target_date': timezone.now().date().isoformat(),
        }
        response = self.client.post(
            reverse('admin_projects:project_milestones', kwargs={'project_id': self.project.id}),
            post_data
        )

        # Should redirect back to milestones page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Milestone.objects.count(), 1)

    def test_project_timeline_view(self):
        """Test project timeline view."""
        self.client.login(email='admin@test.com', password='testpass123')

        # Create a milestone for timeline
        Milestone.objects.create(
            project=self.project,
            title='Test Timeline Milestone',
            target_date=timezone.now().date() + timezone.timedelta(days=30),
            created_by=self.admin
        )

        response = self.client.get(
            reverse('admin_projects:project_timeline', kwargs={'project_id': self.project.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/dashboard/admin/projects/timeline.html')
        self.assertContains(response, 'Test Timeline Milestone')

    def test_project_budget_view(self):
        """Test project budget view."""
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.get(
            reverse('admin_projects:project_budget', kwargs={'project_id': self.project.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/dashboard/admin/projects/budget.html')
        self.assertContains(response, 'Budget')

    def test_project_delete_ajax(self):
        """Test project delete via AJAX."""
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.post(
            reverse('admin_projects:project_delete', kwargs={'project_id': self.project.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        import json
        data = json.loads(response.content)
        self.assertTrue(data['success'])

        # Verify project is archived
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_archived)

    def test_milestone_complete(self):
        """Test marking a milestone as complete."""
        self.client.login(email='admin@test.com', password='testpass123')

        milestone = Milestone.objects.create(
            project=self.project,
            title='Test Milestone',
            target_date=timezone.now().date() + timezone.timedelta(days=30),
            completion_percentage=0,
            created_by=self.admin
        )

        response = self.client.post(
            reverse('admin_projects:milestone_complete', kwargs={'milestone_id': milestone.id})
        )

        self.assertEqual(response.status_code, 302)
        milestone.refresh_from_db()
        self.assertEqual(milestone.completion_percentage, 100)
        self.assertEqual(milestone.status, 'COMPLETED')

    def test_milestone_delete(self):
        """Test deleting a milestone."""
        self.client.login(email='admin@test.com', password='testpass123')

        milestone = Milestone.objects.create(
            project=self.project,
            title='Test Milestone',
            target_date=timezone.now().date() + timezone.timedelta(days=30),
            created_by=self.admin
        )

        self.assertEqual(Milestone.objects.count(), 1)

        response = self.client.post(
            reverse('admin_projects:milestone_delete', kwargs={'milestone_id': milestone.id})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Milestone.objects.count(), 0)

    def test_update_progress_ajax(self):
        """Test updating progress via AJAX."""
        self.client.login(email='admin@test.com', password='testpass123')

        response = self.client.post(
            reverse('admin_projects:update_progress', kwargs={'project_id': self.project.id}),
            {'progress': '75', 'notes': 'Test progress update'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        import json
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['progress'], 75)

        self.project.refresh_from_db()
        self.assertEqual(self.project.progress, 75)

    def test_unauthorized_access(self):
        """Test that non-admin users cannot access views."""
        # Create a regular user (non-admin)
        regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            full_name='Regular User',
            phone='0712345678',
            is_active=True
        )

        self.client.login(email='user@test.com', password='testpass123')

        # Try to access project list
        response = self.client.get(reverse('admin_projects:project_list'))
        # Should return 403 Forbidden
        self.assertEqual(response.status_code, 403)
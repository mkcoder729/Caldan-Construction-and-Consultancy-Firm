# Project Service Tests - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from projects.models import Project, Milestone
from projects.services.project_service import ProjectService
from projects.services.progress_service import ProgressService

User = get_user_model()


class ProjectServiceTests(TestCase):
    """Test cases for ProjectService."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            full_name='Test Admin',
            phone='0712345678',
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

        self.project_data = {
            'name': 'Test Project',
            'description': 'This is a test project',
            'location': 'Westlands',
            'county': 'Nairobi',
            'town': 'Westlands',
            'start_date': timezone.now().date(),
            'budget': 1000000,
            'status': 'PLANNING',
        }

    def test_create_project(self):
        """Test creating a project."""
        project = ProjectService.create_project(self.project_data, self.user)

        self.assertIsNotNone(project.id)
        self.assertEqual(project.name, 'Test Project')
        self.assertEqual(project.budget, 1000000)
        self.assertTrue(project.project_code.startswith('PRJ-'))
        self.assertEqual(project.created_by, self.user)

    def test_create_project_auto_generates_code(self):
        """Test that project code is auto-generated."""
        project = ProjectService.create_project(self.project_data, self.user)

        self.assertIsNotNone(project.project_code)
        self.assertTrue(project.project_code.startswith('PRJ-'))
        self.assertRegex(project.project_code, r'^PRJ-\d{4}-\d{4}$')

    def test_get_project(self):
        """Test retrieving a project."""
        project = ProjectService.create_project(self.project_data, self.user)

        retrieved = ProjectService.get_project(project.id, self.user)
        self.assertEqual(retrieved.id, project.id)
        self.assertEqual(retrieved.name, project.name)

    def test_get_all_projects(self):
        """Test retrieving all projects with filtering."""
        # Create multiple projects
        for i in range(3):
            data = self.project_data.copy()
            data['name'] = f'Test Project {i}'
            ProjectService.create_project(data, self.user)

        result = ProjectService.get_all_projects(user=self.user)
        self.assertEqual(result['total_count'], 3)
        self.assertEqual(len(result['projects']), 3)

    def test_get_all_projects_with_filter(self):
        """Test filtering projects."""
        # Create projects with different statuses
        data1 = self.project_data.copy()
        data1['name'] = 'Active Project'
        data1['status'] = 'ACTIVE'
        ProjectService.create_project(data1, self.user)

        data2 = self.project_data.copy()
        data2['name'] = 'Planning Project'
        data2['status'] = 'PLANNING'
        ProjectService.create_project(data2, self.user)

        filters = {'status': 'ACTIVE'}
        result = ProjectService.get_all_projects(filters=filters, user=self.user)
        self.assertEqual(result['total_count'], 1)
        self.assertEqual(result['projects'][0].name, 'Active Project')

    def test_get_all_projects_with_search(self):
        """Test searching projects."""
        ProjectService.create_project(self.project_data, self.user)

        filters = {'search': 'Test'}
        result = ProjectService.get_all_projects(filters=filters, user=self.user)
        self.assertEqual(result['total_count'], 1)

        filters = {'search': 'Nonexistent'}
        result = ProjectService.get_all_projects(filters=filters, user=self.user)
        self.assertEqual(result['total_count'], 0)

    def test_update_project(self):
        """Test updating a project."""
        project = ProjectService.create_project(self.project_data, self.user)

        update_data = {
            'name': 'Updated Project Name',
            'budget': 2000000,
            'status': 'ACTIVE',
        }

        updated = ProjectService.update_project(project.id, update_data, self.user)
        self.assertEqual(updated.name, 'Updated Project Name')
        self.assertEqual(updated.budget, 2000000)
        self.assertEqual(updated.status, 'ACTIVE')

    def test_update_progress(self):
        """Test updating project progress."""
        project = ProjectService.create_project(self.project_data, self.user)
        self.assertEqual(project.progress, 0)

        updated = ProjectService.update_progress(
            project.id, 75, 'Test progress update', self.user
        )
        self.assertEqual(updated.progress, 75)

    def test_archive_project(self):
        """Test archiving a project."""
        project = ProjectService.create_project(self.project_data, self.user)
        self.assertFalse(project.is_archived)

        archived = ProjectService.archive_project(project.id, self.user)
        self.assertTrue(archived.is_archived)
        self.assertEqual(archived.status, 'ARCHIVED')
        self.assertIsNotNone(archived.archived_at)

    def test_archive_already_archived(self):
        """Test archiving an already archived project."""
        project = ProjectService.create_project(self.project_data, self.user)
        ProjectService.archive_project(project.id, self.user)

        with self.assertRaises(ValueError):
            ProjectService.archive_project(project.id, self.user)

    def test_restore_project(self):
        """Test restoring an archived project."""
        project = ProjectService.create_project(self.project_data, self.user)
        ProjectService.archive_project(project.id, self.user)

        restored = ProjectService.restore_project(project.id, self.user)
        self.assertFalse(restored.is_archived)
        self.assertEqual(restored.status, 'PLANNING')
        self.assertIsNone(restored.archived_at)

    def test_get_project_summary(self):
        """Test getting project summary."""
        project = ProjectService.create_project(self.project_data, self.user)

        # Add a milestone
        milestone = Milestone.objects.create(
            project=project,
            title='Test Milestone',
            target_date=timezone.now().date() + timedelta(days=30),
            created_by=self.user
        )

        summary = ProjectService.get_project_summary(project.id, self.user)
        self.assertEqual(summary['project'].id, project.id)
        self.assertEqual(summary['stats']['total_milestones'], 1)
        self.assertEqual(summary['stats']['completion_rate'], 0)

    def test_hard_delete_project_requires_backup(self):
        """Test that hard delete requires backup confirmation."""
        project = ProjectService.create_project(self.project_data, self.user)

        with self.assertRaises(ValueError) as context:
            ProjectService.hard_delete_project(project.id, self.user, confirm_backup=True)

        self.assertIn('backup', str(context.exception).lower())

    def test_get_counties(self):
        """Test getting list of counties."""
        ProjectService.create_project(self.project_data, self.user)

        data2 = self.project_data.copy()
        data2['county'] = 'Kisumu'
        ProjectService.create_project(data2, self.user)

        counties = ProjectService.get_counties()
        self.assertIn('Nairobi', counties)
        self.assertIn('Kisumu', counties)
        self.assertEqual(len(counties), 2)
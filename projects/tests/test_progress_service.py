# Progress Service Tests - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from projects.models import Project, Milestone
from projects.services.project_service import ProjectService
from projects.services.progress_service import ProgressService

User = get_user_model()


class ProgressServiceTests(TestCase):
    """Test cases for ProgressService."""

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
            'status': 'ACTIVE',
        }

        self.project = ProjectService.create_project(self.project_data, self.user)

    def test_get_project_progress_no_milestones(self):
        """Test progress with no milestones."""
        progress = ProgressService.get_project_progress(self.project)
        self.assertEqual(progress['overall_progress'], 0)
        self.assertEqual(progress['total_milestones'], 0)

    def test_get_project_progress_with_milestones(self):
        """Test progress with milestones."""
        # Create milestones with different completion levels
        Milestone.objects.create(
            project=self.project,
            title='Milestone 1',
            target_date=timezone.now().date() + timedelta(days=10),
            completion_percentage=100,
            status='COMPLETED',
            created_by=self.user
        )

        Milestone.objects.create(
            project=self.project,
            title='Milestone 2',
            target_date=timezone.now().date() + timedelta(days=20),
            completion_percentage=50,
            status='IN_PROGRESS',
            created_by=self.user
        )

        Milestone.objects.create(
            project=self.project,
            title='Milestone 3',
            target_date=timezone.now().date() + timedelta(days=30),
            completion_percentage=0,
            status='PENDING',
            created_by=self.user
        )

        progress = ProgressService.get_project_progress(self.project)
        self.assertEqual(progress['total_milestones'], 3)
        self.assertEqual(progress['completed_milestones'], 1)
        self.assertEqual(progress['in_progress_milestones'], 1)
        self.assertEqual(progress['pending_milestones'], 1)
        self.assertEqual(progress['overall_progress'], 50)

    def test_update_project_progress(self):
        """Test updating project progress from milestones."""
        Milestone.objects.create(
            project=self.project,
            title='Milestone 1',
            target_date=timezone.now().date() + timedelta(days=10),
            completion_percentage=75,
            created_by=self.user
        )

        Milestone.objects.create(
            project=self.project,
            title='Milestone 2',
            target_date=timezone.now().date() + timedelta(days=20),
            completion_percentage=25,
            created_by=self.user
        )

        progress = ProgressService.update_project_progress(self.project)
        self.assertEqual(progress, 50)

    def test_create_milestone(self):
        """Test creating a milestone."""
        data = {
            'title': 'Test Milestone',
            'description': 'Test description',
            'target_date': timezone.now().date() + timedelta(days=30),
        }

        milestone = ProgressService.create_milestone(self.project, data, self.user)

        self.assertIsNotNone(milestone.id)
        self.assertEqual(milestone.title, 'Test Milestone')
        self.assertEqual(milestone.project, self.project)
        self.assertEqual(milestone.status, 'PENDING')

    def test_complete_milestone(self):
        """Test completing a milestone."""
        milestone = Milestone.objects.create(
            project=self.project,
            title='Test Milestone',
            target_date=timezone.now().date() + timedelta(days=30),
            completion_percentage=50,
            created_by=self.user
        )

        completed = ProgressService.complete_milestone(milestone.id, self.user)
        self.assertEqual(completed.completion_percentage, 100)
        self.assertEqual(completed.status, 'COMPLETED')
        self.assertIsNotNone(completed.completed_date)

    def test_delete_milestone(self):
        """Test deleting a milestone."""
        milestone = Milestone.objects.create(
            project=self.project,
            title='Test Milestone',
            target_date=timezone.now().date() + timedelta(days=30),
            created_by=self.user
        )

        self.assertEqual(Milestone.objects.count(), 1)
        ProgressService.delete_milestone(milestone.id, self.user)
        self.assertEqual(Milestone.objects.count(), 0)

    def test_get_overdue_milestones(self):
        """Test getting overdue milestones."""
        # Past due milestone
        Milestone.objects.create(
            project=self.project,
            title='Overdue Milestone',
            target_date=timezone.now().date() - timedelta(days=5),
            status='PENDING',
            created_by=self.user
        )

        # Future milestone
        Milestone.objects.create(
            project=self.project,
            title='Future Milestone',
            target_date=timezone.now().date() + timedelta(days=5),
            status='PENDING',
            created_by=self.user
        )

        overdue = ProgressService.get_overdue_milestones()
        self.assertEqual(overdue.count(), 1)
        self.assertEqual(overdue.first().title, 'Overdue Milestone')

    def test_get_upcoming_milestones(self):
        """Test getting upcoming milestones."""
        # Upcoming milestone (within 7 days)
        Milestone.objects.create(
            project=self.project,
            title='Upcoming Milestone',
            target_date=timezone.now().date() + timedelta(days=3),
            status='PENDING',
            created_by=self.user
        )

        # Far future milestone
        Milestone.objects.create(
            project=self.project,
            title='Far Milestone',
            target_date=timezone.now().date() + timedelta(days=20),
            status='PENDING',
            created_by=self.user
        )

        upcoming = ProgressService.get_upcoming_milestones(days=7)
        self.assertEqual(upcoming.count(), 1)
        self.assertEqual(upcoming.first().title, 'Upcoming Milestone')

    def test_get_progress_chart_data(self):
        """Test getting progress chart data."""
        Milestone.objects.create(
            project=self.project,
            title='Milestone 1',
            target_date=timezone.now().date() + timedelta(days=10),
            completion_percentage=100,
            status='COMPLETED',
            created_by=self.user
        )

        Milestone.objects.create(
            project=self.project,
            title='Milestone 2',
            target_date=timezone.now().date() + timedelta(days=20),
            completion_percentage=0,
            status='PENDING',
            created_by=self.user
        )

        chart_data = ProgressService.get_progress_chart_data(self.project)
        self.assertIn('status_distribution', chart_data)
        self.assertIn('progress_timeline', chart_data)
        self.assertIn('overall', chart_data)

        # Check status distribution
        labels = chart_data['status_distribution']['labels']
        self.assertIn('COMPLETED', labels)
        self.assertIn('PENDING', labels)
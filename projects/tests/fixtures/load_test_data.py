# Load Test Data Helper - Projects - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

import json
import os
from django.core.management import call_command
from django.db import transaction
from django.core.management.base import BaseCommand


def load_test_fixtures():
    """
    Load all test fixtures for the projects app.
    Usage: from projects.tests.fixtures.load_test_data import load_test_fixtures
    """
    fixture_dir = os.path.dirname(os.path.abspath(__file__))

    fixtures = [
        'users.json',
        'projects.json',
        'milestones.json',
    ]

    for fixture in fixtures:
        fixture_path = os.path.join(fixture_dir, fixture)
        if os.path.exists(fixture_path):
            call_command('loaddata', fixture_path, verbosity=0)
            print(f"✅ Loaded: {fixture}")
        else:
            print(f"⚠️ Fixture not found: {fixture}")


class Command(BaseCommand):
    help = 'Load test data fixtures for projects app'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📋 Loading test fixtures...'))

        with transaction.atomic():
            load_test_fixtures()

        self.stdout.write(self.style.SUCCESS('✅ Test fixtures loaded successfully!'))
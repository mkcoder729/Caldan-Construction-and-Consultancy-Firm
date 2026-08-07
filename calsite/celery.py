"""
Celery configuration for Caldan Construction.

This module defines the Celery application instance for the project.
All Celery tasks should be imported from apps' tasks.py files.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calsite.settings')

app = Celery('caldan_construction')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Timezone settings
app.conf.timezone = settings.TIME_ZONE
app.conf.enable_utc = True

# Task settings
app.conf.task_track_started = True
app.conf.task_time_limit = 30 * 60
app.conf.task_soft_time_limit = 20 * 60

# Beat schedule (will be overridden by database scheduler)
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'


@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}')
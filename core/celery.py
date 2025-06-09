from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the "celery" program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.development")

# Create a Celery instance and configure it with Django settings.
app = Celery("core")

# Using a string here means the worker does not have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


# Schedule the task to run daily at 4 AM
app.conf.beat_schedule = {
    'task-at-4am': {
        'task': 'apps.questions.tasks.calculate_hardness',
        'schedule': crontab(hour=4, minute=0),
    },
}

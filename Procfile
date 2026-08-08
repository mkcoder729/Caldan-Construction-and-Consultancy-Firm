web: gunicorn --config gunicorn.conf.py calsite.wsgi:application
release: bash entrypoint.sh
worker: celery -A calsite worker --loglevel=info --concurrency=1 --max-tasks-per-child=50
beat: celery -A calsite beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
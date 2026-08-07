release: bash entrypoint.sh
web: gunicorn calsite.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --worker-class gthread --timeout 120 --max-requests 1000 --max-requests-jitter 50 --access-logfile - --error-logfile -
worker: celery -A calsite worker --loglevel=info --concurrency=2 --max-tasks-per-child=100
beat: celery -A calsite beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
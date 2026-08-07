release: bash entrypoint.sh
web: gunicorn calsite.wsgi --log-file -
worker: celery -A calsite worker --loglevel=info
beat: celery -A calsite beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

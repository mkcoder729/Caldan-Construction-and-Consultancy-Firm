#!/usr/bin/env bash
# Railway release hook: run before each deploy.
# Idempotent — safe to run multiple times.

set -e

echo "==> Applying database migrations"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Entrypoint complete"

#!/usr/bin/env bash
set -e

echo "🚀 Running migrations..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createcachetable 2>/dev/null || true
echo "✅ Release complete!"
#!/usr/bin/env bash
# ============================================================================
# CALDAN CONSTRUCTION - RAILWAY RELEASE HOOK
# Runs ONCE before each deploy. Does NOT start gunicorn — the Procfile's
# `web:` line handles that. Keep this script idempotent.
# ============================================================================

set -e

echo "=========================================="
echo "🚀 CALDAN CONSTRUCTION - PRODUCTION"
echo "🇰🇪 Building Kenya's Future, One Project at a Time."
echo "=========================================="
echo "📦 Environment: ${ENVIRONMENT:-production}"
echo "📦 Django Settings: ${DJANGO_SETTINGS_MODULE}"
echo "📦 Database: MySQL (mysqlclient)"
echo "📦 Cache: Redis"
echo "📧 Real emails: ${SEND_REAL_EMAILS:-False}"
echo "🌱 Force seed: ${FORCE_SEED:-False}"
echo "🕐 Time: $(date)"
echo "=========================================="

# Create required directories
mkdir -p logs staticfiles media

# ============================================================================
# DATABASE MIGRATIONS
#
# NOTE: gunicorn.conf.py also runs `manage.py migrate` on every worker
# startup as a self-heal guard (in case Railway's release phase was
# skipped via "Restart" instead of "Redeploy"). Running it here too is
# intentional — the release-phase run gives us early failure if the DB
# is unreachable, while the gunicorn-side run catches Restart-only paths.
# `migrate --noinput` is idempotent so double-running is safe.
# ============================================================================
echo "📦 Running database migrations..."
python manage.py migrate --noinput || {
    echo "❌ Migration failed! Check database connection."
    echo "🔍 Database Host: ${MYSQL_HOST:-Not Set}"
    echo "🔍 Database Name: ${MYSQL_DATABASE:-Not Set}"
    exit 1
}
echo "✅ Migrations completed successfully"

# ============================================================================
# COLLECT STATIC FILES
# ============================================================================
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "❌ Static file collection failed!"
    exit 1
}
echo "✅ Static files collected"

# ============================================================================
# CACHE TABLE (For database cache fallback)
# ============================================================================
echo "💾 Setting up cache table..."
python manage.py createcachetable 2>/dev/null || echo "⚠️ Cache table creation skipped (may already exist)"

# ============================================================================
# REDIS CONNECTION CHECK
# ============================================================================
echo "🔍 Checking Redis connection..."
python manage.py shell -c "
import redis
import os
try:
    url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    r = redis.from_url(url)
    r.ping()
    print('✅ Redis is connected and working!')
except Exception as e:
    print(f'⚠️ Redis connection failed: {e}')
    print('⚠️ Celery tasks will not work without Redis!')
" || echo "⚠️ Redis check skipped"

# ============================================================================
# SEED DATA (Single meta-command runs every seed_* in dependency order)
# ============================================================================
echo "🌱 Checking seed state..."

# Check if any data exists (services is a reliable signal)
SERVICE_COUNT=$(python manage.py shell -c "from services.models import Service; print(Service.objects.count())" 2>/dev/null || echo "0")
echo "📊 Current service count: $SERVICE_COUNT"

if [ "${FORCE_SEED:-false}" = "true" ]; then
    echo "🌱 FORCE_SEED=true — running seed_all (idempotent: skips existing rows)..."
    python manage.py seed_all --stop-on-error
    echo "✅ Seed_all completed"
elif [ "$SERVICE_COUNT" -eq "0" ]; then
    echo "🌱 Empty database detected — running seed_all for initial content..."
    python manage.py seed_all --stop-on-error
    echo "✅ Seed_all completed"
    NEW_SERVICE_COUNT=$(python manage.py shell -c "from services.models import Service; print(Service.objects.count())" 2>/dev/null || echo "0")
    echo "📊 Post-seed service count: $NEW_SERVICE_COUNT"
else
    echo "ℹ️ Data already exists ($SERVICE_COUNT services). Skipping seed."
    echo "   Set FORCE_SEED=true in Railway Variables to re-run."
fi

# ============================================================================
# DJANGO CHECKS (Validate production settings)
# ============================================================================
echo "🔍 Running Django production checks..."
python manage.py check --deploy || {
    echo "⚠️ Deployment check warnings (non-fatal)"
}

echo "=========================================="
echo "✅ Entrypoint complete! Gunicorn will now start via Procfile."
echo "=========================================="

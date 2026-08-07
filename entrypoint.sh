#!/usr/bin/env bash
# ============================================================================
# CALDAN CONSTRUCTION - RAILWAY ENTRYPOINT
# Production-grade startup script
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
echo "🕐 Time: $(date)"
echo "=========================================="

# Create required directories
mkdir -p logs staticfiles media

# ============================================================================
# DATABASE MIGRATIONS
# ============================================================================
echo "📦 Running database migrations..."
python manage.py migrate --noinput || {
    echo "❌ Migration failed! Check database connection."
    echo "🔍 Database Host: ${DB_HOST:-Not Set}"
    echo "🔍 Database Name: ${DB_NAME:-Not Set}"
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
# DJANGO CHECKS (Validate production settings)
# ============================================================================
echo "🔍 Running Django production checks..."
python manage.py check --deploy || {
    echo "⚠️ Deployment check warnings (non-fatal)"
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
echo "📋 Logging to: ./logs/"
echo "=========================================="
echo "✅ Entrypoint complete! Starting Gunicorn..."
echo "=========================================="

# ============================================================================
# START GUNICORN
# ============================================================================
exec gunicorn calsite.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level warning \
    --logger-class gunicorn.glogging.Logger \
    --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
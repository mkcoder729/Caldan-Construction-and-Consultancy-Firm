# gunicorn.conf.py - Memory Optimized for Railway Free Tier
import os
import multiprocessing
import subprocess
import sys

# ============================================================================
# SERVER SOCKET
# ============================================================================
port = os.getenv('PORT', '8080')
bind = f"0.0.0.0:{port}"

# ============================================================================
# WORKER CONFIGURATION - REDUCED FOR MEMORY
# ============================================================================
# Railway free tier has 512MB RAM
# Use only 2 workers to save memory
workers = 2

# Number of threads per worker
threads = 2

# Worker type
worker_class = 'gthread'

# ============================================================================
# TIMEOUTS
# ============================================================================
timeout = 60
graceful_timeout = 30
keepalive = 2

# ============================================================================
# REQUEST HANDLING
# ============================================================================
max_requests = 500
max_requests_jitter = 50

# ============================================================================
# LOGGING
# ============================================================================
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# ============================================================================
# PROCESS NAMING
# ============================================================================
proc_name = 'caldan-construction'

# ============================================================================
# PRE-LOAD APPLICATION (Saves memory)
# ============================================================================
preload_app = True

# ============================================================================
# MIGRATION GUARD
# ============================================================================
# Why this exists:
# Railway's `release:` hook (Procfile) runs migrations on full deploys,
# but if you trigger a "Restart" instead of "Redeploy", the release
# phase is skipped and the workers come up against an out-of-date DB.
# Symptoms: 500s like "Unknown column 'projects.is_featured'" or
# "Table 'railway.compassion_outreach_stories' doesn't exist".
#
# This on_starting hook runs migrations idempotently every time
# gunicorn boots. `migrate` is a no-op when the DB is already current,
# so this only adds work when something's actually missing.
#
# Safety:
# - We shell out to a child process BEFORE Django is loaded so we don't
#   fork a half-initialized ORM.
# - We don't fatal-out on failure — gunicorn still boots even if the
#   DB is unreachable, so health checks keep reporting. The error logs
#   are loud enough that you'll see it in the deploy output.
# - We only run when DJANGO_SETTINGS_MODULE is set (i.e. not during
#   local gunicorn dev runs that don't have a DB).
# ============================================================================
def _run_migrations_on_startup(server):
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
    if not settings_module:
        server.log.info("⏭  DJANGO_SETTINGS_MODULE not set — skipping startup migrations")
        return

    server.log.info("📦 Running migrations on gunicorn startup…")
    # Force UTF-8 in the child process so Windows terminals don't choke on
    # manage.py output that contains non-ASCII characters (the Django
    # startup banner uses emoji glyphs like 🔍 and ℹ️).
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env["PYTHONUTF8"] = "1"

    try:
        result = subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=child_env,
        )
        if result.returncode == 0:
            # Only print stdout if migrate actually applied something
            # (otherwise it's a no-op that just says "No migrations to apply").
            out = (result.stdout or "").strip()
            if "No migrations to apply" in out or "Applying" in out:
                for line in out.splitlines():
                    server.log.info(f"   migrate: {line}")
            server.log.info("✅ Migrations check complete")
        else:
            server.log.error("❌ Migration command failed (gunicorn will still start):")
            for line in (result.stdout or "").splitlines():
                server.log.error(f"   stdout: {line}")
            for line in (result.stderr or "").splitlines():
                server.log.error(f"   stderr: {line}")
    except subprocess.TimeoutExpired:
        server.log.error("❌ Migration command timed out after 120s (gunicorn will still start)")
    except Exception as exc:
        server.log.error(f"❌ Migration command crashed: {exc} (gunicorn will still start)")


# ============================================================================
# HOOKS
# ============================================================================
def on_starting(server):
    server.log.info(f"🚀 Caldan Construction starting on port {port} with {workers} workers")
    # Self-heal: ensure DB schema matches models before workers fork.
    # Idempotent — safe to run on every boot, including local dev where
    # `migrate` will be a no-op.
    _run_migrations_on_startup(server)


def when_ready(server):
    server.log.info("✅ Caldan Construction ready to serve requests")
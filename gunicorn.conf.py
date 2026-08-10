# gunicorn.conf.py - Memory Optimized for Railway
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
# WORKER CONFIGURATION
# ============================================================================
# Two workers + two threads each = 4 effective request slots. With
# preload_app=True, workers share the parent's read-only memory pages, so
# the second worker adds roughly 80-150 MB on top of the parent's ~250 MB.
# For low-to-medium traffic (well under 50 req/s sustained) this is the
# sweet spot — single worker is faster to boot but blocks under load,
# three+ workers just wastes RAM on a low-traffic site.
workers = int(os.getenv('GUNICORN_WORKERS', '2'))
threads = int(os.getenv('GUNICORN_THREADS', '2'))

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
# Recycle workers every 500 requests (with ±50 jitter) so any slow leak
# gets cleaned up without a full restart. Each new worker boots from the
# preloaded parent in <1s, so this is nearly invisible to users.
max_requests = 500
max_requests_jitter = 50

# ============================================================================
# LOGGING
# ============================================================================
accesslog = '-'
errorlog = '-'
# 'warning' keeps the deploy/startup logs readable without drowning them
# in per-request access lines (which gunicorn writes to stdout and Railway
# bills as part of log volume).
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'warning')

# ============================================================================
# PROCESS NAMING
# ============================================================================
proc_name = 'caldan-construction'

# ============================================================================
# PRE-LOAD APPLICATION (Saves memory)
# ============================================================================
# Preloading the Django app in the parent process means workers fork with
# already-loaded modules (copy-on-write), so the second worker costs only
# ~80-150 MB of incremental RAM instead of another full ~250 MB.
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
    server.log.info(f"🚀 Caldan Construction starting on port {port} with {workers} workers x {threads} threads")
    # Self-heal: ensure DB schema matches models before workers fork.
    # Idempotent — safe to run on every boot, including local dev where
    # `migrate` will be a no-op.
    _run_migrations_on_startup(server)


def when_ready(server):
    server.log.info("✅ Caldan Construction ready to serve requests")


def _worker_abort(server, worker):
    """Log the worker's memory usage when it gets recycled (max_requests hit)
    or crashes. This is the smoking gun when a leak is happening: the
    RSS line should be roughly the same on every recycle, but a leak
    makes it climb steadily."""
    try:
        import resource
        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux returns KB; macOS returns bytes. Normalize to MB.
        rss_mb = rss_kb / 1024 if rss_kb < 10_000_000 else rss_kb / (1024 * 1024)
        server.log.info(f"📊 worker {worker.age} exiting — RSS {rss_mb:.1f} MB, served {worker.stat.get('requests', 0)} requests")
    except Exception:
        pass


def post_fork(server, worker):
    """Log RSS for each newly forked worker. If leaks exist you'll see
    RSS climb across consecutive `📊 new worker` log lines."""
    try:
        import resource
        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_mb = rss_kb / 1024 if rss_kb < 10_000_000 else rss_kb / (1024 * 1024)
        server.log.info(f"📊 new worker {worker.age} forked — RSS {rss_mb:.1f} MB")
    except Exception:
        pass
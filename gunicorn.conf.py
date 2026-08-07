# gunicorn.conf.py
# Professional Gunicorn configuration for Railway

import os
import multiprocessing

# ============================================================================
# SERVER SOCKET
# ============================================================================
# Railway injects PORT environment variable
# Use os.getenv() to get it properly
port = os.getenv('PORT', '8080')
bind = f"0.0.0.0:{port}"

# ============================================================================
# WORKER CONFIGURATION
# ============================================================================
# Number of worker processes
# Formula: (2 x CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Number of threads per worker
threads = 4

# Worker type - gthread for I/O bound applications
worker_class = 'gthread'

# Maximum number of simultaneous connections per worker
worker_connections = 1000

# ============================================================================
# TIMEOUTS
# ============================================================================
# Worker timeout in seconds
timeout = 120

# Graceful timeout
graceful_timeout = 30

# Keep-alive timeout
keepalive = 5

# ============================================================================
# REQUEST HANDLING
# ============================================================================
# Maximum number of requests a worker will process before restarting
# Helps with memory leaks
max_requests = 1000

# Jitter to prevent all workers from restarting simultaneously
max_requests_jitter = 50

# ============================================================================
# LOGGING
# ============================================================================
# Log to stdout/stderr (Railway captures these)
accesslog = '-'
errorlog = '-'

# Log level
loglevel = 'info'

# Access log format with additional fields
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ============================================================================
# PROCESS NAMING
# ============================================================================
# Easier to identify in process lists
proc_name = 'caldan-construction'

# ============================================================================
# SECURITY
# ============================================================================
# Limit request line size
limit_request_line = 4094

# Limit header fields
limit_request_fields = 100

# Limit header field size
limit_request_field_size = 8190

# ============================================================================
# PRE-LOAD APPLICATION (Optional)
# ============================================================================
# Pre-load application code before forking workers
# Reduces memory usage but increases startup time
preload_app = True

# ============================================================================
# HOOKS (Optional)
# ============================================================================
def on_starting(server):
    """Log when Gunicorn starts."""
    server.log.info(f"🚀 Caldan Construction starting on port {port}")

def on_reload(server):
    """Log when Gunicorn reloads."""
    server.log.info("🔄 Caldan Construction reloading")

def when_ready(server):
    """Log when Gunicorn is ready to serve requests."""
    server.log.info("✅ Caldan Construction ready to serve requests")

def worker_abort(worker):
    """Log when a worker aborts."""
    worker.log.warning(f"⚠️ Worker {worker.pid} aborted")
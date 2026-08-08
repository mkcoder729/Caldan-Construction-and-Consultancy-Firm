# gunicorn.conf.py - Memory Optimized for Railway Free Tier
import os
import multiprocessing

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
# HOOKS
# ============================================================================
def on_starting(server):
    server.log.info(f"🚀 Caldan Construction starting on port {port} with {workers} workers")

def when_ready(server):
    server.log.info("✅ Caldan Construction ready to serve requests")
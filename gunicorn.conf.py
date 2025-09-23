"""
Gunicorn configuration for SyncScope Analytics Service
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
backlog = 2048

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_connections = 1000
timeout = int(os.getenv("GUNICORN_TIMEOUT", 60))
keepalive = 60

# Restart workers after this many requests to prevent memory leaks
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 100))

# Worker timeout
timeout = 60
graceful_timeout = 30

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "syncscope-analytics"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = "/tmp"

# SSL (if needed)
keyfile = os.getenv("SSL_KEYFILE")
certfile = os.getenv("SSL_CERTFILE")

# Application
wsgi_module = "config.wsgi:application"

# Performance
preload_app = True
sendfile = True


# Worker process callbacks
def when_ready(server):
    server.log.info("Analytics Service is ready to serve requests")


def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")


def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)
    # Initialize worker-specific resources here if needed


def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)


def worker_abort(worker):
    worker.log.info("Worker received SIGABRT signal")


# Error handling
def on_exit(server):
    server.log.info("Analytics Service is shutting down")


def on_reload(server):
    server.log.info("Analytics Service is reloading")


# Environment variables
raw_env = [
    "DJANGO_SETTINGS_MODULE=config.settings",
]

# Add any additional environment variables
for key, value in os.environ.items():
    if key.startswith(("DATABASE_", "REDIS_", "SECRET_")):
        raw_env.append(f"{key}={value}")

# Forwarded headers
forwarded_allow_ips = "*"
secure_scheme_headers = {
    "X-FORWARDED-PROTOCOL": "ssl",
    "X-FORWARDED-PROTO": "https",
    "X-FORWARDED-SSL": "on",
}

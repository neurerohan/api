"""
Gunicorn configuration for production deployment on Render.
"""
import os

# Bind to 0.0.0.0 to ensure the application is accessible
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Worker configuration
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout configuration
timeout = 120

# Logging configuration
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Startup notification
def on_starting(server):
    print(f"Starting server on {bind}")

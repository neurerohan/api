#!/bin/bash
# Simple startup script for Render deployment

# Print environment info for debugging
echo "Starting Nepali Data API"
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "PORT environment variable: $PORT"

# Use the PORT environment variable or default to 10000
PORT="${PORT:-10000}"
echo "Using port: $PORT"

# Start the application with the proper host and port arguments
echo "Starting uvicorn with command: uvicorn main:app --host 0.0.0.0 --port $PORT"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"

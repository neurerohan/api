#!/bin/bash
# Explicit port binding for Render deployment

# Print environment information
echo "Starting Nepali Data API"
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "PORT environment variable: $PORT"

# Run the application with explicit port binding
python server.py

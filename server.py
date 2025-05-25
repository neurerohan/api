"""
Server entry point for Render deployment with explicit port binding.
"""
import os
import sys
import logging
from main import app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

if __name__ == "__main__":
    import uvicorn
    import socket
    
    # Get port from environment variable for cloud deployment or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Log important information
    logger.info(f"Starting server on port {port}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Manually test socket binding to verify we can bind to the port
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        test_socket.bind(("0.0.0.0", port))
        logger.info(f"Successfully tested binding to 0.0.0.0:{port}")
        test_socket.close()
    except Exception as e:
        logger.error(f"Error testing port binding: {e}")
        # If the port is already in use, try to find another available port
        if port != 8000:
            logger.info(f"Trying alternate port 8000 instead of {port}")
            port = 8000
    
    # Run the application with explicit host and port binding
    logger.info(f"Starting uvicorn on 0.0.0.0:{port}")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0",  # Bind to all interfaces
        port=port,
        log_level="info"
    )

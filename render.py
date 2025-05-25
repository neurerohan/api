"""
Special entry point for Render deployment that explicitly binds to the PORT environment variable.
"""
import os
import sys
import socket
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("render")

def main():
    """Run the application for Render deployment."""
    # Get port from environment
    port = int(os.environ.get("PORT", 10000))
    
    # Log environment details
    logger.info(f"Starting server for Render deployment")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Using port: {port}")
    
    # Test socket binding explicitly
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", port))
        logger.info(f"Successfully verified binding to 0.0.0.0:{port}")
        sock.close()
    except Exception as e:
        logger.error(f"Error binding to port {port}: {e}")
        sys.exit(1)
    
    # Start the application
    logger.info(f"Starting application on port {port}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )

if __name__ == "__main__":
    main()

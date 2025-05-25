"""
Direct server script for Render deployment that explicitly binds to the port.
"""
import os
import sys
import socket
import logging
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("direct_server")

def main():
    """Start the server with direct port binding for Render."""
    # Get port from environment variable
    port = int(os.environ.get("PORT", 10000))
    
    # Log debug information
    logger.info(f"Starting server with direct port binding")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"PORT environment variable: {port}")
    
    # Import the FastAPI app directly
    from main import app
    
    # Configure the app to listen on 0.0.0.0
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Try to bind to the port
        sock.bind(('0.0.0.0', port))
        logger.info(f"Successfully bound test socket to port {port}")
        sock.close()
    except Exception as e:
        logger.error(f"Error binding to port {port}: {e}")
        # Try alternate port if binding fails
        alt_port = 8000
        logger.info(f"Trying alternate port {alt_port}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('0.0.0.0', alt_port))
            logger.info(f"Successfully bound to alternate port {alt_port}")
            sock.close()
            port = alt_port
        except Exception as e2:
            logger.error(f"Error binding to alternate port: {e2}")
            raise
    
    # Start the application directly
    logger.info(f"Starting application on 0.0.0.0:{port}")
    
    # Use uvicorn directly but with explicit host
    from uvicorn import Config, Server
    config = Config(app=app, host="0.0.0.0", port=port, log_level="info")
    server = Server(config)
    server.run()

if __name__ == "__main__":
    main()

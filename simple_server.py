"""
Ultra simple server for Render deployment that just binds to a port.
"""
import os
import sys
import socket
import logging
import importlib
import subprocess
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("simple_server")

def run_actual_server(port):
    """Run the actual FastAPI application with uvicorn."""
    try:
        # Import needed just to verify imports are working
        import uvicorn
        from fastapi import FastAPI
        
        logger.info(f"Starting FastAPI application on port {port}")
        
        # Run uvicorn directly as a subprocess
        cmd = [
            sys.executable, 
            "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", str(port)
        ]
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        
        # Log successful start
        logger.info(f"Uvicorn process started with PID: {process.pid}")
        
        # Wait for the process
        process.wait()
    except Exception as e:
        logger.error(f"Error running FastAPI app: {e}")
        raise

def main():
    """Main entry point that ensures port binding works."""
    # Get port from environment variable with fallbacks
    port = int(os.environ.get("PORT", 10000))
    fallback_ports = [8000, 8080, 3000]
    
    # Print debug information
    logger.info(f"Starting simple server for Render deployment")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Environment variables: PORT={port}")
    logger.info(f"Files in current directory: {os.listdir('.')}")
    
    # Try to bind to main port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Set socket to reuse address to avoid "address already in use" errors
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Try to bind to specified port
        sock.bind(('0.0.0.0', port))
        logger.info(f"Successfully bound test socket to port {port}")
        sock.close()
        
        # Run the actual server with the working port
        run_actual_server(port)
    except Exception as e:
        logger.error(f"Error binding to port {port}: {e}")
        
        # Try fallback ports
        for fallback_port in fallback_ports:
            logger.info(f"Trying fallback port {fallback_port}")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('0.0.0.0', fallback_port))
                logger.info(f"Successfully bound to fallback port {fallback_port}")
                sock.close()
                
                # Run with fallback port
                run_actual_server(fallback_port)
                break
            except Exception as e2:
                logger.error(f"Error binding to fallback port {fallback_port}: {e2}")
        else:
            logger.error("All port binding attempts failed")
            raise Exception("Could not bind to any port")

if __name__ == "__main__":
    main()

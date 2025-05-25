"""
Middleware components for the Nepali Data API.
This provides rate limiting, request logging, and error handling.
"""
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from typing import Callable, Dict
import asyncio
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware that limits requests per IP address.
    """
    def __init__(self, app: FastAPI, requests_limit: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}  # IP -> List of timestamps
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if this IP is in our records
        current_time = datetime.now()
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove outdated requests
        cutoff_time = current_time - timedelta(seconds=self.window_seconds)
        self.requests[client_ip] = [ts for ts in self.requests[client_ip] if ts > cutoff_time]
        
        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.requests_limit:
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(self.window_seconds)}
            )
        
        # Add current request timestamp
        self.requests[client_ip].append(current_time)
        
        # Process the request
        return await call_next(request)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging request details and timing.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(f"Request started: {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add custom processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log response
        logger.info(f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
        
        return response

def setup_middleware(app: FastAPI):
    """
    Set up all middleware components for the application.
    """
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For development - restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add rate limiting middleware - 60 requests per minute
    app.add_middleware(RateLimitMiddleware, requests_limit=60, window_seconds=60)

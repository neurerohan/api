"""
Global error handlers and exception types for the Nepali Data API.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging
from typing import Dict, Any

# Set up logging
logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API errors"""
    def __init__(self, status_code: int, detail: str, headers: Dict[str, str] = None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

class DatabaseError(APIError):
    """Exception for database errors"""
    def __init__(self, detail: str = "Database error occurred"):
        super().__init__(status_code=500, detail=detail)

class ResourceNotFoundError(APIError):
    """Exception for when a requested resource is not found"""
    def __init__(self, resource_type: str = "Resource", resource_id: Any = None):
        detail = f"{resource_type} not found"
        if resource_id:
            detail += f": {resource_id}"
        super().__init__(status_code=404, detail=detail)

class ScrapingError(APIError):
    """Exception for when scraping fails"""
    def __init__(self, detail: str = "Failed to scrape data"):
        super().__init__(status_code=500, detail=detail)

def setup_error_handlers(app: FastAPI):
    """Register all error handlers with the FastAPI application"""
    
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """Handle custom API exceptions"""
        headers = exc.headers or {}
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors"""
        logger.warning(f"Validation error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation error", "errors": exc.errors()},
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors"""
        logger.error(f"Database error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error occurred"},
        )
    
    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """Handle any unhandled exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred"},
        )

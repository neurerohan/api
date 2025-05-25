import logging
from sqlmodel import Session
from functools import wraps
from database import get_db_context

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all scraping modules
from .rashifal import scrape_rashifal
from .vegetables import scrape_vegetables
from .metals import scrape_metals
from .forex import scrape_forex
from .calendar import scrape_calendar, scrape_hamro_patro, scrape_panchang
from .events import scrape_events

# Helper function to handle database sessions in scraping functions
def with_db_session(func):
    """Decorator that provides a database session to scraping functions.
    This helps avoid the 'Session has no attribute connect' error.
    """
    @wraps(func)
    async def wrapper(db, *args, **kwargs):
        # Check if db is already a valid session
        if isinstance(db, Session) and hasattr(db, 'exec'):
            return await func(db, *args, **kwargs)
        
        # Otherwise, create a new session
        logger.info(f"Creating new database session for {func.__name__}")
        with get_db_context() as session:
            return await func(session, *args, **kwargs)
    
    return wrapper

# Export all scraping functions
__all__ = [
    "scrape_rashifal",
    "scrape_vegetables", 
    "scrape_metals", 
    "scrape_forex", 
    "scrape_calendar", 
    "scrape_events",
    "scrape_hamro_patro",
    "scrape_panchang"
]

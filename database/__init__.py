from sqlmodel import SQLModel, create_engine, Session
import os
import logging
import time
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional
from functools import wraps

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Create the database URL
DATABASE_URL = f"sqlite:///{BASE_DIR / 'nepali_data.db'}"

# Maximum number of retries for database operations
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds

# Create SQLite database engine with optimized settings
engine = create_engine(
    DATABASE_URL, 
    connect_args={
        "check_same_thread": False,
        "timeout": 30,         # Wait up to 30 seconds for the database lock to be released
    },
    pool_pre_ping=True,       # Verify connections before usage
    pool_recycle=3600,        # Recycle connections after 1 hour
    pool_size=20,             # Allow up to 20 concurrent connections
    max_overflow=10,          # Allow 10 more connections beyond pool_size when needed
    echo=False
)

# Context manager for getting a database session with retry logic
@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions with retry logic for better reliability."""
    session = None
    retries = 0
    last_error = None
    
    while retries < MAX_RETRIES:
        try:
            session = Session(engine)
            yield session
            if session.is_active:
                session.commit()
            break
        except Exception as e:
            last_error = e
            logger.warning(f"Database error (attempt {retries+1}/{MAX_RETRIES}): {str(e)}")
            if session and session.is_active:
                session.rollback()
            retries += 1
            if retries < MAX_RETRIES:
                time.sleep(RETRY_DELAY)  # Wait before retrying
        except Exception as e:
            last_error = e
            logger.error(f"Database session error: {e}")
            if session and session.is_active:
                session.rollback()
            retries += 1
            if retries < MAX_RETRIES:
                time.sleep(RETRY_DELAY * retries)  # Exponential backoff
            else:
                raise  # Re-raise the exception after max retries
        finally:
            if session:
                session.close()

# Create a function to get a database session for FastAPI dependency injection
def get_session():
    """Get a database session for FastAPI dependency injection with error handling.
    This is used as a FastAPI dependency in routes.
    """
    session = None
    try:
        session = Session(engine)
        yield session
        if session.is_active:
            session.commit()
    except Exception as e:
        logger.error(f"Database session error in FastAPI dependency: {e}")
        if session and session.is_active:
            session.rollback()
        raise
    finally:
        if session:
            session.close()

# Create a function to initialize the database
def init_db():
    logger.info(f"Initializing database at {DATABASE_URL}")
    SQLModel.metadata.create_all(engine)
    logger.info("Database schema created successfully")

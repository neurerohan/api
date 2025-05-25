"""
Database session management for the Nepali Data API.
"""
import logging
from sqlmodel import Session, create_engine, SQLModel
from contextlib import contextmanager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = "sqlite:///nepali_data.db"

# Create engine
engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    """Create database and tables."""
    logger.info(f"Creating database tables in {DATABASE_URL}")
    SQLModel.metadata.create_all(engine)

@contextmanager
def get_db_session():
    """Get a database session with proper error handling."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def get_session():
    """Generator for FastAPI dependency injection."""
    with get_db_session() as session:
        yield session

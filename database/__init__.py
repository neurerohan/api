from sqlmodel import SQLModel, create_engine, Session
import os
import logging
from pathlib import Path
from contextlib import contextmanager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Create the database URL
DATABASE_URL = f"sqlite:///{BASE_DIR / 'nepali_data.db'}"

# Create SQLite database engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False
)

# Context manager for getting a database session
@contextmanager
def get_db_context():
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

# Create a function to get a database session for FastAPI dependency injection
def get_session():
    with get_db_context() as session:
        yield session

# Create a function to initialize the database
def init_db():
    logger.info(f"Initializing database at {DATABASE_URL}")
    SQLModel.metadata.create_all(engine)
    logger.info("Database schema created successfully")

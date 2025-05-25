import os
import logging
import sqlite3
from sqlmodel import SQLModel, create_engine

from database.models import CalendarDay, Event, Rashifal, MetalPrice, ForexRate, VegetablePrice

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_database(database_url=None):
    """Initialize the database with all models."""
    if database_url is None:
        # Default to SQLite database in the current directory
        database_url = "sqlite:///nepali_data.db"
    
    logger.info(f"Initializing database at {database_url}")
    engine = create_engine(database_url)
    
    # Create all tables
    SQLModel.metadata.create_all(engine)
    logger.info("Database schema created")
    
    # Check and add missing columns
    ensure_schema_up_to_date(database_url)

def ensure_schema_up_to_date(database_url):
    """Ensure all columns defined in models exist in the database."""
    # For SQLite, extract the path from the URL
    if database_url.startswith("sqlite:///"):
        db_path = database_url[10:]  # Remove 'sqlite:///'
    else:
        logger.warning(f"Unsupported database type for migration: {database_url}")
        return
    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check and add missing columns for each table
        add_missing_columns(cursor, 'calendarday', [
            ('nepali_weekday', 'TEXT'),
            ('event', 'TEXT'),
            ('tithi', 'TEXT'),
            ('panchang', 'TEXT'),
            ('is_holiday', 'INTEGER'),
        ])
        
        add_missing_columns(cursor, 'vegetableprice', [
            ('image_url', 'TEXT'),
        ])
        
        conn.commit()
        conn.close()
        logger.info("Database schema successfully updated")
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")

def add_missing_columns(cursor, table_name, columns):
    """Add missing columns to a table if they don't exist."""
    # Get existing columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    # Add missing columns
    for column_name, column_type in columns:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                logger.info(f"Added column {column_name} to table {table_name}")
            except sqlite3.OperationalError as e:
                logger.error(f"Error adding column {column_name} to {table_name}: {e}")

if __name__ == "__main__":
    initialize_database()

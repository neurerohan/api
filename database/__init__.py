from sqlmodel import SQLModel, create_engine, Session
import os
from pathlib import Path

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

# Create a function to get a database session
def get_session():
    with Session(engine) as session:
        yield session

# Create a function to initialize the database
def init_db():
    SQLModel.metadata.create_all(engine)

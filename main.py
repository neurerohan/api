from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, SQLModel, create_engine
import asyncio
import logging
import os
import sys
from typing import List, Optional

# Import database and models
from database import get_session, init_db
from database.models import (
    CalendarDay, Event, Rashifal, 
    MetalPrice, ForexRate, VegetablePrice
)
from database.migrations import ensure_schema_up_to_date
from database.crud import (
    calendar_crud, event_crud, rashifal_crud,
    metal_price_crud, forex_rate_crud, vegetable_price_crud
)

# Import scheduler and scraping functions
from scheduler import scheduler
from scraping import (
    scrape_rashifal, scrape_vegetables, scrape_metals,
    scrape_forex, scrape_calendar, scrape_events, 
    scrape_hamro_patro, scrape_panchang
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Nepali Data API",
    description="API for Nepali calendar, events, rashifal, and market prices",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database with schema migration
def initialize_database():
    """Initialize the database with all models."""
    database_url = "sqlite:///nepali_data.db"
    logger.info(f"Initializing database at {database_url}")
    engine = create_engine(database_url)
    SQLModel.metadata.create_all(engine)
    
    # Ensure database schema is up to date with all columns
    ensure_schema_up_to_date(database_url)
    
    return database_url

# Start app
@app.on_event("startup")
async def startup_event():
    # Initialize database
    initialize_database()
    logger.info("Database initialized")
    
    # Start initial data scraping
    logger.info("Starting initial data scraping")
    await run_initial_scraping()
    
    # Start scheduler
    logger.info("Scheduler started")
    asyncio.create_task(scheduler.start())

    # For Render deployment - bind to 0.0.0.0 explicitly
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Explicitly bind to 0.0.0.0 with port from environment
        port = int(os.environ.get("PORT", 8000))
        sock.bind(("0.0.0.0", port))
        logger.info(f"Successfully bound to 0.0.0.0:{port}")
    except Exception as e:
        logger.error(f"Error binding to port: {e}")
    finally:
        sock.close()

@app.on_event("shutdown")
async def shutdown_event():
    # Stop scheduler
    await scheduler.stop()
    logger.info("Scheduler stopped")

# Initial scraping function
async def run_initial_scraping():
    """Run initial scraping tasks on startup."""
    try:
        db = Session(next(get_session()))
        
        # Run all scraping tasks
        await scrape_rashifal(db)
        await scrape_vegetables(db)
        await scrape_metals(db)
        await scrape_forex(db)
        await scrape_panchang(db)  # Add panchang scraping
        
        # For calendar and events, scrape current data
        from datetime import datetime
        now = datetime.now()
        await scrape_calendar(db, year=now.year, month=now.month)
        await scrape_events(db, year=now.year)
        
        logger.info("Initial data scraping completed")
    except Exception as e:
        logger.error(f"Error in initial data scraping: {str(e)}")


# API Routes

@app.get("/", tags=["Root"])
async def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Nepali Data API",
        "docs_url": "/docs",
        "version": "1.0.0",
    }

@app.get("/calendar/{year}/{month}", tags=["Calendar"], response_model=List[CalendarDay])
async def get_calendar(
    year: int, 
    month: int, 
    db: Session = Depends(get_session)
):
    """Get calendar days for a specific month."""
    calendar_days = calendar_crud.get_by_date(db=db, year=year, month=month)
    
    if not calendar_days:
        # If no data found, try to scrape it
        await scrape_calendar(db, year=year, month=month)
        calendar_days = calendar_crud.get_by_date(db=db, year=year, month=month)
        
    return calendar_days

@app.get("/today", tags=["Calendar"])
async def get_today_date(
    db: Session = Depends(get_session)
):
    from database.session import get_session, create_db_and_tables
    # Use the existing get_session from our session module
    today_info = await scrape_panchang(db)
    
    if not today_info:
        # If scraping fails, return a simple error response
        raise HTTPException(status_code=503, detail="Could not retrieve today's date information")
        
    return today_info

@app.get("/events/{year}", tags=["Events"], response_model=List[Event])
async def get_events(
    year: int, 
    month: Optional[int] = None,
    db: Session = Depends(get_session)
):
    """Get events for a specific year and optional month."""
    if month:
        events = event_crud.get_by_date(db=db, year=year, month=month)
    else:
        events = event_crud.get_by_year(db=db, year=year)
    
    if not events:
        # If no data found, try to scrape it
        await scrape_events(db, year=year)
        
        if month:
            events = event_crud.get_by_date(db=db, year=year, month=month)
        else:
            events = event_crud.get_by_year(db=db, year=year)
        
    return events

@app.get("/rashifal/{sign}", tags=["Rashifal"], response_model=Rashifal)
async def get_rashifal(
    sign: str, 
    db: Session = Depends(get_session)
):
    """Get latest rashifal for a specific zodiac sign."""
    try:
        # Normalize the sign parameter - convert to lowercase
        sign = sign.lower().strip()
        
        # Check if the sign is valid
        from scraping.rashifal import ZODIAC_SIGNS
        if sign not in ZODIAC_SIGNS:
            raise HTTPException(status_code=400, detail=f"Invalid zodiac sign: '{sign}'. Valid signs are: {', '.join(ZODIAC_SIGNS.keys())}")
        
        # Try to get rashifal from database
        rashifal = rashifal_crud.get_by_sign(db=db, sign=sign)
        
        if not rashifal:
            # If no data found, try to scrape it
            logger.info(f"No rashifal found for {sign}, attempting to scrape fresh data")
            await scrape_rashifal(db)
            rashifal = rashifal_crud.get_by_sign(db=db, sign=sign)
            
            if not rashifal:
                raise HTTPException(status_code=404, detail=f"Rashifal for sign '{sign}' not found after scraping")
        
        return rashifal
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error and return a 500 with helpful message
        logger.error(f"Error retrieving rashifal for {sign}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving rashifal: {str(e)}")


@app.get("/prices/vegetables", tags=["Prices"], response_model=List[VegetablePrice])
async def get_vegetable_prices(
    db: Session = Depends(get_session)
):
    """Get latest vegetable prices."""
    prices = vegetable_price_crud.get_latest(db=db)
    
    if not prices:
        # If no data found, try to scrape it
        await scrape_vegetables(db)
        prices = vegetable_price_crud.get_latest(db=db)
        
    return prices

@app.get("/prices/metals", tags=["Prices"], response_model=List[MetalPrice])
async def get_metal_prices(
    db: Session = Depends(get_session)
):
    """Get latest metal prices (gold/silver)."""
    prices = metal_price_crud.get_latest(db=db)
    
    if not prices:
        # If no data found, try to scrape it
        await scrape_metals(db)
        prices = metal_price_crud.get_latest(db=db)
        
    return prices

@app.get("/prices/forex", tags=["Prices"], response_model=List[ForexRate])
async def get_forex_rates(
    db: Session = Depends(get_session)
):
    """Get latest forex rates."""
    rates = forex_rate_crud.get_latest(db=db)
    
    if not rates:
        # If no data found, try to scrape it
        await scrape_forex(db)
        rates = forex_rate_crud.get_latest(db=db)
        
    return rates


@app.get("/cron/scrape", tags=["Admin"])
async def trigger_scrape(api_key: str = None):
    """Endpoint for external cron job to trigger data scraping.
    
    This endpoint is designed to be called by cron-job.org to trigger scraping every 8 hours.
    It will scrape all daily changing data like rashifal, metals, vegetables, etc.
    
    Args:
        api_key: Optional API key for security (can be configured in production)
    """
    from datetime import datetime
    import logging
    logger = logging.getLogger(__name__)
    
    # In production, you should add proper API key validation
    # if api_key != "your_secret_api_key":
    #     raise HTTPException(status_code=403, detail="Invalid API key")
    
    try:
        # Get database session using context manager
        from database import get_db_context
        with get_db_context() as db:
        
            # Run scraping tasks for daily changing data
            start_time = datetime.now()
            logger.info(f"Starting scheduled scraping at {start_time}")
            
            results = {}
            for scraper in [scrape_rashifal, scrape_metals, scrape_vegetables, scrape_forex, scrape_events]:
                try:
                    await scraper(db)
                    results[scraper.__name__] = "success"
                except Exception as e:
                    error_msg = f"Error in {scraper.__name__}: {str(e)}"
                    logger.error(error_msg)
                    results[scraper.__name__] = f"error: {str(e)}"
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Completed scheduled scraping in {duration} seconds")
            
            return {
                "status": "completed",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "results": results
            }
    except Exception as e:
        error_msg = f"Critical error in scheduled scraping: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable for cloud deployment or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Ensure we bind to 0.0.0.0 so the app is accessible externally
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

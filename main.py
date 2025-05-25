from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
import asyncio
import logging
from typing import List, Optional

# Import database and models
from database import get_session, init_db
from database.models import (
    CalendarDay, Event, Rashifal, 
    MetalPrice, ForexRate, VegetablePrice
)
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

# Initialize database and start scheduler
@app.on_event("startup")
async def startup_event():
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Start initial data scraping
    logger.info("Starting initial data scraping")
    background_tasks = BackgroundTasks()
    background_tasks.add_task(run_initial_scraping)
    
    # Start scheduler
    asyncio.create_task(scheduler.start())
    logger.info("Scheduler started")

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
    """Get today's Nepali date with detailed information."""
    # Try to scrape today's information from Ashesh.com.np Panchang
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
    rashifal = rashifal_crud.get_by_sign(db=db, sign=sign)
    
    if not rashifal:
        # If no data found, try to scrape it
        await scrape_rashifal(db)
        rashifal = rashifal_crud.get_by_sign(db=db, sign=sign)
        
        if not rashifal:
            raise HTTPException(status_code=404, detail=f"Rashifal for sign '{sign}' not found")
        
    return rashifal

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
    # In production, you should add proper API key validation
    # if api_key != "your_secret_api_key":
    #     raise HTTPException(status_code=403, detail="Invalid API key")
    
    try:
        db = Session(next(get_session()))
        
        # Run scraping tasks for daily changing data
        await scrape_rashifal(db)
        await scrape_vegetables(db)
        await scrape_metals(db)
        await scrape_forex(db)
        await scrape_panchang(db)  # Get today's panchang information
        
        # For a monthly job, you could add this logic
        # now = datetime.now()
        # if now.day == 1:  # First day of month, scrape the new month's calendar
        #     next_month = now + timedelta(days=32)
        #     next_month = datetime(next_month.year, next_month.month, 1)  # First day of next month
        #     await scrape_calendar(db, year=next_month.year, month=next_month.month)
        
        return {"status": "success", "message": "Data scraping completed successfully", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error in cron-triggered scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in data scraping: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

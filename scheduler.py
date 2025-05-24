import asyncio
import logging
from datetime import datetime, timedelta
from sqlmodel import Session
from typing import Callable, Coroutine, Any, Dict, List
from functools import partial

from database import engine
from scraping import (
    scrape_rashifal,
    scrape_vegetables,
    scrape_metals,
    scrape_forex,
    scrape_calendar,
    scrape_events
)

logger = logging.getLogger(__name__)

class Scheduler:
    """Scheduler for running background scraping tasks."""
    
    def __init__(self):
        self.running = False
        self.tasks = {}
    
    async def run_scraping_task(self, task_func: Callable, name: str) -> None:
        """Run a scraping task and handle errors."""
        logger.info(f"Running scraping task: {name}")
        try:
            with Session(engine) as db:
                await task_func(db)
            logger.info(f"Completed scraping task: {name}")
        except Exception as e:
            logger.error(f"Error in scraping task {name}: {str(e)}")
    
    async def schedule_task(
        self, 
        task_func: Callable[[Session], Coroutine[Any, Any, List[Dict]]], 
        name: str,
        interval_hours: float = 24.0
    ) -> None:
        """Schedule a task to run at specified intervals."""
        while self.running:
            await self.run_scraping_task(task_func, name)
            # Wait for the specified interval
            await asyncio.sleep(interval_hours * 3600)
    
    async def start(self) -> None:
        """Start the scheduler."""
        self.running = True
        
        # Schedule all scraping tasks
        self.tasks["rashifal"] = asyncio.create_task(
            self.schedule_task(scrape_rashifal, "rashifal")
        )
        self.tasks["vegetables"] = asyncio.create_task(
            self.schedule_task(scrape_vegetables, "vegetables")
        )
        self.tasks["metals"] = asyncio.create_task(
            self.schedule_task(scrape_metals, "metals")
        )
        self.tasks["forex"] = asyncio.create_task(
            self.schedule_task(scrape_forex, "forex")
        )
        
        # Calendar and events need year/month parameters
        # For calendar, we'll scrape the current month and the next month
        now = datetime.now()
        self.tasks["calendar_current"] = asyncio.create_task(
            self.schedule_task(
                partial(scrape_calendar, year=now.year, month=now.month),
                "calendar_current"
            )
        )
        
        next_month = now + timedelta(days=31)
        self.tasks["calendar_next"] = asyncio.create_task(
            self.schedule_task(
                partial(scrape_calendar, year=next_month.year, month=next_month.month),
                "calendar_next"
            )
        )
        
        # For events, we'll scrape the current year
        self.tasks["events"] = asyncio.create_task(
            self.schedule_task(
                partial(scrape_events, year=now.year),
                "events"
            )
        )
        
        logger.info("Scheduler started successfully")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
        
        # Cancel all tasks
        for name, task in self.tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.tasks = {}
        logger.info("Scheduler stopped successfully")


# Singleton instance
scheduler = Scheduler()

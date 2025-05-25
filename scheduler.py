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
    scrape_events,
    scrape_panchang
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
        interval_hours: float = 24.0,
        run_immediately: bool = True
    ) -> None:
        """Schedule a task to run at specified intervals.
        
        For daily changing data like rashifal and prices, we'll rely on the cron job endpoint
        that will be triggered by cron-job.org every 8 hours.
        
        For calendar data, we'll keep a backup scheduler with longer intervals.
        """
        # Optionally skip the immediate run for tasks that will be handled by cron jobs
        if run_immediately:
            await self.run_scraping_task(task_func, name)
            
        # Continue with the scheduled interval
        while self.running:
            # Wait for the specified interval
            await asyncio.sleep(interval_hours * 3600)
            await self.run_scraping_task(task_func, name)
    
    async def start(self) -> None:
        """Start the scheduler.
        
        Note: Daily data scraping (rashifal, metals, vegetables, etc.) will primarily be handled
        by the external cron job that calls the /cron/scrape endpoint every 8 hours.
        
        This scheduler is configured as a backup with longer intervals for redundancy.
        """
        self.running = True
        
        # Schedule daily data tasks with reduced frequency (48 hours) as backup
        # These will primarily be handled by the cron job every 8 hours
        # Set run_immediately=False since the initial scraping happens in run_initial_scraping()
        self.tasks["rashifal"] = asyncio.create_task(
            self.schedule_task(scrape_rashifal, "rashifal", interval_hours=48.0, run_immediately=False)
        )
        self.tasks["vegetables"] = asyncio.create_task(
            self.schedule_task(scrape_vegetables, "vegetables", interval_hours=48.0, run_immediately=False)
        )
        self.tasks["metals"] = asyncio.create_task(
            self.schedule_task(scrape_metals, "metals", interval_hours=48.0, run_immediately=False)
        )
        self.tasks["forex"] = asyncio.create_task(
            self.schedule_task(scrape_forex, "forex", interval_hours=48.0, run_immediately=False)
        )
        self.tasks["panchang"] = asyncio.create_task(
            self.schedule_task(scrape_panchang, "panchang", interval_hours=48.0, run_immediately=False)
        )
        
        # Calendar and events are scheduled less frequently
        # For calendar, we'll scrape the current month and the next month
        now = datetime.now()
        
        # Current month calendar (every 7 days to catch updates)
        self.tasks["calendar_current"] = asyncio.create_task(
            self.schedule_task(
                partial(scrape_calendar, year=now.year, month=now.month),
                "calendar_current",
                interval_hours=168.0  # 7 days
            )
        )
        
        # Next month's calendar (scrape at the beginning of each month)
        next_month = now + timedelta(days=31)
        next_month = datetime(next_month.year, next_month.month, 1)  # First day of next month
        self.tasks["calendar_next"] = asyncio.create_task(
            self.schedule_task(
                partial(scrape_calendar, year=next_month.year, month=next_month.month),
                "calendar_next",
                interval_hours=168.0  # 7 days
            )
        )
        
        # Events for the current year (monthly check for updates)
        self.tasks["events"] = asyncio.create_task(
            self.schedule_task(
                partial(scrape_events, year=now.year),
                "events",
                interval_hours=720.0  # 30 days
            )
        )
        
        logger.info("Scheduler started successfully - daily data will be primarily updated by cron job")
    
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

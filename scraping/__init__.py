from .rashifal import scrape_rashifal
from .vegetables import scrape_vegetables
from .metals import scrape_metals
from .forex import scrape_forex
from .calendar import scrape_calendar, scrape_hamro_patro, scrape_panchang
from .events import scrape_events

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

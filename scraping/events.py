import httpx
from bs4 import BeautifulSoup
from typing import Dict, List
from datetime import datetime
import logging
from sqlmodel import Session

from database.crud import event_crud

logger = logging.getLogger(__name__)

async def scrape_events(db: Session, year: int = None) -> List[Dict]:
    """
    Scrape Nepali events and holidays for a specific year.
    
    Args:
        db: Database session
        year: Optional year to scrape (defaults to current year)
        
    Returns:
        List of event data dictionaries
    """
    results = []
    
    # If no year provided, use current year
    if not year:
        year = datetime.now().year
    
    try:
        # Using a Nepali calendar/events API (adjust URL as needed)
        url = f"https://nepalipatro.com.np/events/{year}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # The site structure might have changed, let's try multiple selectors
            # First, try the most common container selectors
            events_container = soup.select_one(".events-container, .events-list, .holidays-list, .calendar-events")
            
            # If not found, try getting the main content area
            if not events_container:
                events_container = soup.select_one(".main-content, .content-area, #content, main")
            
            # If still not found, use the body as fallback
            if not events_container:
                events_container = soup.body
                
            if not events_container:
                logger.warning("Could not find any content on the page - site structure may have changed")
                return []
                
            # Log for debugging
            logger.info(f"Found events container with {len(events_container.select('*'))} child elements")
                
            # Find all event items
            event_items = events_container.select(".event-item, .holiday-item, .festival-item")
            
            for event_item in event_items:
                try:
                    # Extract event title
                    title_elem = event_item.select_one(".event-title, .holiday-name, h3, h4")
                    title = title_elem.text.strip() if title_elem else "Unknown Event"
                    
                    # Extract event date
                    date_elem = event_item.select_one(".event-date, .holiday-date, .date")
                    date_text = date_elem.text.strip() if date_elem else None
                    
                    if date_text:
                        # Parse date (assuming format like "YYYY-MM-DD" or "Month DD, YYYY")
                        try:
                            if "-" in date_text:
                                year, month, day = map(int, date_text.split("-"))
                            else:
                                # For textual dates, try to parse with dateutil
                                parsed_date = datetime.strptime(date_text, "%B %d, %Y")
                                year, month, day = parsed_date.year, parsed_date.month, parsed_date.day
                                
                            date_str = f"{year}-{month:02d}-{day:02d}"
                        except:
                            # If parsing fails, use a fallback approach
                            logger.warning(f"Could not parse date: {date_text}")
                            continue
                    else:
                        logger.warning("No date found for event")
                        continue
                    
                    # Extract event description
                    desc_elem = event_item.select_one(".event-description, .holiday-description, .description, p")
                    description = desc_elem.text.strip() if desc_elem else None
                    
                    # Determine event type and if it's a public holiday
                    event_type = "holiday" if "holiday" in event_item.get("class", []) else "festival"
                    is_public_holiday = "public-holiday" in event_item.get("class", []) or "national-holiday" in event_item.get("class", [])
                    
                    event_data = {
                        "title": title,
                        "description": description,
                        "date": date_str,
                        "year": year,
                        "month": month,
                        "day": day,
                        "event_type": event_type,
                        "is_public_holiday": is_public_holiday
                    }
                    
                    # Save to database
                    event_crud.upsert(db=db, obj_in=event_data)
                    results.append(event_data)
                    
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error parsing event item: {str(e)}")
            
        return results
    
    except Exception as e:
        logger.error(f"Error scraping events for {year}: {str(e)}")
        return []

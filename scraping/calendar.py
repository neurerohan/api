import httpx
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from sqlmodel import Session
from dateutil.parser import parse
import re

from database.crud import calendar_crud

logger = logging.getLogger(__name__)

# Nepali month names with English equivalents
NEPALI_MONTHS = {
    1: "वैशाख",
    2: "जेठ",
    3: "असार",
    4: "साउन",
    5: "भदौ",
    6: "असोज",
    7: "कार्तिक",
    8: "मंसिर",
    9: "पुष",
    10: "माघ",
    11: "फागुन",
    12: "चैत"
}

# Nepali weekday names with English equivalents
NEPALI_WEEKDAYS = {
    "आइतवार": "Sunday",
    "सोमवार": "Monday",
    "मङ्गलवार": "Tuesday",
    "बुधवार": "Wednesday",
    "बिहिवार": "Thursday",
    "शुक्रवार": "Friday",
    "शनिवार": "Saturday"
}

async def scrape_panchang(db: Session) -> Dict:
    """
    Scrape today's detailed panchang (calendar) information from Ashesh.com.np.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with today's panchang information
    """
    try:
        # Using Ashesh.com.np's panchang widget
        url = "https://www.ashesh.com.np/panchang/widget.php?header_title=Nepali%20Panchang&header_color=e6e5e2&api=332257p082"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # All data is in event div with ev_left and ev_right divs
            event_rows = soup.select(".event .ev_left, .event .ev_right")
            
            # Process the data in pairs (label, value)
            data = {}
            for i in range(0, len(event_rows), 2):
                if i + 1 < len(event_rows):
                    label = event_rows[i].text.strip()
                    value = event_rows[i + 1].text.strip()
                    data[label] = value
            
            # Extract specific fields
            nepali_date = data.get("वि.सं", "")  # वि.सं
            english_date = data.get("ईसवी", "")  # ईसवी
            nepal_sambat = data.get("नेपाल संवत", "")  # नेपाल संवत
            sun_info = data.get("सूर्य", "")  # सूर्य
            moon_info = data.get("चन्द्र", "")  # चन्द्र
            tithi = data.get("तिथि", "")  # तिथि
            paksha = data.get("पक्ष", "")  # पक्ष
            nakshatra = data.get("नक्षत्र", "")  # नक्षत्र
            yoga = data.get("योग", "")  # योग
            karana = data.get("करण", "")  # करण
            moon_rashi = data.get("चन्द्र राशि", "")  # चन्द्र राशि
            dinman = data.get("दिनमान", "")  # दिनमान
            ritu = data.get("ऋतु", "")  # ऋतु
            ayana = data.get("आयान", "")  # आयान
            
            # Parse Nepali date to extract year, month, day, weekday
            nepali_date_parts = nepali_date.split()
            nepali_year = nepali_date_parts[0] if len(nepali_date_parts) > 0 else ""
            nepali_month = nepali_date_parts[1] if len(nepali_date_parts) > 1 else ""
            nepali_day = nepali_date_parts[2] if len(nepali_date_parts) > 2 else ""
            nepali_weekday = nepali_date_parts[3] if len(nepali_date_parts) > 3 else ""
            
            # Parse English date
            english_date_parts = english_date.split()
            english_year = english_date_parts[0] if len(english_date_parts) > 0 else ""
            english_month = english_date_parts[1] if len(english_date_parts) > 1 else ""
            english_day = english_date_parts[2].rstrip(",") if len(english_date_parts) > 2 else ""
            english_weekday = english_date_parts[3] if len(english_date_parts) > 3 else ""
            
            # Extract sunrise, sunset, moonrise, moonset times
            sunrise = ""
            sunset = ""
            moonrise = ""
            moonset = ""
            
            if sun_info:
                sun_parts = re.findall(r'(\d+:\d+)\S*', sun_info)
                if len(sun_parts) >= 2:
                    sunrise = sun_parts[0]
                    sunset = sun_parts[1]
            
            if moon_info:
                moon_parts = re.findall(r'(\d+:\d+ (?:AM|PM))\S*', moon_info)
                if len(moon_parts) >= 2:
                    moonrise = moon_parts[0]
                    moonset = moon_parts[1]
            
            # Format sun and moon info
            sun_moon_formatted = ""
            if sunrise and sunset and moonrise and moonset:
                sun_moon_formatted = f"☀ {sunrise}, {sunset}◑ {moonrise}, {moonset}"
            
            # Get events or tithi for the day
            event = tithi.split("upto")[0].strip() if tithi else ""
            
            # Get month number from month name
            month_num = None
            for num, name in NEPALI_MONTHS.items():
                if name == nepali_month:
                    month_num = num
                    break
            
            # Construct the result
            today_info = {
                "nepali_date": nepali_date,
                "english_date": english_date,
                "nepal_sambat": nepal_sambat,
                "tithi": tithi,
                "paksha": paksha,
                "nakshatra": nakshatra,
                "yoga": yoga,
                "karana": karana,
                "moon_rashi": moon_rashi,
                "dinman": dinman,
                "ritu": ritu,
                "ayana": ayana,
                "sunrise": sunrise,
                "sunset": sunset,
                "moonrise": moonrise,
                "moonset": moonset,
                "sun_moon_info": sun_moon_formatted,
                "nepali_year": nepali_year,
                "nepali_month": nepali_month,
                "nepali_month_num": month_num,
                "nepali_day": nepali_day,
                "nepali_weekday": nepali_weekday,
                "english_year": english_year,
                "english_month": english_month,
                "english_day": english_day,
                "english_weekday": english_weekday,
                "event": event,
                # Formatted strings for display
                "nepali_date_text": f"नेपाली पात्रो{english_day}-{english_month}-{english_year}",
                "today_text": f"आज {nepali_year} {nepali_month}",
                "weekday_tithi": f"{nepali_weekday}, {event}"
            }
            
            return today_info
    
    except Exception as e:
        logger.error(f"Error scraping Panchang: {str(e)}")
        return {}

# Keep original function for backward compatibility
async def scrape_hamro_patro(db: Session) -> Dict:
    """
    Scrape today's detailed date information.
    This is now a wrapper around scrape_panchang for backward compatibility.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with today's date information
    """
    return await scrape_panchang(db)

async def scrape_calendar(db: Session, year: int = None, month: int = None) -> List[Dict]:
    """
    Scrape Nepali calendar days for a specific month from Ashesh.com.np.
    
    Args:
        db: Database session
        year: Optional year to scrape (defaults to current year)
        month: Optional month to scrape (defaults to current month)
        
    Returns:
        List of calendar day data dictionaries
    """
    results = []
    
    # If no year/month provided, use current date
    if not year or not month:
        now = datetime.now()
        year = now.year
        month = now.month
    
    # Map English month names to month numbers for the API call
    month_names_to_numbers = {
        "Baishakh": 1, "Jestha": 2, "Ashadh": 3, "Shrawan": 4,
        "Bhadra": 5, "Ashwin": 6, "Kartik": 7, "Mangsir": 8,
        "Poush": 9, "Magh": 10, "Falgun": 11, "Chaitra": 12
    }
    
    # Map from month number to English month name for API call
    numbers_to_month_names = {
        1: "Baishakh", 2: "Jestha", 3: "Ashadh", 4: "Shrawan",
        5: "Bhadra", 6: "Ashwin", 7: "Kartik", 8: "Mangsir",
        9: "Poush", 10: "Magh", 11: "Falgun", 12: "Chaitra"
    }
    
    try:
        # Using Ashesh.com.np for the calendar
        month_name = numbers_to_month_names.get(month, "Baishakh")
        url = f"https://www.ashesh.com.np/nepali-calendar/calendar.php?api=332256p082&year={year}&month={month_name}"
        
        logger.info(f"Scraping calendar for {year}-{month} ({month_name})")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Log successful request
            logger.info(f"Successfully fetched calendar data from {url}")
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract the Nepali month and year from the header
            nepali_month_year_elem = soup.select_one(".cal_left")
            english_month_year_elem = soup.select_one(".cal_right")
            
            nepali_month_year = nepali_month_year_elem.text.strip() if nepali_month_year_elem else ""
            english_month_year = english_month_year_elem.text.strip() if english_month_year_elem else ""
            
            # Parse the Nepali year and month
            nepali_month_name = ""
            nepali_year = year
            if nepali_month_year:
                # Format is like "JESTHA २०८२" - extract the last part as year
                parts = nepali_month_year.split()
                if len(parts) >= 2:
                    # Convert Devanagari digits to Arabic numerals
                    devanagari_to_arabic = {
                        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
                        '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
                    }
                    nepali_year_str = parts[-1]
                    arabic_year = ''.join([devanagari_to_arabic.get(c, c) for c in nepali_year_str])
                    nepali_year = int(arabic_year) if arabic_year.isdigit() else year
                    
                    # Get the month name
                    nepali_month_name = parts[0] if len(parts) > 0 else ""
                    
            # Convert month name to number
            nepali_month = month_names_to_numbers.get(nepali_month_name, month)
            
            # Find all day cells in the calendar table
            day_cells = soup.select("#calendartable td")
            
            for i in range(0, len(day_cells), 7):
                for j in range(7):
                    try:
                        # Extract day number and tithi/event if available
                        day_cell = day_cells[i + j]
                        day_content = day_cell.select_one(".npd")
                        
                        if not day_content:
                            continue
                            
                        day_num = day_content.text.strip()
                        
                        if not day_num.isdigit():
                            continue
                            
                        day_num = int(day_num)
                        
                        # Extract tithi and event information if available
                        tithi_elem = day_cell.select_one(".lunar_day")
                        event_elem = day_cell.select_one(".event_title")
                        
                        tithi = tithi_elem.text.strip() if tithi_elem else ""
                        event = event_elem.text.strip() if event_elem else ""
                        
                        # Extract events
                        event_one_elem = day_cell.select_one(".event_one")
                        rotate_left_elem = day_cell.select_one(".rotate_left")
                        rotate_right_elem = day_cell.select_one(".rotate_right")
                        
                        events = []
                        if event_one_elem and event_one_elem.text.strip() != "\xa0":
                            events.append(event_one_elem.text.strip())
                        if rotate_left_elem and rotate_left_elem.text.strip():
                            events.append(rotate_left_elem.text.strip())
                        if rotate_right_elem and rotate_right_elem.text.strip():
                            events.append(rotate_right_elem.text.strip())
                        
                        event = ", ".join([e for e in events if e])
                        
                        # Determine if it's a holiday - Saturdays and days with special style
                        is_holiday = "color:#FF4D00" in day_cell.get("style", "") or \
                                   day_cell.get("style", "") == "color:#FF4D00" or \
                                   "style='color: #FF4D00'" in str(day_content) or \
                                   "style='color:#FF4D00'" in str(tithi_elem)
                        
                        # Get weekday based on the table column (0-indexed, where 0 = Sunday)
                        weekday_map = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                        
                        # Try to determine the weekday based on column position
                        weekday_index = j
                        english_weekday = weekday_map[weekday_index] if 0 <= weekday_index < len(weekday_map) else ""
                        nepali_weekday = [k for k, v in NEPALI_WEEKDAYS.items() if v == english_weekday][0] if english_weekday in NEPALI_WEEKDAYS.values() else ""
                        
                        # Format dates properly
                        nepali_date = f"{nepali_year}-{nepali_month:02d}-{day_num:02d}"
                        
                        # Parse English month/year format (e.g., "MAY-JUN 2025")
                        english_month = ""
                        english_year = ""
                        if english_month_year:
                            # Format is like "MAY-JUN 2025"
                            if "-" in english_month_year and " " in english_month_year:
                                english_year = english_month_year.split()[-1]
                                english_months = english_month_year.split()[0]
                                english_month = english_months.split("-")[0] if "-" in english_months else english_months
                        
                        # Construct a proper English date string
                        month_name_to_num = {
                            "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
                            "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
                        }
                        english_month_num = month_name_to_num.get(english_month, 1)
                        full_english_date = f"{english_month} {day_num}, {english_year}"
                        
                        # Extract panchang - combine tithi with events as there's no specific panchang section
                        panchang = f"पञ्चाङ्ग: {tithi}" if tithi else ""
                        
                        calendar_data = {
                            "year": nepali_year,
                            "month": nepali_month,
                            "day": day_num,
                            "nepali_date": nepali_date,
                            "english_date": full_english_date,
                            "weekday": english_weekday,
                            "nepali_weekday": nepali_weekday,
                            "is_holiday": is_holiday,
                            "event": event,
                            "tithi": tithi,
                            "panchang": panchang
                        }
                        
                        # Save to database
                        calendar_crud.upsert(db=db, obj_in=calendar_data)
                        results.append(calendar_data)
                        
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Error parsing day cell: {str(e)}")
                    if rotate_left_elem and rotate_left_elem.text.strip():
                        events.append(rotate_left_elem.text.strip())
                    if rotate_right_elem and rotate_right_elem.text.strip():
                        events.append(rotate_right_elem.text.strip())
                    
                    event = ", ".join([e for e in events if e])
                    
                    # Extract tithi
                    tithi_elem = day_cell.select_one(".tithi")
                    tithi = tithi_elem.text.strip() if tithi_elem else ""
                    
                    # Determine if it's a holiday - Saturdays and days with special style
                    is_holiday = "color:#FF4D00" in day_cell.get("style", "") or \
                               day_cell.get("style", "") == "color:#FF4D00" or \
                               "style='color: #FF4D00'" in str(date_np_elem) or \
                               "style='color:#FF4D00'" in str(tithi_elem)
                    
                    # Get weekday based on the table column (0-indexed, where 0 = Sunday)
                    weekday_map = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                    
                    # Try to determine the weekday based on column position
                    weekday_index = -1
                    parent_row = day_cell.parent
                    if parent_row and parent_row.name == "tr":
                        cells = parent_row.select("td")
                        weekday_index = cells.index(day_cell) if day_cell in cells else -1
                    
                    english_weekday = weekday_map[weekday_index] if 0 <= weekday_index < len(weekday_map) else ""
                    nepali_weekday = [k for k, v in NEPALI_WEEKDAYS.items() if v == english_weekday][0] if english_weekday in NEPALI_WEEKDAYS.values() else ""
                    
                    # Format dates properly
                    nepali_date = f"{nepali_year}-{nepali_month:02d}-{nepali_day:02d}"
                    
                    # Parse English month/year format (e.g., "MAY-JUN 2025")
                    english_month = ""
                    english_year = ""
                    if english_month_year:
                        # Format is like "MAY-JUN 2025"
                        if "-" in english_month_year and " " in english_month_year:
                            english_year = english_month_year.split()[-1]
                            english_months = english_month_year.split()[0]
                            english_month = english_months.split("-")[0] if "-" in english_months else english_months
                    
                    # Construct a proper English date string
                    month_name_to_num = {
                        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
                        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
                    }
                    english_month_num = month_name_to_num.get(english_month, 1)
                    full_english_date = f"{english_month} {english_day}, {english_year}"
                    
                    # Extract panchang - combine tithi with events as there's no specific panchang section
                    panchang = f"पञ्चाङ्ग: {tithi}" if tithi else ""
                    
                    calendar_data = {
                        "year": nepali_year,
                        "month": nepali_month,
                        "day": nepali_day,
                        "nepali_date": nepali_date,
                        "english_date": full_english_date,
                        "weekday": english_weekday,
                        "nepali_weekday": nepali_weekday,
                        "is_holiday": is_holiday,
                        "event": event,
                        "tithi": tithi,
                        "panchang": panchang
                    }
                    
                    # Save to database
                    calendar_crud.upsert(db=db, obj_in=calendar_data)
                    results.append(calendar_data)
                    
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error parsing day cell: {str(e)}")
            
        return results
    
    except Exception as e:
        logger.error(f"Error scraping calendar for {year}-{month}: {str(e)}")
        return []

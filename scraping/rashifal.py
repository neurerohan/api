import httpx
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from sqlmodel import Session
import re

from database.crud import rashifal_crud

logger = logging.getLogger(__name__)

# Define zodiac signs in both English and Nepali with mapping to the new source
ZODIAC_SIGNS = {
    "mesh": {"english": "Aries", "nepali": "मेष", "index": 1},
    "brish": {"english": "Taurus", "nepali": "वृष", "index": 2},
    "mithun": {"english": "Gemini", "nepali": "मिथुन", "index": 3},
    "karkat": {"english": "Cancer", "nepali": "कर्कट", "index": 4},
    "singha": {"english": "Leo", "nepali": "सिंह", "index": 5},
    "kanya": {"english": "Virgo", "nepali": "कन्या", "index": 6},
    "tula": {"english": "Libra", "nepali": "तुला", "index": 7},
    "brischik": {"english": "Scorpio", "nepali": "वृश्चिक", "index": 8},
    "dhanu": {"english": "Sagittarius", "nepali": "धनु", "index": 9},
    "makar": {"english": "Capricorn", "nepali": "मकर", "index": 10},
    "kumbha": {"english": "Aquarius", "nepali": "कुम्भ", "index": 11},
    "meen": {"english": "Pisces", "nepali": "मीन", "index": 12}
}

# Reverse mapping from Nepali names to our sign keys
NEPALI_TO_SIGN = {info["nepali"]: sign for sign, info in ZODIAC_SIGNS.items()}

async def scrape_rashifal(db: Session) -> List[Dict]:
    """
    Scrape daily Rashifal (horoscope) for all zodiac signs from Nepali sites.
    
    Args:
        db: Database session
        
    Returns:
        List of rashifal data dictionaries
    """
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Using hamropatro.com as the source
        url = "https://www.hamropatro.com/rashifal"
        
        # Set up headers to mimic a browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
            except httpx.TimeoutException:
                logger.error("Request timed out while fetching rashifal")
                return []
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} while fetching rashifal")
                return []
            except Exception as e:
                logger.error(f"Error fetching rashifal: {str(e)}")
                return []
            
            if not response.text:
                logger.error("Empty response received from rashifal source")
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # The rashifal data is in a table structure
            table = soup.select_one("table")
            if not table:
                logger.error("No table found in the page")
                logger.debug(f"Page content: {response.text[:500]}...")
                return []
                
            # Find all rows in the table
            rashifal_rows = table.select("tr")
            if not rashifal_rows:
                logger.error("No rashifal rows found in the table")
                return []
                
            for row in rashifal_rows[1:]:  # Skip header row
                try:
                    # Extract data from table cells
                    cells = row.select("td")
                    if len(cells) < 2:
                        logger.warning("Row has insufficient cells")
                        continue
                        
                    # First cell contains rashi name, second cell contains prediction
                    name_elem = cells[0]
                    prediction_elem = cells[1]
                    
                    if not all([name_elem, prediction_elem]):
                        logger.warning("Missing required elements in rashifal row")
                        continue
                        
                    # The name cell contains both Nepali and English names
                    name_text = name_elem.text.strip()
                    
                    # Try to extract names using common patterns
                    for s, info in ZODIAC_SIGNS.items():
                        if info['nepali'] in name_text:
                            nepali_name = info['nepali']
                            english_name = info['english']
                            sign = s
                            break
                    else:
                        logger.warning(f"Could not identify rashi from: {name_text}")
                        continue
                    
                    # Get sign key from the Nepali name
                    sign = None
                    for s, info in ZODIAC_SIGNS.items():
                        if info['nepali'] == nepali_name or info['english'].lower() == english_name.lower():
                            sign = s
                            break
                    
                    if not sign:
                        logger.warning(f"Could not map rashifal name to sign: {name_text}")
                        continue
                    
                    # Get prediction text
                    prediction = prediction_elem.text.strip()
                    
                    # Get sign index from image src
                    sign_index = ZODIAC_SIGNS[sign]['index']  # Default to predefined index
                    image_url = image_elem["src"] if image_elem else ""
                    
                    # Extract sign number from image URL if available
                    sign_index = None
                    if image_url:
                        index_match = re.search(r'/(\d+)@2x\.png', image_url)
                        if index_match:
                            sign_index = int(index_match.group(1))
                    
                    rashifal_data = {
                        "sign": sign,
                        "prediction": prediction,
                        "date": today,
                        "nepali_name": nepali_name,
                        "english_name": english_name,
                        "sign_index": sign_index,
                        "prediction_english": None,
                        "lucky_number": None,
                        "lucky_color": None
                    }
                    
                    try:
                        saved_data = rashifal_crud.upsert(db=db, obj_in=rashifal_data)
                        if saved_data:
                            results.append(rashifal_data)
                            logger.info(f"Successfully saved rashifal for {sign}")
                        else:
                            logger.error(f"Failed to save rashifal for {sign}")
                    except Exception as e:
                        logger.error(f"Database error while saving rashifal for {sign}: {str(e)}")
                        continue
                    
                except Exception as e:
                    logger.warning(f"Error parsing rashifal row: {str(e)}")
                    continue
            
            if not results:
                logger.error("No rashifal data was successfully scraped and saved")
            else:
                logger.info(f"Successfully scraped and saved {len(results)} rashifal entries")
            
            return results
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error while scraping rashifal: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error while scraping rashifal: {str(e)}")
        return []

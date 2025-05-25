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
        # Using ashesh.com.np as the source
        url = "https://www.ashesh.com.np/rashifal/widget.php?header_title=Nepali%20Rashifal&header_color=f0b03f&api=522251p370"
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            if not response.text:
                logger.error("Empty response received from rashifal source")
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all rashifal rows - they are inside both columns
            columns = soup.select(".column")
            if not columns:
                logger.error("No columns found in the rashifal page")
                logger.debug(f"Page content: {response.text[:500]}...")
                return []
                
            rashifal_rows = []
            for column in columns:
                rows = column.select(".row")
                rashifal_rows.extend(rows)
            
            if not rashifal_rows:
                logger.error("No rashifal rows found in any column")
                return []
                
            for row in rashifal_rows:
                try:
                    # Extract all required elements
                    name_elem = row.select_one(".rashifal_name")
                    prediction_elem = row.select_one(".rashifal_value")
                    image_elem = row.select_one(".image img")
                    
                    if not all([name_elem, prediction_elem]):
                        logger.warning("Missing required elements in rashifal row")
                        continue
                        
                    # Parse name text which contains both Nepali and English names
                    name_text = name_elem.text.strip()
                    name_parts = name_text.split()
                    
                    if len(name_parts) < 2:
                        logger.warning(f"Invalid name format: {name_text}")
                        continue
                        
                    nepali_name = name_parts[0]  # First part is Nepali name
                    english_name = name_parts[1]  # Second part is English name
                    
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

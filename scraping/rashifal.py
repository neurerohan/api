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
        # Use a more reliable widget URL
        url = "https://www.ashesh.com.np/rashifal/widget.php?header_title=Nepali%20Rashifal&header_color=f0b03f&api=332257p096&header_size=20px&font_color=333333&font_size=14px&line_height=26px&font_family=arial"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all rashifal rows
            rashifal_rows = soup.select(".row")
            
            # Extract date from the header
            header_date = soup.select_one(".header_date iframe")
            date_text = header_date["src"] if header_date else ""
            # The date might be embedded in the iframe, we'll use today's date for simplicity
            
            for row in rashifal_rows:
                try:
                    # Extract the rashifal name (contains both Nepali and English names)
                    name_elem = row.select_one(".rashifal_name")
                    if not name_elem:
                        continue
                        
                    name_text = name_elem.text.strip()
                    
                    # Parse the Nepali and English names
                    name_parts = name_text.split()
                    if len(name_parts) < 2:
                        continue
                        
                    nepali_name = name_parts[0]  # First part is Nepali name
                    english_name = name_parts[1]  # Second part is English name
                    
                    # Get our sign key from the Nepali name
                    sign = NEPALI_TO_SIGN.get(nepali_name)
                    if not sign:
                        # Try to match by English name if Nepali name not found
                        for s, info in ZODIAC_SIGNS.items():
                            if info["english"].lower() == english_name.lower():
                                sign = s
                                break
                                
                    if not sign:
                        logger.warning(f"Could not map rashifal name to sign: {name_text}")
                        continue
                    
                    # Extract the prediction text
                    prediction_elem = row.select_one(".rashifal_value")
                    prediction = prediction_elem.text.strip() if prediction_elem else "No prediction available"
                    
                    # Get the image for potential extra data
                    image_elem = row.select_one("img")
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
                        "prediction_english": None,  # We don't have English translation available
                        "lucky_number": None,  # Not provided in this source
                        "lucky_color": None,   # Not provided in this source
                        "nepali_name": nepali_name,
                        "english_name": english_name,
                        "sign_index": sign_index
                    }
                    
                    # Save to database
                    rashifal_crud.upsert(db=db, obj_in=rashifal_data)
                    results.append(rashifal_data)
                    
                except Exception as e:
                    logger.warning(f"Error parsing rashifal row: {str(e)}")
            
        return results
    
    except Exception as e:
        logger.error(f"Error scraping rashifal: {str(e)}")
        return []

import httpx
from bs4 import BeautifulSoup
from typing import Dict, List
from datetime import datetime
import logging
from sqlmodel import Session
import re

from database.crud import vegetable_price_crud

logger = logging.getLogger(__name__)

async def scrape_vegetables(db: Session) -> List[Dict]:
    """
    Scrape daily vegetable and fruit prices from Ashesh.com.np.
    
    Args:
        db: Database session
        
    Returns:
        List of vegetable price data dictionaries
    """
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Using Ashesh.com.np vegetable widget
        url = "https://www.ashesh.com.np/vegetable/widget.php?api=332259p484&header_color=519122"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract the date from the header
            date_div = soup.select_one(".header_date")
            scrape_date = today
            if date_div:
                date_text = date_div.text.strip()
                # Convert DD-MMM-YYYY to YYYY-MM-DD if possible
                try:
                    date_obj = datetime.strptime(date_text, "%d-%b-%Y")
                    scrape_date = date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    pass
            
            # Find all vegetable/fruit items
            items = soup.select(".country")
            
            if not items:
                logger.warning("Could not find vegetable items on the page")
                return []
                
            for item in items:
                try:
                    # Extract data from the structure
                    name_div = item.select_one(".name")
                    min_div = item.select_one(".unit")
                    max_div = item.select_one(".rate_buying")
                    avg_div = item.select_one(".rate_selling")
                    img_tag = item.select_one(".flag img")
                    
                    if not all([name_div, min_div, max_div, avg_div]):
                        continue
                        
                    name = name_div.text.strip()
                    
                    # Handle '--' values for prices
                    min_price_text = min_div.text.strip()
                    min_price = None if min_price_text == '--' else float(min_price_text)
                    
                    max_price_text = max_div.text.strip()
                    max_price = None if max_price_text == '--' else float(max_price_text)
                    
                    avg_price_text = avg_div.text.strip()
                    avg_price = None if avg_price_text == '--' else float(avg_price_text)
                    
                    # Extract image URL if available
                    image_url = None
                    if img_tag and 'src' in img_tag.attrs:
                        image_url = img_tag['src']
                    
                    vegetable_data = {
                        "name": name,
                        "nepali_name": None,  # Ashesh doesn't provide Nepali names
                        "min_price": min_price,
                        "max_price": max_price,
                        "avg_price": avg_price,
                        "unit": "Per KG",  # Ashesh prices are per kg
                        "date": scrape_date,
                        "image_url": image_url
                    }
                    
                    # Save to database
                    vegetable_price_crud.upsert(db=db, obj_in=vegetable_data)
                    results.append(vegetable_data)
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error parsing item data: {str(e)}")
            
        return results
    
    except Exception as e:
        logger.error(f"Error scraping vegetable prices: {str(e)}")
        return []

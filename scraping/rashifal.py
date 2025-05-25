from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from sqlmodel import Session
import re
from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent

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
        
        # Create a user agent
        ua = UserAgent()
        
        # Set up headers
        headers = {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Make the request
        logger.info(f"Making request to {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch content: {response.status_code}")
            return []
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try different approaches to find rashifal items
        items = []
        
        # Approach 1: Look for rashifal cards
        cards = soup.select('.rashifal-card, .rashi-card, .rashifal-item, .rashi-item')
        if cards:
            logger.info(f"Found {len(cards)} cards with CSS selectors")
            for card in cards:
                try:
                    title = card.find('h3')
                    desc = card.find(class_='desc')
                    if title and desc:
                        items.append({
                            'name': title.get_text(strip=True),
                            'prediction': desc.get_text(strip=True)
                        })
                except Exception as e:
                    logger.warning(f"Error parsing card: {str(e)}")
        
        # Approach 2: Look for h3 elements followed by paragraphs
        if not items:
            h3_elements = soup.find_all('h3')
            logger.info(f"Found {len(h3_elements)} h3 elements")
            for h3 in h3_elements:
                try:
                    title = h3.get_text(strip=True)
                    # Look for prediction in next sibling elements
                    prediction = None
                    next_elem = h3.find_next_sibling()
                    while next_elem and not prediction:
                        if next_elem.name in ['p', 'div'] and next_elem.get_text(strip=True):
                            prediction = next_elem.get_text(strip=True)
                            break
                        next_elem = next_elem.find_next_sibling()
                    
                    if title and prediction:
                        items.append({
                            'name': title,
                            'prediction': prediction
                        })
                except Exception as e:
                    logger.warning(f"Error parsing h3: {str(e)}")
        
        # Save debug info if no items found
        if not items:
            logger.error("No items found")
            with open('debug.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info("Saved page source to debug.html")
            
        # Log findings
        logger.info(f"Found {len(items)} total items")
        if items:
            logger.info(f"Sample item - Name: {items[0]['name']}, Prediction: {items[0]['prediction'][:50]}...")
        
        # Process items and create final results
        results = []
        for item in items:
            try:
                nepali_name = item.get('name')
                prediction = item.get('prediction')
                
                if not all([nepali_name, prediction]):
                    logger.warning("Missing name or prediction")
                    continue
                
                # Find matching sign
                sign = None
                english_name = None
                for s, info in ZODIAC_SIGNS.items():
                    if info['nepali'] == nepali_name:
                        sign = s
                        english_name = info['english']
                        break
                
                if not sign:
                    logger.warning(f"Could not map rashifal name: {nepali_name}")
                    continue
                
                # Create rashifal data
                rashifal_data = {
                    "sign": sign,
                    "prediction": prediction,
                    "date": today,
                    "nepali_name": nepali_name,
                    "english_name": english_name,
                    "sign_index": ZODIAC_SIGNS[sign]['index'],
                    "prediction_english": None,
                    "lucky_number": None,
                    "lucky_color": None
                }
                
                # Save to database if session provided
                if db is not None:
                    try:
                        saved_data = rashifal_crud.upsert(db=db, obj_in=rashifal_data)
                        if saved_data:
                            logger.info(f"Successfully saved rashifal for {sign}")
                        else:
                            logger.error(f"Failed to save rashifal for {sign}")
                    except Exception as e:
                        logger.error(f"Database error while saving rashifal for {sign}: {str(e)}")
                
                # Add to results
                results.append(rashifal_data)
                
            except Exception as e:
                logger.warning(f"Error processing rashifal item: {str(e)}")
                continue
        
        if not results:
            logger.error("No rashifal data was successfully processed")
        else:
            logger.info(f"Successfully processed {len(results)} rashifal entries")
        
        return results
                    
            # Process items and create final results
            results = []
            for item in items:
                try:
                    nepali_name = item.get('name')
                    prediction = item.get('prediction')
                    
                    if not all([nepali_name, prediction]):
                        logger.warning("Missing name or prediction")
                        continue
                    
                    # Find matching sign
                    sign = None
                    english_name = None
                    for s, info in ZODIAC_SIGNS.items():
                        if info['nepali'] == nepali_name:
                            sign = s
                            english_name = info['english']
                            break
                    
                    if not sign:
                        logger.warning(f"Could not map rashifal name: {nepali_name}")
                        continue
                    
                    # Create rashifal data
                    rashifal_data = {
                        "sign": sign,
                        "prediction": prediction,
                        "date": today,
                        "nepali_name": nepali_name,
                        "english_name": english_name,
                        "sign_index": ZODIAC_SIGNS[sign]['index'],
                        "prediction_english": None,
                        "lucky_number": None,
                        "lucky_color": None
                    }
                    
                    # Save to database if session provided
                    if db is not None:
                        try:
                            saved_data = rashifal_crud.upsert(db=db, obj_in=rashifal_data)
                            if saved_data:
                                logger.info(f"Successfully saved rashifal for {sign}")
                            else:
                                logger.error(f"Failed to save rashifal for {sign}")
                        except Exception as e:
                            logger.error(f"Database error while saving rashifal for {sign}: {str(e)}")
                    
                    # Add to results
                    results.append(rashifal_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing rashifal item: {str(e)}")
                    continue
            
            if not results:
                logger.error("No rashifal data was successfully processed")
            else:
                logger.info(f"Successfully processed {len(results)} rashifal entries")
            
            # Log all classes in the page for debugging
            all_classes = set()
            for tag in soup.find_all(True):
                if 'class' in tag.attrs:
                    all_classes.update(tag.attrs['class'])
            logger.info(f"Found classes in page: {all_classes}")
            
            # Try different selectors
            selectors = [
                '.rashifal-card',
                '.rashifal-item',
                '.rashifal',
                '.rashi-card',
                '.rashi-item',
                '.rashi'
            ]
            
            cards = []
            for selector in selectors:
                cards = soup.select(selector)
                if cards:
                    logger.info(f"Found {len(cards)} items with selector {selector}")
                    break
            
            if not cards:
                logger.error("No items found with any selector")
                return []
            
            # Process found cards
            for card in cards:
                try:
                    # Try different title selectors
                    name = None
                    for title_selector in ['h3', '.title', '.rashi-title', 'h2']:
                        name_elem = card.select_one(title_selector)
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                            break
                    
                    # Try different description selectors
                    desc = None
                    for desc_selector in ['.desc', '.description', '.prediction', 'p']:
                        desc_elem = card.select_one(desc_selector)
                        if desc_elem:
                            desc = desc_elem.get_text(strip=True)
                            break
                    
                    if name and desc:
                        items.append({
                            'name': name,
                            'prediction': desc
                        })
                        logger.info(f"Found item: {name}")
                except Exception as e:
                    logger.warning(f"Error parsing card: {str(e)}")
                    continue
            
            logger.info(f"Found {len(items)} rashifal items")
            
            # Log first item for debugging
            if items:
                logger.info(f"Sample item - Name: {items[0]['name']}, Prediction: {items[0]['prediction'][:50]}...")
            else:
                logger.error("No items found in the page")
                return []
            
            logger.info(f"Extracted {len(items)} valid rashifal items")
            
            # Log the first item for debugging
            if items:
                logger.info(f"Sample item - Name: {items[0].get('name')}, Prediction: {items[0].get('prediction')[:50]}...")
            else:
                logger.error("No items were extracted from the page")
                logger.debug(f"Page source: {driver.page_source[:500]}...")
                return []
            
            # Process items
            for item in items:
                try:
                    nepali_name = item.get('name')
                    prediction = item.get('prediction')
                    
                    if not all([nepali_name, prediction]):
                        logger.warning("Missing name or prediction")
                        continue
                    
                    # Find matching sign
                    sign = None
                    english_name = None
                    for s, info in ZODIAC_SIGNS.items():
                        if info['nepali'] == nepali_name:
                            sign = s
                            english_name = info['english']
                            break
                    
                    if not sign:
                        logger.warning(f"Could not map rashifal name: {nepali_name}")
                        continue
                    
                    # Create rashifal data
                    rashifal_data = {
                        "sign": sign,
                        "prediction": prediction,
                        "date": today,
                        "nepali_name": nepali_name,
                        "english_name": english_name,
                        "sign_index": ZODIAC_SIGNS[sign]['index'],
                        "prediction_english": None,
                        "lucky_number": None,
                        "lucky_color": None
                    }
                    
                    # Save to database if session provided
                    if db is not None:
                        try:
                            saved_data = rashifal_crud.upsert(db=db, obj_in=rashifal_data)
                            if saved_data:
                                logger.info(f"Successfully saved rashifal for {sign}")
                            else:
                                logger.error(f"Failed to save rashifal for {sign}")
                        except Exception as e:
                            logger.error(f"Database error while saving rashifal for {sign}: {str(e)}")
                    
                    # Add to results regardless of database save
                    results.append(rashifal_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing rashifal item: {str(e)}")
                    continue
            
        finally:
            # Always close the browser
            driver.quit()
        
        if not results:
            logger.error("No rashifal data was successfully scraped and saved")
        else:
            logger.info(f"Successfully scraped and saved {len(results)} rashifal entries")
        
        return results
    
    except Exception as e:
        logger.error(f"Unexpected error while scraping rashifal: {str(e)}")
        return []

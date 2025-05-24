import httpx
from bs4 import BeautifulSoup
from typing import Dict, List
from datetime import datetime
import logging
import re
from sqlmodel import Session

from database.crud import metal_price_crud

logger = logging.getLogger(__name__)

async def scrape_metals(db: Session) -> List[Dict]:
    """
    Scrape daily metal prices (gold/silver) from Ashesh.com.np.
    
    Args:
        db: Database session
        
    Returns:
        List of metal price data dictionaries
    """
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    # Dictionary to store consolidated prices by metal type
    metal_prices_by_type = {}
    
    try:
        # Using Ashesh.com.np gold widget
        url = "https://www.ashesh.com.np/gold/widget.php?api=422253p432&header_color=0077e5"
        
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
            
            # Find all metal items
            items = soup.select(".country")
            
            if not items:
                logger.warning("Could not find metal items on the page")
                return []
            
            # Define metal types and their metadata
            metal_types = {
                "Gold Hallmark": {"type": "gold", "hallmark": "24K"},
                "Gold Tajabi": {"type": "gold", "hallmark": "Tejabi"},
                "Silver": {"type": "silver", "hallmark": None}
            }
            
            # Process each item
            for item in items:
                try:
                    name_div = item.select_one(".name")
                    price_div = item.select_one(".rate_buying")
                    unit_div = item.select_one(".unit")
                    
                    if not all([name_div, price_div, unit_div]):
                        continue
                    
                    name = name_div.text.strip()
                    price = float(price_div.text.strip().replace(",", ""))
                    unit = unit_div.text.strip().lower()
                    
                    # Find the corresponding metal type
                    metal_info = None
                    for key, info in metal_types.items():
                        if key in name:
                            metal_info = info
                            break
                    
                    if not metal_info:
                        continue
                    
                    # Store all prices for each metal type to consolidate later
                    if metal_info["type"] not in metal_prices_by_type:
                        metal_prices_by_type[metal_info["type"]] = {
                            "hallmark": metal_info["hallmark"],
                            "date": scrape_date
                        }
                    
                    # Store prices based on unit
                    if "tola" in unit:
                        metal_prices_by_type[metal_info["type"]]["price_per_tola"] = price
                    elif "gram" in unit:
                        metal_prices_by_type[metal_info["type"]]["price_per_10_grams"] = price
                
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error parsing metal data: {str(e)}")
            
            # Process consolidated data
            for metal_type, data in metal_prices_by_type.items():
                try:
                    # Skip incomplete data
                    if "price_per_tola" not in data:
                        # If we only have price_per_10_grams, calculate an estimated tola price
                        # 1 tola = 11.66 grams, so price_per_tola ≈ price_per_10_grams * (11.66/10)
                        if "price_per_10_grams" in data:
                            data["price_per_tola"] = round(data["price_per_10_grams"] * 1.166, 2)
                        else:
                            continue
                    
                    if "price_per_10_grams" not in data:
                        # If we only have price_per_tola, calculate an estimated gram price
                        # price_per_10_grams ≈ price_per_tola * (10/11.66)
                        data["price_per_10_grams"] = round(data["price_per_tola"] / 1.166, 2)
                    
                    metal_data = {
                        "metal_type": metal_type,
                        "hallmark": data["hallmark"],
                        "price_per_tola": data["price_per_tola"],
                        "price_per_10_grams": data["price_per_10_grams"],
                        "date": data["date"]
                    }
                    
                    # Save to database and results
                    metal_price_crud.upsert(db=db, obj_in=metal_data)
                    results.append(metal_data)
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error processing metal data: {str(e)}")
            
        return results
    
    except Exception as e:
        logger.error(f"Error scraping metal prices: {str(e)}")
        return []

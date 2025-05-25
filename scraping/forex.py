import httpx
from bs4 import BeautifulSoup
from typing import Dict, List
from datetime import datetime
import logging
from sqlmodel import Session

from database.crud import forex_rate_crud

logger = logging.getLogger(__name__)

async def scrape_forex(db: Session) -> List[Dict]:
    """
    Scrape daily forex rates from Nepal Rastra Bank.
    
    Args:
        db: Database session
        
    Returns:
        List of forex rate data dictionaries
    """
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # Using Nepal Rastra Bank website
        url = "https://www.nrb.org.np/forex/"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Try multiple possible selectors for forex tables
            forex_table = soup.select_one("table.forex-table, table.currency-rates, table.table-forex, table.table-responsive")
            
            # If not found, try any table on the page
            if not forex_table:
                tables = soup.select("table")
                if tables:
                    # Use the table with the most rows as it's likely the forex table
                    forex_table = max(tables, key=lambda t: len(t.select("tr")))
            
            if not forex_table:
                logger.warning("Could not find forex rates table on the page - site structure may have changed")
                # Instead of returning empty, try a fallback approach
                logger.info("Attempting to scrape forex data from alternate source")
                
                # Try an alternate method if primary fails
                # This could be another source or alternative parsing method
                try:
                    # Try to find any data that looks like forex rates (e.g., currency codes with numbers)
                    potential_rates = []
                    for element in soup.select("*"):
                        text = element.get_text().strip()
                        # Look for text that might contain currency rates (USD, EUR, etc. followed by numbers)
                        if any(code in text for code in ["USD", "EUR", "GBP", "JPY", "CHF"]) and any(char.isdigit() for char in text):
                            potential_rates.append(element)
                    
                    if potential_rates:
                        logger.info(f"Found {len(potential_rates)} potential forex elements")
                        # Process these potential rates
                        # Add code here to handle these elements
                
                except Exception as e:
                    logger.warning(f"Fallback forex scraping also failed: {str(e)}")
                
                return []
                
            rows = forex_table.select("tr")
            
            # Skip header row
            for row in rows[1:]:
                cells = row.select("td")
                
                if len(cells) >= 4:
                    try:
                        currency_info = cells[0].text.strip()
                        # Extract currency code and name
                        if "(" in currency_info and ")" in currency_info:
                            currency_name = currency_info.split("(")[0].strip()
                            currency_code = currency_info.split("(")[1].split(")")[0].strip()
                        else:
                            currency_name = currency_info
                            currency_code = currency_info[:3]  # Assume first 3 chars are the code
                        
                        unit = cells[1].text.strip()
                        buy_rate = float(cells[2].text.strip().replace(",", ""))
                        sell_rate = float(cells[3].text.strip().replace(",", ""))
                        
                        # Normalize rates to 1 unit if needed
                        if unit.isdigit() and int(unit) > 1:
                            unit_value = int(unit)
                            buy_rate = buy_rate / unit_value
                            sell_rate = sell_rate / unit_value
                        
                        forex_data = {
                            "currency_code": currency_code,
                            "currency_name": currency_name,
                            "buy_rate": buy_rate,
                            "sell_rate": sell_rate,
                            "date": today
                        }
                        
                        # Save to database
                        forex_rate_crud.upsert(db=db, obj_in=forex_data)
                        results.append(forex_data)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing row data: {str(e)}")
            
        return results
    
    except Exception as e:
        logger.error(f"Error scraping forex rates: {str(e)}")
        return []

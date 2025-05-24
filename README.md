# Nepali Data API

A full-featured FastAPI backend that scrapes and serves data from various Nepali websites including calendar, events, rashifal (horoscope), and market prices.

## Features

1. **Daily Data Scraping from Nepali Websites:**
   - Nepali Month Calendar (e.g., NepaliPatro)
   - Nepali Events (e.g., government holidays)
   - Rashifal (daily horoscope for 12 zodiac signs)
   - Kalimati Vegetable Market Prices
   - Daily Metal Prices (gold/silver)
   - Daily Forex Rates (NPR vs USD, INR, etc.)

2. **Data Storage in SQLite:**
   - Uses SQLModel for ORM (created by FastAPI's author)
   - Well-defined data models for different types of data

3. **Automatic Daily Scraping:**
   - Background tasks run every 24 hours
   - Initial scraping on application startup

4. **Modern REST API Endpoints:**
   - `GET /today` - Get today's Nepali date with detailed information
   - `GET /calendar/{year}/{month}` - Get calendar days for a specific month
   - `GET /events/{year}` - Get events for a specific year
   - `GET /rashifal/{sign}` - Get daily horoscope for a specific zodiac sign
   - `GET /prices/vegetables` - Get latest vegetable prices
   - `GET /prices/metals` - Get latest metal prices (gold/silver)
   - `GET /prices/forex` - Get latest forex rates
   - Auto-generated Swagger docs at `/docs`

## Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLModel**: SQL databases in Python, designed for simplicity and compatibility
- **SQLite**: Lightweight disk-based database
- **httpx**: Fully featured HTTP client for making async requests
- **BeautifulSoup4**: Library for parsing HTML and XML documents
- **Uvicorn**: ASGI server for running the FastAPI application
- **Python AsyncIO**: For efficient background scraping tasks

## Project Structure

```
project/
│
├── main.py              # FastAPI app entrypoint
├── database/
│   ├── __init__.py      # Database connection setup
│   ├── models.py        # SQLModel classes
│   └── crud.py          # Data fetching/insert logic
├── scraping/
│   ├── __init__.py
│   ├── rashifal.py      # Rashifal scraper
│   ├── vegetables.py    # Vegetable prices scraper
│   ├── metals.py        # Metal prices scraper
│   ├── forex.py         # Forex rates scraper
│   ├── calendar.py      # Calendar scraper
│   └── events.py        # Events scraper
├── scheduler.py         # Background scraping setup
├── requirements.txt     # Project dependencies
└── README.md            # Project documentation
```

## Installation & Running

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   uvicorn main:app --reload
   ```
4. Open `http://localhost:8000/docs` in your browser to view API documentation

## Notes

- The application automatically creates an SQLite database file (`nepali_data.db`) on startup
- Data is refreshed every 24 hours in the background
- If data is not available when an endpoint is called, the system will attempt to scrape it on-demand

## Customization

The scraping modules are designed to be adaptable to different websites. You may need to adjust the CSS selectors or parsing logic if the source websites change their structure.

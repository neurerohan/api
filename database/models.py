from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


class CalendarDay(SQLModel, table=True):
    """Model for Nepali calendar days."""
    id: Optional[int] = Field(default=None, primary_key=True)
    year: int
    month: int
    day: int
    nepali_date: str
    english_date: str
    weekday: str
    nepali_weekday: Optional[str] = None
    is_holiday: bool = False
    event: Optional[str] = None
    tithi: Optional[str] = None
    panchang: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    
    events: List["Event"] = Relationship(back_populates="calendar_day")


class Event(SQLModel, table=True):
    """Model for Nepali events/holidays."""
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    date: str
    year: int
    month: int
    day: int
    event_type: str  # holiday, festival, etc.
    is_public_holiday: bool = False
    calendar_day_id: Optional[int] = Field(default=None, foreign_key="calendarday.id")
    updated_at: datetime = Field(default_factory=datetime.now)
    
    calendar_day: Optional[CalendarDay] = Relationship(back_populates="events")


class Rashifal(SQLModel, table=True):
    """Model for daily horoscope (Rashifal) for zodiac signs."""
    id: Optional[int] = Field(default=None, primary_key=True)
    sign: str  # Mesh, Brish, etc.
    prediction: str
    date: str
    prediction_english: Optional[str] = None
    lucky_number: Optional[str] = None
    lucky_color: Optional[str] = None
    nepali_name: Optional[str] = None  # Nepali name of the sign (e.g., मेष)
    english_name: Optional[str] = None  # English name of the sign (e.g., Aries)
    sign_index: Optional[int] = None  # Index of the sign (1-12)
    updated_at: datetime = Field(default_factory=datetime.now)


class MetalPrice(SQLModel, table=True):
    """Model for daily metal prices (gold/silver)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    metal_type: str  # gold, silver
    price_per_tola: float
    price_per_10_grams: Optional[float] = None
    hallmark: Optional[str] = None  # 24K, 22K, etc.
    date: str
    updated_at: datetime = Field(default_factory=datetime.now)


class ForexRate(SQLModel, table=True):
    """Model for daily forex rates."""
    id: Optional[int] = Field(default=None, primary_key=True)
    currency_code: str  # USD, EUR, INR, etc.
    currency_name: str
    buy_rate: float
    sell_rate: float
    date: str
    updated_at: datetime = Field(default_factory=datetime.now)


class VegetablePrice(SQLModel, table=True):
    """Model for vegetable and fruit market prices."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    nepali_name: Optional[str] = None
    min_price: float
    max_price: float
    avg_price: float
    unit: str  # kg, piece, etc.
    date: str
    image_url: Optional[str] = None  # URL to the vegetable/fruit image
    updated_at: datetime = Field(default_factory=datetime.now)

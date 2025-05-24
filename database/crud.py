from typing import List, Optional, Type, TypeVar, Generic, Dict, Any
from sqlmodel import Session, select, SQLModel
from datetime import datetime

from .models import (
    CalendarDay, Event, Rashifal, 
    MetalPrice, ForexRate, VegetablePrice
)

T = TypeVar('T', bound=SQLModel)


class CRUDBase(Generic[T]):
    """Base CRUD operations for all models."""
    
    def __init__(self, model: Type[T]):
        self.model = model
    
    def get(self, db: Session, id: int) -> Optional[T]:
        """Get a single record by ID."""
        return db.get(self.model, id)
    
    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[T]:
        """Get multiple records with pagination."""
        statement = select(self.model).offset(skip).limit(limit)
        return db.exec(statement).all()
    
    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> T:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(self, db: Session, *, db_obj: T, obj_in: Dict[str, Any]) -> T:
        """Update an existing record."""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        
        if hasattr(db_obj, 'updated_at'):
            setattr(db_obj, 'updated_at', datetime.now())
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


# Specific CRUD implementations for each model
class CalendarCRUD(CRUDBase[CalendarDay]):
    """CRUD operations for CalendarDay model."""
    
    def get_by_date(self, db: Session, *, year: int, month: int, day: Optional[int] = None) -> List[CalendarDay]:
        """Get calendar days by year, month, and optionally day."""
        if day:
            statement = select(self.model).where(
                self.model.year == year,
                self.model.month == month,
                self.model.day == day
            )
        else:
            statement = select(self.model).where(
                self.model.year == year,
                self.model.month == month
            )
        return db.exec(statement).all()
    
    def upsert(self, db: Session, *, obj_in: Dict[str, Any]) -> CalendarDay:
        """Create or update a calendar day."""
        statement = select(self.model).where(
            self.model.year == obj_in["year"],
            self.model.month == obj_in["month"],
            self.model.day == obj_in["day"]
        )
        existing = db.exec(statement).first()
        
        if existing:
            return self.update(db=db, db_obj=existing, obj_in=obj_in)
        else:
            return self.create(db=db, obj_in=obj_in)


class EventCRUD(CRUDBase[Event]):
    """CRUD operations for Event model."""
    
    def get_by_year(self, db: Session, *, year: int) -> List[Event]:
        """Get events by year."""
        statement = select(self.model).where(self.model.year == year)
        return db.exec(statement).all()
    
    def get_by_date(self, db: Session, *, year: int, month: int, day: Optional[int] = None) -> List[Event]:
        """Get events by date."""
        if day:
            statement = select(self.model).where(
                self.model.year == year,
                self.model.month == month,
                self.model.day == day
            )
        else:
            statement = select(self.model).where(
                self.model.year == year,
                self.model.month == month
            )
        return db.exec(statement).all()
    
    def upsert(self, db: Session, *, obj_in: Dict[str, Any]) -> Event:
        """Create or update an event."""
        statement = select(self.model).where(
            self.model.title == obj_in["title"],
            self.model.date == obj_in["date"]
        )
        existing = db.exec(statement).first()
        
        if existing:
            return self.update(db=db, db_obj=existing, obj_in=obj_in)
        else:
            return self.create(db=db, obj_in=obj_in)


class RashifalCRUD(CRUDBase[Rashifal]):
    """CRUD operations for Rashifal model."""
    
    def get_by_sign(self, db: Session, *, sign: str) -> Optional[Rashifal]:
        """Get latest rashifal by zodiac sign."""
        statement = select(self.model).where(
            self.model.sign == sign
        ).order_by(self.model.updated_at.desc())
        return db.exec(statement).first()
    
    def upsert(self, db: Session, *, obj_in: Dict[str, Any]) -> Rashifal:
        """Create or update a rashifal."""
        statement = select(self.model).where(
            self.model.sign == obj_in["sign"],
            self.model.date == obj_in["date"]
        )
        existing = db.exec(statement).first()
        
        if existing:
            return self.update(db=db, db_obj=existing, obj_in=obj_in)
        else:
            return self.create(db=db, obj_in=obj_in)


class MetalPriceCRUD(CRUDBase[MetalPrice]):
    """CRUD operations for MetalPrice model."""
    
    def get_latest(self, db: Session) -> List[MetalPrice]:
        """Get the latest metal prices."""
        # Get the most recent date
        date_statement = select(self.model.date).order_by(self.model.updated_at.desc())
        latest_date = db.exec(date_statement).first()
        
        if latest_date:
            statement = select(self.model).where(self.model.date == latest_date)
            return db.exec(statement).all()
        return []
    
    def upsert(self, db: Session, *, obj_in: Dict[str, Any]) -> MetalPrice:
        """Create or update a metal price."""
        statement = select(self.model).where(
            self.model.metal_type == obj_in["metal_type"],
            self.model.hallmark == obj_in.get("hallmark"),
            self.model.date == obj_in["date"]
        )
        existing = db.exec(statement).first()
        
        if existing:
            return self.update(db=db, db_obj=existing, obj_in=obj_in)
        else:
            return self.create(db=db, obj_in=obj_in)


class ForexRateCRUD(CRUDBase[ForexRate]):
    """CRUD operations for ForexRate model."""
    
    def get_latest(self, db: Session) -> List[ForexRate]:
        """Get the latest forex rates."""
        # Get the most recent date
        date_statement = select(self.model.date).order_by(self.model.updated_at.desc())
        latest_date = db.exec(date_statement).first()
        
        if latest_date:
            statement = select(self.model).where(self.model.date == latest_date)
            return db.exec(statement).all()
        return []
    
    def upsert(self, db: Session, *, obj_in: Dict[str, Any]) -> ForexRate:
        """Create or update a forex rate."""
        statement = select(self.model).where(
            self.model.currency_code == obj_in["currency_code"],
            self.model.date == obj_in["date"]
        )
        existing = db.exec(statement).first()
        
        if existing:
            return self.update(db=db, db_obj=existing, obj_in=obj_in)
        else:
            return self.create(db=db, obj_in=obj_in)


class VegetablePriceCRUD(CRUDBase[VegetablePrice]):
    """CRUD operations for VegetablePrice model."""
    
    def get_latest(self, db: Session) -> List[VegetablePrice]:
        """Get the latest vegetable prices."""
        # Get the most recent date
        date_statement = select(self.model.date).order_by(self.model.updated_at.desc())
        latest_date = db.exec(date_statement).first()
        
        if latest_date:
            statement = select(self.model).where(self.model.date == latest_date)
            return db.exec(statement).all()
        return []
    
    def upsert(self, db: Session, *, obj_in: Dict[str, Any]) -> VegetablePrice:
        """Create or update a vegetable price."""
        statement = select(self.model).where(
            self.model.name == obj_in["name"],
            self.model.date == obj_in["date"]
        )
        existing = db.exec(statement).first()
        
        if existing:
            return self.update(db=db, db_obj=existing, obj_in=obj_in)
        else:
            return self.create(db=db, obj_in=obj_in)


# Create instances for each model
calendar_crud = CalendarCRUD(CalendarDay)
event_crud = EventCRUD(Event)
rashifal_crud = RashifalCRUD(Rashifal)
metal_price_crud = MetalPriceCRUD(MetalPrice)
forex_rate_crud = ForexRateCRUD(ForexRate)
vegetable_price_crud = VegetablePriceCRUD(VegetablePrice)

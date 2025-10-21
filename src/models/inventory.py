from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CONSUMED = "consumed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Product(BaseModel):
    id: str
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    unit_price: float = Field(..., gt=0)
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Inventory(BaseModel):
    id: str
    product_id: str
    store_id: str
    available_quantity: int = Field(..., ge=0)
    reserved_quantity: int = Field(..., ge=0)
    total_quantity: int = Field(..., ge=0)
    version: int = Field(default=1, ge=1)
    last_updated: datetime
    
    @validator('total_quantity')
    def validate_total_quantity(cls, v, values):
        available = values.get('available_quantity', 0)
        reserved = values.get('reserved_quantity', 0)
        if v != available + reserved:
            raise ValueError('Total quantity must equal available + reserved')
        return v
    
    @property
    def is_available(self) -> bool:
        return self.available_quantity > 0
    
    class Config:
        from_attributes = True


class Reservation(BaseModel):
    id: str
    order_id: str
    product_id: str
    store_id: str
    quantity: int = Field(..., gt=0)
    status: ReservationStatus
    expires_at: datetime
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    class Config:
        from_attributes = True


class StockUpdate(BaseModel):
    product_id: str
    store_id: str
    quantity_change: int
    reason: str = Field(..., min_length=1, max_length=200)
    reference_id: Optional[str] = None


class ReservationRequest(BaseModel):
    order_id: str
    product_id: str
    store_id: str
    quantity: int = Field(..., gt=0)
    ttl_minutes: int = Field(default=15, ge=1, le=60)


class ReservationResponse(BaseModel):
    reservation_id: str
    status: ReservationStatus
    expires_at: datetime
    message: str


class StockLevel(BaseModel):
    product_id: str
    store_id: str
    available: int
    reserved: int
    total: int
    last_updated: datetime


class InventoryEvent(BaseModel):
    event_type: str
    product_id: str
    store_id: str
    quantity_before: int
    quantity_after: int
    change_reason: str
    timestamp: datetime
    correlation_id: Optional[str] = None

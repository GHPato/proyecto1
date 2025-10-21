from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class StoreStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class Store(BaseModel):
    id: str
    name: str = Field(..., min_length=1, max_length=200)
    address: str = Field(..., min_length=1, max_length=500)
    city: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)
    zip_code: str = Field(..., min_length=1, max_length=20)
    phone: Optional[str] = None
    email: Optional[str] = None
    status: StoreStatus = StoreStatus.ACTIVE
    timezone: str = Field(default="UTC", min_length=1, max_length=50)
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class StoreInventory(BaseModel):
    store_id: str
    product_id: str
    available_quantity: int
    reserved_quantity: int
    total_quantity: int
    last_updated: datetime
    sync_version: int

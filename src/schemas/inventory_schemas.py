from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
import re


class ReservationRequestSchema(BaseModel):
    order_id: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Unique order ID from the client"
    )
    product_id: str = Field(
        ..., 
        min_length=36, 
        max_length=36,
        description="ID of the product to reserve"
    )
    store_id: str = Field(
        ..., 
        min_length=36, 
        max_length=36,
        description="ID of the store"
    )
    quantity: int = Field(
        ..., 
        gt=0, 
        le=100,
        description="Quantity to reserve (1-100)"
    )
    ttl_minutes: int = Field(
        ..., 
        ge=1, 
        le=60,
        description="Reservation time-to-live in minutes (1-60)"
    )

    @validator('order_id')
    def validate_order_id(cls, v):
        if not re.match(r'^[A-Z0-9-_]+$', v):
            raise ValueError('Order ID must contain only uppercase letters, numbers, hyphens and underscores')
        return v

    @validator('product_id', 'store_id')
    def validate_uuid_format(cls, v):
        if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', v):
            raise ValueError('ID must be a valid UUID')
        return v

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        if v > 100:
            raise ValueError('Quantity cannot be greater than 100')
        return v

    class Config:
        schema_extra = {
            "example": {
                "order_id": "ORDER-12345",
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "store_id": "123e4567-e89b-12d3-a456-426614174001",
                "quantity": 2,
                "ttl_minutes": 15
            }
        }


class ReservationConfirmSchema(BaseModel):
    reservation_id: str = Field(
        ..., 
        min_length=36, 
        max_length=36,
        description="ID of the reservation to confirm"
    )
    order_id: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Order ID (must match the reservation)"
    )

    @validator('reservation_id')
    def validate_reservation_id(cls, v):
        if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', v):
            raise ValueError('Reservation ID must be a valid UUID')
        return v

    @validator('order_id')
    def validate_order_id(cls, v):
        if not re.match(r'^[A-Z0-9-_]+$', v):
            raise ValueError('Order ID must contain only uppercase letters, numbers, hyphens and underscores')
        return v

    class Config:
        schema_extra = {
            "example": {
                "reservation_id": "123e4567-e89b-12d3-a456-426614174002",
                "order_id": "ORDER-12345"
            }
        }


class ReservationConsumeSchema(BaseModel):
    reservation_id: str = Field(
        ..., 
        min_length=36, 
        max_length=36,
        description="ID of the reservation to consume"
    )

    @validator('reservation_id')
    def validate_reservation_id(cls, v):
        if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', v):
            raise ValueError('Reservation ID must be a valid UUID')
        return v

    class Config:
        schema_extra = {
            "example": {
                "reservation_id": "123e4567-e89b-12d3-a456-426614174002"
            }
        }


class StockUpdateSchema(BaseModel):
    product_id: str = Field(
        ..., 
        min_length=36, 
        max_length=36,
        description="ID of the product"
    )
    store_id: str = Field(
        ..., 
        min_length=36, 
        max_length=36,
        description="ID of the store"
    )
    quantity: int = Field(
        ..., 
        description="Quantity to add or subtract from stock"
    )
    operation: str = Field(
        ..., 
        description="Operation to perform: 'add' or 'subtract'"
    )

    @validator('product_id', 'store_id')
    def validate_uuid_format(cls, v):
        if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', v):
            raise ValueError('ID must be a valid UUID')
        return v

    @validator('operation')
    def validate_operation(cls, v):
        if v not in ['add', 'subtract']:
            raise ValueError('Operation must be "add" or "subtract"')
        return v

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        if v > 1000:
            raise ValueError('Quantity cannot be greater than 1000')
        return v

    class Config:
        schema_extra = {
            "example": {
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "store_id": "123e4567-e89b-12d3-a456-426614174001",
                "quantity": 10,
                "operation": "add"
            }
        }


class ProductCreateSchema(BaseModel):
    sku: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Unique product SKU"
    )
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Product name"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000,
        description="Product description"
    )
    category: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Product category"
    )
    unit_price: float = Field(
        ..., 
        gt=0,
        description="Product unit price"
    )

    @validator('sku')
    def validate_sku(cls, v):
        if not re.match(r'^[A-Z0-9-_]+$', v):
            raise ValueError('SKU must contain only uppercase letters, numbers, hyphens and underscores')
        return v

    @validator('unit_price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        if v > 1000000:
            raise ValueError('Price cannot be greater than 1,000,000')
        return v

    class Config:
        schema_extra = {
            "example": {
                "sku": "LAPTOP-001",
                "name": "MacBook Pro 16-inch",
                "description": "Apple MacBook Pro with M2 chip",
                "category": "Electronics",
                "unit_price": 2499.99
            }
        }
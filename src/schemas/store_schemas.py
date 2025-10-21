from pydantic import BaseModel, Field, validator
import re


class StoreCreateSchema(BaseModel):
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Store name"
    )
    address: str = Field(
        ..., 
        min_length=1, 
        max_length=500,
        description="Store address"
    )
    city: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Store city"
    )
    country: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Store country"
    )
    zip_code: str = Field(
        ..., 
        min_length=1, 
        max_length=20,
        description="Store zip code"
    )

    @validator('name', 'city', 'country')
    def validate_text_fields(cls, v):
        if not re.match(r'^[a-zA-Z0-9\s\-\.]+$', v):
            raise ValueError('Field must contain only letters, numbers, spaces, hyphens and dots')
        return v

    @validator('zip_code')
    def validate_zip_code(cls, v):
        if not re.match(r'^[A-Z0-9\s\-]+$', v):
            raise ValueError('zip code must contain only uppercase letters, numbers, spaces and hyphens')
        return v

    class Config:
        schema_extra = {
            "example": {
                "name": "Downtown Store",
                "address": "Main St 123",
                "city": "Madrid",
                "country": "Spain",
                "zip_code": "28001"
            }
        }

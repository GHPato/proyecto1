from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class Event(BaseEntity):
    event_type: str
    aggregate_id: str
    aggregate_type: str
    payload: dict
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    version: int = 1
    
    class Config:
        from_attributes = True

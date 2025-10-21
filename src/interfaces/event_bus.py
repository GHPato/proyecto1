from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime


class EventBus(ABC):
    
    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        pass
    
    
    @abstractmethod
    async def close(self) -> None:
        pass


class LockManager(ABC):
    
    @abstractmethod
    async def acquire_lock(self, key: str, ttl: int = 30) -> bool:
        pass
    
    @abstractmethod
    async def release_lock(self, key: str) -> None:
        pass

class CacheManager(ABC):    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass


class EventMessage:
    
    def __init__(
        self,
        event_type: str,
        payload: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        source: str = "inventory_service",
        version: str = "1.0"
    ):
        self.event_type = event_type
        self.payload = payload
        self.timestamp = timestamp or datetime.utcnow()
        self.source = source
        self.version = version
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "version": self.version
        }
    

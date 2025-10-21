from src.interfaces.event_bus import EventBus, LockManager, CacheManager
from src.implementations.redis_event_bus import (
    RedisEventBus, RedisLockManager, RedisCacheManager
)


class EventBusConfig:    
    def __init__(self):
        pass
    
    def get_event_bus(self) -> EventBus:
        return RedisEventBus()
    
    def get_lock_manager(self, event_bus: EventBus) -> LockManager:
        if isinstance(event_bus, RedisEventBus):
            return RedisLockManager(event_bus.redis)
        else:
            raise ValueError("Redis lock manager requires Redis event bus")
    
    def get_cache_manager(self, event_bus: EventBus) -> CacheManager:
        if isinstance(event_bus, RedisEventBus):
            return RedisCacheManager(event_bus.redis)
        else:
            raise ValueError("Redis cache manager requires Redis event bus")


event_bus_config = EventBusConfig()

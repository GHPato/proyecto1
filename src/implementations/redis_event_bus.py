import json
from typing import Dict, Any, Optional, AsyncGenerator
from src.interfaces.event_bus import EventBus, LockManager, CacheManager
from src.utils.logging import get_logger
import redis.asyncio as redis
from config.settings import settings

logger = get_logger(__name__)


class RedisEventBus(EventBus):
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Connected to Redis Event Bus")
        except Exception as e:
            logger.error(f"Failed to connect to Redis Event Bus: {e}")
            raise
    
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        try:
            await self.redis.publish(topic, json.dumps(message))
            logger.debug(f"Published message to topic {topic}")
        except Exception as e:
            logger.error(f"Failed to publish message to topic {topic}: {e}")
            raise
    
    
    async def close(self) -> None:
        if self.redis:
            await self.redis.close()
            logger.info("Redis Event Bus connection closed")


class RedisLockManager(LockManager):
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def acquire_lock(self, key: str, ttl: int = 30) -> bool:
        try:
            return await self.redis.set(key, "locked", nx=True, ex=ttl)
        except Exception as e:
            logger.error(f"Redis lock acquisition failed for key {key}: {e}")
            return False
    
    async def release_lock(self, key: str) -> None:
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis lock release failed for key {key}: {e}")


class RedisCacheManager(CacheManager):
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[str]:
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis get operation failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if ttl:
                await self.redis.setex(key, ttl, value)
            else:
                await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Redis set operation failed for key {key}: {e}")
            raise
    
    async def delete(self, key: str) -> None:
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete operation failed for key {key}: {e}")
            raise
    
    async def exists(self, key: str) -> bool:
        try:
            return await self.redis.exists(key)
        except Exception as e:
            logger.error(f"Redis exists operation failed for key {key}: {e}")
            return False

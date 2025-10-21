import redis.asyncio as redis
import json
from typing import Optional, Any, Dict
from config.settings import settings
import structlog

logger = structlog.get_logger()


class RedisClient:
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
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
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
    
    async def get(self, key: str) -> Optional[str]:
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis get operation failed for key {key}: {e}")
            return None
    
    async def get_json(self, key: str) -> Optional[Dict]:
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def delete(self, key: str):
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete failed for key {key}: {e}")
            raise
    
    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key)
    
    async def publish(self, channel: str, message: Dict):
        try:
            await self.redis.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Redis publish failed for channel {channel}: {e}")
            raise
    
    async def subscribe(self, channel: str):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
    
    async def acquire_lock(self, key: str, ttl: int = 30) -> bool:
        try:
            return await self.redis.set(key, "locked", nx=True, ex=ttl)
        except Exception as e:
            logger.error(f"Redis lock acquisition failed for key {key}: {e}")
            return False
    
    async def release_lock(self, key: str):
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis lock release failed for key {key}: {e}")


redis_client = RedisClient()

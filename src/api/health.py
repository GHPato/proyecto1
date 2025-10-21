from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from src.utils.database import get_db
from src.config.event_bus_config import event_bus_config
from src.utils.prometheus import prometheus_metrics
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "inventory-management"
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute("SELECT 1")
        try:
            event_bus = event_bus_config.get_event_bus()
            await event_bus.connect()
            redis_connected = True
            await event_bus.close()
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}")
            redis_connected = False
        
        if redis_connected:
            return {
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "connected",
                "redis": "connected"
            }
        else:
            logger.warning("Redis ping failed - service degraded")
            return {
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "connected",
                "redis": "disconnected"
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/metrics")
async def get_metrics():
    return prometheus_metrics.get_metrics()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from src.utils.database import init_db
from src.config.event_bus_config import event_bus_config
from src.utils.logging import configure_logging, get_logger
from src.utils.middleware import LoggingMiddleware, MetricsMiddleware
from src.utils.prometheus import prometheus_metrics
from src.api import inventory, stores, health
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)
    
    logger.info("Starting application")
    
    await init_db()
    
    event_bus = event_bus_config.get_event_bus()
    await event_bus.connect()
    logger.info("Event bus (Redis) connected successfully")
    
    logger.info("Application started successfully")
    
    yield
    
    logger.info("Shutting down application")
    
    await event_bus.close()
    logger.info("Event bus connection closed")
    
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Distributed Inventory Management System",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware, prometheus_client=prometheus_metrics)

app.include_router(inventory.router)
app.include_router(stores.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "message": "Inventory Management System API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

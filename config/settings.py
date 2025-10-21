from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    app_name: str = "Inventory Management System"
    app_version: str = "1.0.0"
    debug: bool = False
    
    database_url: str = "sqlite:///./data/inventory.db"
    redis_url: str = "redis://localhost:6379"
    
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    reservation_ttl_minutes: int = 15
    max_reservation_quantity: int = 1000
    
    sync_interval_minutes: int = 15
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    prometheus_port: int = 8001
    health_check_interval: int = 30
    
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

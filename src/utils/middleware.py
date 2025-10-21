import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        start_time = time.time()
        
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            correlation_id=correlation_id,
            client_ip=request.client.host if request.client else None
        )
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=process_time,
            correlation_id=correlation_id
        )
        
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, prometheus_client):
        super().__init__(app)
        self.prometheus_client = prometheus_client
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        self.prometheus_client.record_request_metrics(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=process_time
        )
        
        return response

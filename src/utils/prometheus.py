from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from typing import Dict, Any
import time


class PrometheusMetrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        
        self.request_count = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.active_connections = Gauge(
            'active_connections',
            'Number of active connections',
            registry=self.registry
        )
        
        self.inventory_stock_level = Gauge(
            'inventory_stock_level',
            'Current stock level',
            ['product_id', 'store_id'],
            registry=self.registry
        )
        
        self.reservation_count = Counter(
            'inventory_reservations_total',
            'Total inventory reservations',
            ['status'],
            registry=self.registry
        )
        
        self.sync_operations = Counter(
            'store_sync_operations_total',
            'Total store sync operations',
            ['store_id', 'status'],
            registry=self.registry
        )
    
    def record_request_metrics(self, method: str, endpoint: str, status_code: int, duration: float):
        self.request_count.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def update_stock_level(self, product_id: str, store_id: str, quantity: int):
        self.inventory_stock_level.labels(
            product_id=product_id,
            store_id=store_id
        ).set(quantity)
    
    def record_reservation(self, status: str):
        self.reservation_count.labels(status=status).inc()
    
    def record_sync_operation(self, store_id: str, status: str):
        self.sync_operations.labels(store_id=store_id, status=status).inc()
    
    def get_metrics(self) -> str:
        return generate_latest(self.registry).decode('utf-8')


prometheus_metrics = PrometheusMetrics()

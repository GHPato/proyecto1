from typing import Optional
from src.constants import *


class InventoryServiceBaseException(Exception):    
    def __init__(self, status_code: int, error_type: str, message: str, error_code: Optional[str] = None):
        self.status_code = status_code
        self.error_type = error_type
        self.error_msg = message
        self.error_code = error_code
        super().__init__(self.error_msg)


class BusinessError(InventoryServiceBaseException):    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            status_code=RESP_BAD_REQUEST,
            error_type=BUSINESS_ERROR,
            message=message,
            error_code=error_code
        )


class ValidationError(InventoryServiceBaseException):    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            status_code=RESP_UNPROCESSABLE_ENTITY,
            error_type=VALIDATION_ERROR,
            message=message,
            error_code=error_code
        )


class NotFoundError(InventoryServiceBaseException):    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            status_code=RESP_NOT_FOUND,
            error_type=NOT_FOUND_ERROR,
            message=message,
            error_code=error_code
        )


class ConflictError(InventoryServiceBaseException):    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            status_code=RESP_CONFLICT,
            error_type=CONFLICT_ERROR,
            message=message,
            error_code=error_code
        )


class ServerError(InventoryServiceBaseException):    
    def __init__(self, message: str = "Internal server error", error_code: Optional[str] = None):
        super().__init__(
            status_code=RESP_INTERNAL_SERVER_ERROR,
            error_type=SERVER_ERROR,
            message=message,
            error_code=error_code
        )


class ExternalServiceError(InventoryServiceBaseException):    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(
            status_code=RESP_SERVICE_UNAVAILABLE,
            error_type=EXTERNAL_SERVICE_ERROR,
            message=message,
            error_code=error_code
        )


class InsufficientStockError(BusinessError):
    def __init__(self, available: int, requested: int):
        super().__init__(
            message=f"Insufficient stock available. Available: {available}, Requested: {requested}",
            error_code=INSUFFICIENT_STOCK
        )


class InventoryNotFoundError(NotFoundError):
    def __init__(self, product_id: str, store_id: str):
        super().__init__(
            message=f"Inventory not found for product {product_id} in store {store_id}",
            error_code=INVENTORY_NOT_FOUND
        )


class ProductNotFoundError(NotFoundError):
    def __init__(self, product_id: str):
        super().__init__(
            message=f"Product not found: {product_id}",
            error_code=PRODUCT_NOT_FOUND
        )


class StoreNotFoundError(NotFoundError):
    def __init__(self, store_id: str):
        super().__init__(
            message=f"Store not found: {store_id}",
            error_code=STORE_NOT_FOUND
        )


class ReservationNotFoundError(NotFoundError):
    def __init__(self, reservation_id: str):
        super().__init__(
            message=f"Reservation not found: {reservation_id}",
            error_code=RESERVATION_NOT_FOUND
        )


class ReservationExpiredError(ConflictError):
    def __init__(self, reservation_id: str):
        super().__init__(
            message=f"Reservation {reservation_id} has expired",
            error_code=RESERVATION_EXPIRED
        )


class ReservationAlreadyConfirmedError(ConflictError):
    def __init__(self, reservation_id: str):
        super().__init__(
            message=f"Reservation {reservation_id} is already confirmed",
            error_code=RESERVATION_ALREADY_CONFIRMED
        )


class OptimisticLockConflictError(ConflictError):
    def __init__(self, resource: str):
        super().__init__(
            message=f"Optimistic lock conflict on {resource}. Resource was modified by another operation",
            error_code=OPTIMISTIC_LOCK_CONFLICT
        )


class DistributedLockFailedError(ExternalServiceError):
    def __init__(self, lock_key: str):
        super().__init__(
            message=f"Could not acquire distributed lock: {lock_key}",
            error_code=DISTRIBUTED_LOCK_FAILED
        )


class InvalidReservationStatusError(BusinessError):
    def __init__(self, reservation_id: str, current_status: str, expected_status: str):
        super().__init__(
            message=f"Invalid reservation status for {reservation_id}. Current: {current_status}, Expected: {expected_status}",
            error_code=INVALID_RESERVATION_STATUS
        )

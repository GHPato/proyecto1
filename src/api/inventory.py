from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.utils.database import get_db
from src.services.inventory_service import InventoryService
from src.config.event_bus_config import event_bus_config
from src.models.inventory import (
    ReservationRequest, ReservationResponse, StockUpdate, 
    StockLevel, InventoryEvent, Product, Inventory
)
from src.schemas.inventory_schemas import (
    ReservationRequestSchema, ReservationConfirmSchema, 
    ReservationConsumeSchema, StockUpdateSchema
)
from src.utils.logging import get_logger
from src.utils.error_utils import handle_service_exception

logger = get_logger(__name__)
router = APIRouter(prefix="/inventory", tags=["inventory"])


async def get_inventory_service(db: AsyncSession = Depends(get_db)):
    event_bus = event_bus_config.get_event_bus()
    await event_bus.connect()
    
    lock_manager = event_bus_config.get_lock_manager(event_bus)
    cache_manager = event_bus_config.get_cache_manager(event_bus)
    
    return InventoryService(db, event_bus, lock_manager, cache_manager)


@router.post("/reserve", response_model=ReservationResponse)
async def reserve_stock(
    request: ReservationRequestSchema,
    service: InventoryService = Depends(get_inventory_service)
):
    try:
        reservation_request = ReservationRequest(
            order_id=request.order_id,
            product_id=request.product_id,
            store_id=request.store_id,
            quantity=request.quantity,
            ttl_minutes=request.ttl_minutes
        )
        result = await service.reserve_stock(reservation_request)
        
        logger.info(
            "Stock reservation successful",
            reservation_id=str(result.reservation_id),
            order_id=str(request.order_id)
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Stock reservation failed",
            error=str(e),
            order_id=str(request.order_id)
        )
        raise handle_service_exception(e)


@router.post("/confirm")
async def confirm_reservation(
    request: ReservationConfirmSchema,
    service: InventoryService = Depends(get_inventory_service)
):
    try:
        success = await service.confirm_reservation(request.reservation_id)
        
        if success:
            logger.info(
                "Reservation confirmed",
                reservation_id=str(request.reservation_id)
            )
            return {"message": "Reservation confirmed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to confirm reservation"
            )
            
    except Exception as e:
        logger.error(
            "Reservation confirmation failed",
            error=str(e),
            reservation_id=str(reservation_id)
        )
        raise handle_service_exception(e)


@router.post("/cancel/{reservation_id}")
async def cancel_reservation(
    reservation_id: str,
    service: InventoryService = Depends(get_inventory_service)
):
    try:
        success = await service.cancel_reservation(reservation_id)
        
        if success:
            logger.info(
                "Reservation cancelled",
                reservation_id=str(reservation_id)
            )
            return {"message": "Reservation cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel reservation"
            )
            
    except Exception as e:
        logger.error(
            "Reservation cancellation failed",
            error=str(e),
            reservation_id=str(reservation_id)
        )
        raise handle_service_exception(e)


@router.get("/stock/{product_id}/{store_id}", response_model=StockLevel)
async def get_stock_level(
    product_id: str,
    store_id: str,
    service: InventoryService = Depends(get_inventory_service)
):
    try:
        stock_level = await service.get_stock_level(product_id, store_id)
        
        if not stock_level:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock level not found"
            )
        
        return stock_level
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get stock level",
            error=str(e),
            product_id=str(product_id),
            store_id=str(store_id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/update-stock")
async def update_stock(
    stock_update: StockUpdateSchema,
    service: InventoryService = Depends(get_inventory_service)
):
    try:
        stock_update_model = StockUpdate(
            product_id=stock_update.product_id,
            store_id=stock_update.store_id,
            quantity_change=stock_update.quantity if stock_update.operation == "add" else -stock_update.quantity
        )
        success = await service.update_stock(stock_update_model)
        
        if success:
            logger.info(
                "Stock updated successfully",
                product_id=str(stock_update.product_id),
                store_id=str(stock_update.store_id),
                quantity_change=stock_update.quantity_change
            )
            return {"message": "Stock updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update stock"
            )
            
    except Exception as e:
        logger.error(
            "Stock update failed",
            error=str(e),
            product_id=str(stock_update.product_id),
            store_id=str(stock_update.store_id)
        )
        raise handle_service_exception(e)


@router.get("/products/", response_model=List[Product])
async def get_products(service: InventoryService = Depends(get_inventory_service)):
    try:
        products = await service.get_all_products()
        return products
    except Exception as e:
        logger.error("Error getting products", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/all", response_model=List[Inventory])
async def get_inventory(service: InventoryService = Depends(get_inventory_service)):
    try:
        inventory = await service.get_all_inventory()
        return inventory
    except Exception as e:
        logger.error("Error getting inventory", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/consume", status_code=status.HTTP_200_OK)
async def consume_reservation(
    request: ReservationConsumeSchema,
    service: InventoryService = Depends(get_inventory_service)
):
    try:
        success = await service.consume_reservation(request.reservation_id)
        
        if success:
            return {"message": "Reservation consumed successfully - stock updated"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to consume reservation"
            )
            
    except Exception as e:
        logger.error("Error consuming reservation", error=str(e), request=request)
        raise handle_service_exception(e)

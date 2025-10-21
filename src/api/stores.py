from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.utils.database import get_db
from src.services.store_service import StoreService
from src.config.event_bus_config import event_bus_config
from src.models.store import Store, StoreInventory
from src.utils.logging import get_logger
from src.utils.error_utils import handle_service_exception

logger = get_logger(__name__)
router = APIRouter(prefix="/stores", tags=["stores"])


async def get_store_service(db: AsyncSession = Depends(get_db)):
    event_bus = event_bus_config.get_event_bus()
    await event_bus.connect()
    
    return StoreService(db, event_bus)


@router.get("/", response_model=List[Store])
async def get_all_stores(
    service: StoreService = Depends(get_store_service)
):
    try:
        stores = await service.get_all_stores()
        return stores
        
    except Exception as e:
        logger.error(
            "Failed to get stores",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{store_id}", response_model=Store)
async def get_store(
    store_id: str,
    service: StoreService = Depends(get_store_service)
):
    try:
        store = await service.get_store(store_id)
        
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found"
            )
        
        return store
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get store",
            error=str(e),
            store_id=str(store_id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{store_id}/inventory", response_model=List[StoreInventory])
async def get_store_inventory(
    store_id: str,
    service: StoreService = Depends(get_store_service)
):
    try:
        inventory = await service.get_store_inventory(store_id)
        return inventory
        
    except Exception as e:
        logger.error(
            "Failed to get store inventory",
            error=str(e),
            store_id=str(store_id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )







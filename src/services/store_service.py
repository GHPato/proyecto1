from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.database import StoreDB, InventoryDB
from src.models.store import Store, StoreInventory
from src.interfaces.event_bus import EventBus
from src.utils.logging import get_logger
from src.exceptions import StoreNotFoundError

logger = get_logger(__name__)


class StoreService:
    def __init__(self, db: AsyncSession, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
    
    async def get_all_stores(self) -> List[Store]:
        result = await self.db.execute(select(StoreDB))
        stores_db = result.scalars().all()
        return [
            Store(
                id=store_db.id,
                name=store_db.name,
                address=store_db.address,
                city=store_db.city,
                country=store_db.country,
                zip_code=store_db.zip_code,
                status=store_db.status,
                timezone=store_db.timezone,
                created_at=store_db.created_at,
                updated_at=store_db.updated_at
            )
            for store_db in stores_db
        ]
    
    async def get_store(self, store_id: str) -> Optional[Store]:
        result = await self.db.execute(
            select(StoreDB).where(StoreDB.id == store_id)
        )
        store_db = result.scalar_one_or_none()
        if not store_db:
            return None
        return Store(
            id=store_db.id,
            name=store_db.name,
            address=store_db.address,
            city=store_db.city,
            country=store_db.country,
            zip_code=store_db.zip_code,
            status=store_db.status,
            timezone=store_db.timezone,
            created_at=store_db.created_at,
            updated_at=store_db.updated_at
        )
    
    async def get_store_inventory(self, store_id: str) -> List[StoreInventory]:
        store = await self.get_store(store_id)
        if not store:
            raise StoreNotFoundError(store_id)
        
        result = await self.db.execute(
            select(InventoryDB).where(InventoryDB.store_id == store_id)
        )
        inventory_db = result.scalars().all()
        
        return [
            StoreInventory(
                store_id=inv.store_id,
                product_id=inv.product_id,
                available_quantity=inv.available_quantity,
                reserved_quantity=inv.reserved_quantity,
                total_quantity=inv.total_quantity,
                last_updated=inv.last_updated,
                sync_version=inv.version
            )
            for inv in inventory_db
        ]
    
    

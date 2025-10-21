from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from src.models.database import InventoryDB, ProductDB, StoreDB, ReservationDB, EventDB
from src.models.inventory import (
    Inventory, Product, Reservation, ReservationRequest, 
    ReservationResponse, ReservationStatus, StockUpdate, StockLevel
)
from src.interfaces.event_bus import EventBus, LockManager, CacheManager
from src.services.event_service import EventService
from src.utils.logging import get_logger
from src.exceptions import (
    InsufficientStockError, InventoryNotFoundError, ProductNotFoundError,
    ReservationNotFoundError, ReservationExpiredError, ReservationAlreadyConfirmedError,
    OptimisticLockConflictError, DistributedLockFailedError, InvalidReservationStatusError
)
from config.settings import settings

logger = get_logger(__name__)


class InventoryService:
    def __init__(
        self, 
        db: AsyncSession, 
        event_bus: EventBus,
        lock_manager: LockManager,
        cache_manager: CacheManager
    ):
        self.db = db
        self.event_bus = event_bus
        self.lock_manager = lock_manager
        self.cache_manager = cache_manager
        self.event_service = EventService(event_bus)
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        result = await self.db.execute(
            select(ProductDB).where(ProductDB.id == product_id)
        )
        product_db = result.scalar_one_or_none()
        if not product_db:
            return None
        
        return Product(
            id=product_db.id,
            sku=product_db.sku,
            name=product_db.name,
            description=product_db.description,
            category=product_db.category,
            unit_price=product_db.unit_price / 100,
            created_at=product_db.created_at,
            updated_at=product_db.updated_at
        )
    
    async def get_inventory(self, product_id: str, store_id: str) -> Optional[Inventory]:
        result = await self.db.execute(
            select(InventoryDB)
            .where(
                and_(
                    InventoryDB.product_id == product_id,
                    InventoryDB.store_id == store_id
                )
            )
        )
        inventory_db = result.scalar_one_or_none()
        if not inventory_db:
            return None
        
        return Inventory(
            id=inventory_db.id,
            product_id=inventory_db.product_id,
            store_id=inventory_db.store_id,
            available_quantity=inventory_db.available_quantity,
            reserved_quantity=inventory_db.reserved_quantity,
            total_quantity=inventory_db.total_quantity,
            version=inventory_db.version,
            last_updated=inventory_db.last_updated
        )
    
    async def get_stock_level(self, product_id: str, store_id: str) -> Optional[StockLevel]:
        inventory = await self.get_inventory(product_id, store_id)
        if not inventory:
            return None
        
        return StockLevel(
            product_id=inventory.product_id,
            store_id=inventory.store_id,
            available=inventory.available_quantity,
            reserved=inventory.reserved_quantity,
            total=inventory.total_quantity,
            last_updated=inventory.last_updated
        )
    
    async def reserve_stock(self, request: ReservationRequest) -> ReservationResponse:
        lock_key = f"inventory_lock:{request.product_id}:{request.store_id}"
        
        try:
            acquired = await self.lock_manager.acquire_lock(lock_key, ttl=30)
            if not acquired:
                logger.error(f"Could not acquire distributed lock for {lock_key}")
                raise DistributedLockFailedError(lock_key)
            
            inventory = await self.get_inventory(request.product_id, request.store_id)
            if not inventory:
                raise InventoryNotFoundError(request.product_id, request.store_id)
            
            if inventory.available_quantity < request.quantity:
                raise InsufficientStockError(inventory.available_quantity, request.quantity)
            
            expires_at = datetime.utcnow() + timedelta(minutes=request.ttl_minutes)
            
            reservation_db = ReservationDB(
                order_id=request.order_id,
                product_id=request.product_id,
                store_id=request.store_id,
                quantity=request.quantity,
                status=ReservationStatus.PENDING,
                expires_at=expires_at
            )
            
            self.db.add(reservation_db)
            
            result = await self.db.execute(
                update(InventoryDB)
                .where(
                    and_(
                        InventoryDB.product_id == request.product_id,
                        InventoryDB.store_id == request.store_id,
                        InventoryDB.version == inventory.version
                    )
                )
                .values(
                    available_quantity=InventoryDB.available_quantity - request.quantity,
                    reserved_quantity=InventoryDB.reserved_quantity + request.quantity,
                    version=InventoryDB.version + 1,
                    last_updated=datetime.utcnow()
                )
            )
            
            if result.rowcount == 0:
                raise OptimisticLockConflictError(f"inventory:{request.product_id}:{request.store_id}")
            
            await self.event_service.publish_event("reservation_created", {
                "reservation_id": str(reservation_db.id),
                "order_id": str(request.order_id),
                "product_id": str(request.product_id),
                "store_id": str(request.store_id),
                "quantity": request.quantity,
                "expires_at": expires_at.isoformat()
            })
            
            await self.db.commit()
            
            logger.info(
                "Stock reserved successfully",
                reservation_id=str(reservation_db.id),
                order_id=str(request.order_id),
                product_id=str(request.product_id),
                store_id=str(request.store_id),
                quantity=request.quantity
            )
            
            return ReservationResponse(
                reservation_id=reservation_db.id,
                status=ReservationStatus.PENDING,
                expires_at=expires_at,
                message="Stock reserved successfully"
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to reserve stock",
                error=str(e),
                order_id=str(request.order_id),
                product_id=str(request.product_id),
                store_id=str(request.store_id)
            )
            raise
        finally:
            try:
                await self.lock_manager.release_lock(lock_key)
            except Exception as e:
                logger.error(f"Failed to release distributed lock {lock_key}: {e}")
    
    async def confirm_reservation(self, reservation_id: str) -> bool:
        result = await self.db.execute(
            select(ReservationDB).where(ReservationDB.id == reservation_id)
        )
        reservation = result.scalar_one_or_none()
        
        if not reservation:
            raise ReservationNotFoundError(reservation_id)
        
        if reservation.status != ReservationStatus.PENDING:
            raise InvalidReservationStatusError(
                reservation_id, 
                reservation.status, 
                ReservationStatus.PENDING
            )
        
        if reservation.expires_at < datetime.utcnow():
            await self._expire_reservation(reservation_id)
            raise ReservationExpiredError(reservation_id)
        
        await self.db.execute(
            update(ReservationDB)
            .where(ReservationDB.id == reservation_id)
            .values(
                status=ReservationStatus.CONFIRMED,
                confirmed_at=datetime.utcnow()
            )
        )
        
        await self.event_service.publish_event("reservation_confirmed", {
                "reservation_id": str(reservation_id),
                "order_id": str(reservation.order_id),
                "product_id": str(reservation.product_id),
                "store_id": str(reservation.store_id),
                "quantity": reservation.quantity
            })
        
        await self.db.commit()
        
        logger.info(
            "Reservation confirmed",
            reservation_id=str(reservation_id),
            order_id=str(reservation.order_id)
        )
        
        return True

    async def consume_reservation(self, reservation_id: str) -> bool:
        result = await self.db.execute(
            select(ReservationDB).where(ReservationDB.id == reservation_id)
        )
        reservation = result.scalar_one_or_none()
        
        if not reservation:
            raise Exception("Reservation not found")
        
        if reservation.status != ReservationStatus.CONFIRMED:
            raise Exception("Reservation must be confirmed before consumption")
        
        inventory_result = await self.db.execute(
            select(InventoryDB).where(
                and_(
                    InventoryDB.product_id == reservation.product_id,
                    InventoryDB.store_id == reservation.store_id
                )
            )
        )
        inventory = inventory_result.scalar_one_or_none()
        
        if not inventory:
            raise Exception("Inventory not found")
        
        result = await self.db.execute(
            update(InventoryDB)
            .where(
                and_(
                    InventoryDB.product_id == reservation.product_id,
                    InventoryDB.store_id == reservation.store_id,
                    InventoryDB.version == inventory.version
                )
            )
            .values(
                reserved_quantity=InventoryDB.reserved_quantity - reservation.quantity,
                total_quantity=InventoryDB.total_quantity - reservation.quantity,
                version=InventoryDB.version + 1,
                last_updated=datetime.utcnow()
            )
        )
        
        if result.rowcount == 0:
            raise Exception("Optimistic lock conflict - inventory was modified by another operation")
        
        await self.db.execute(
            update(ReservationDB)
            .where(ReservationDB.id == reservation_id)
            .values(status=ReservationStatus.CONSUMED)
        )
        
        await self.event_service.publish_event("reservation_consumed", {
                "reservation_id": str(reservation_id),
                "order_id": str(reservation.order_id),
                "product_id": str(reservation.product_id),
                "store_id": str(reservation.store_id),
                "quantity": reservation.quantity
            })
        
        await self.db.commit()
        
        logger.info(
            "Reservation consumed - stock updated",
            reservation_id=str(reservation_id),
            order_id=str(reservation.order_id),
            quantity=reservation.quantity
        )
        
        return True
    
    async def cancel_reservation(self, reservation_id: str) -> bool:
        result = await self.db.execute(
            select(ReservationDB).where(ReservationDB.id == reservation_id)
        )
        reservation = result.scalar_one_or_none()
        
        if not reservation:
            raise Exception("Reservation not found")
        
        if reservation.status not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
            raise Exception("Reservation cannot be cancelled")
        
        lock_key = f"inventory_lock:{reservation.product_id}:{reservation.store_id}"
        
        try:
            acquired = await self.lock_manager.acquire_lock(lock_key, ttl=30)
            if not acquired:
                raise Exception("Could not acquire inventory lock")
            
            if reservation.status in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
                await self.db.execute(
                    update(InventoryDB)
                    .where(
                        and_(
                            InventoryDB.product_id == reservation.product_id,
                            InventoryDB.store_id == reservation.store_id
                        )
                    )
                    .values(
                        available_quantity=InventoryDB.available_quantity + reservation.quantity,
                        reserved_quantity=InventoryDB.reserved_quantity - reservation.quantity,
                        version=InventoryDB.version + 1,
                        last_updated=datetime.utcnow()
                    )
                )
            
            await self.db.execute(
                update(ReservationDB)
                .where(ReservationDB.id == reservation_id)
                .values(
                    status=ReservationStatus.CANCELLED,
                    cancelled_at=datetime.utcnow()
                )
            )
            
            await self.event_service.publish_event("reservation_cancelled", {
                    "reservation_id": str(reservation_id),
                    "order_id": str(reservation.order_id),
                    "product_id": str(reservation.product_id),
                    "store_id": str(reservation.store_id),
                    "quantity": reservation.quantity
                })
            
            await self.db.commit()
            
            logger.info(
                "Reservation cancelled",
                reservation_id=str(reservation_id),
                order_id=str(reservation.order_id)
            )
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to cancel reservation",
                error=str(e),
                reservation_id=str(reservation_id)
            )
            raise
        finally:
            try:
                await self.lock_manager.release_lock(lock_key)
            except Exception as e:
                logger.error(f"Failed to release distributed lock {lock_key}: {e}")
    
    async def update_stock(self, stock_update: StockUpdate) -> bool:
        lock_key = f"inventory_lock:{stock_update.product_id}:{stock_update.store_id}"
        
        try:
            acquired = await self.lock_manager.acquire_lock(lock_key, ttl=30)
            if not acquired:
                raise Exception("Could not acquire inventory lock")
            
            inventory = await self.get_inventory(stock_update.product_id, stock_update.store_id)
            if not inventory:
                raise Exception("Inventory not found")
            
            new_available = inventory.available_quantity + stock_update.quantity_change
            if new_available < 0:
                raise Exception("Stock cannot go below zero")
            
            result = await self.db.execute(
                update(InventoryDB)
                .where(
                    and_(
                        InventoryDB.product_id == stock_update.product_id,
                        InventoryDB.store_id == stock_update.store_id,
                        InventoryDB.version == inventory.version
                    )
                )
                .values(
                    available_quantity=new_available,
                    total_quantity=InventoryDB.total_quantity + stock_update.quantity_change,
                    version=InventoryDB.version + 1,
                    last_updated=datetime.utcnow()
                )
            )
            
            if result.rowcount == 0:
                raise OptimisticLockConflictError(f"inventory:{stock_update.product_id}:{stock_update.store_id}")
            
            await self.event_service.publish_event("stock_updated", {
                "product_id": str(stock_update.product_id),
                "store_id": str(stock_update.store_id),
                "quantity_change": stock_update.quantity_change,
                "new_available": new_available,
                "reason": stock_update.reason,
                "reference_id": stock_update.reference_id
            })
            
            await self.db.commit()
            
            logger.info(
                "Stock updated successfully",
                product_id=str(stock_update.product_id),
                store_id=str(stock_update.store_id),
                quantity_change=stock_update.quantity_change,
                new_available=new_available
            )
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "Failed to update stock",
                error=str(e),
                product_id=str(stock_update.product_id),
                store_id=str(stock_update.store_id)
            )
            raise
        finally:
            try:
                await self.lock_manager.release_lock(lock_key)
            except Exception as e:
                logger.error(f"Failed to release distributed lock {lock_key}: {e}")
    
    async def _expire_reservation(self, reservation_id: str):
        result = await self.db.execute(
            select(ReservationDB).where(ReservationDB.id == reservation_id)
        )
        reservation = result.scalar_one_or_none()
        
        if not reservation or reservation.status != ReservationStatus.PENDING:
            return
        
        await self.db.execute(
            update(InventoryDB)
            .where(
                and_(
                    InventoryDB.product_id == reservation.product_id,
                    InventoryDB.store_id == reservation.store_id
                )
            )
            .values(
                available_quantity=InventoryDB.available_quantity + reservation.quantity,
                reserved_quantity=InventoryDB.reserved_quantity - reservation.quantity,
                last_updated=datetime.utcnow()
            )
        )
        
        await self.db.execute(
            update(ReservationDB)
            .where(ReservationDB.id == reservation_id)
            .values(status=ReservationStatus.EXPIRED)
        )
        
        await self._publish_event("reservation_expired", {
            "reservation_id": str(reservation_id),
            "order_id": str(reservation.order_id),
            "product_id": str(reservation.product_id),
            "store_id": str(reservation.store_id),
            "quantity": reservation.quantity
        })
    

    async def get_all_products(self) -> List[Product]:
        result = await self.db.execute(select(ProductDB))
        products_db = result.scalars().all()
        
        products = []
        for product_db in products_db:
            products.append(Product(
                id=product_db.id,
                sku=product_db.sku,
                name=product_db.name,
                description=product_db.description,
                category=product_db.category,
                unit_price=product_db.unit_price / 100,
                created_at=product_db.created_at,
                updated_at=product_db.updated_at
            ))
        
        return products

    async def get_all_inventory(self) -> List[Inventory]:
        result = await self.db.execute(select(InventoryDB))
        inventory_db = result.scalars().all()
        
        inventory = []
        for inv_db in inventory_db:
            inventory.append(Inventory(
                id=inv_db.id,
                product_id=inv_db.product_id,
                store_id=inv_db.store_id,
                available_quantity=inv_db.available_quantity,
                reserved_quantity=inv_db.reserved_quantity,
                total_quantity=inv_db.total_quantity,
                version=inv_db.version,
                last_updated=inv_db.last_updated
            ))
        
        return inventory

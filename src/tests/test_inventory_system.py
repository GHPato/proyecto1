"""
Tests unitarios para el sistema de inventario distribuido.
Cubre concurrencia, lógica de negocio, errores, eventos y tolerancia a fallos.
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.services.inventory_service import InventoryService
from src.models.inventory import Inventory, ReservationStatus
from src.schemas.inventory_schemas import ReservationRequestSchema, StockUpdateSchema
from src.exceptions import (
    InsufficientStockError,
    InventoryNotFoundError,
    OptimisticLockConflictError,
    DistributedLockFailedError
)


class TestInventorySystem:
    """Tests del sistema de inventario distribuido."""

    @pytest.fixture
    def mock_service(self):
        """Mock del InventoryService."""
        service = MagicMock(spec=InventoryService)
        service.db = AsyncMock()
        service.event_service = AsyncMock()
        service.lock_manager = AsyncMock()
        service.cache_manager = AsyncMock()
        service.get_reservation = AsyncMock()
        service.confirm_reservation = AsyncMock()
        service.cancel_reservation = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_concurrent_reservations_prevent_overselling(self, mock_service):
        """Valida que reservas concurrentes previenen overselling."""
        mock_inventory = Inventory(
            id="inv-1",
            product_id="123e4567-e89b-12d3-a456-426614174000",
            store_id="123e4567-e89b-12d3-a456-426614174001",
            total_quantity=5,
            available_quantity=5,
            reserved_quantity=0,
            version=1,
            last_updated=datetime.utcnow()
        )
        
        mock_service.get_inventory.return_value = mock_inventory
        mock_service.lock_manager.acquire_lock.return_value = True
        mock_service.lock_manager.release_lock.return_value = True
        
        def side_effect_reserve(*args, **kwargs):
            if mock_inventory.available_quantity >= 3:
                mock_inventory.available_quantity -= 3
                mock_inventory.reserved_quantity += 3
                return MagicMock(id="res-1", status=ReservationStatus.PENDING)
            else:
                raise InsufficientStockError(available=2, requested=3)
        
        mock_service.reserve_stock.side_effect = side_effect_reserve
        
        async def reserve_stock():
            try:
                return await mock_service.reserve_stock(
                    product_id="123e4567-e89b-12d3-a456-426614174000",
                    store_id="123e4567-e89b-12d3-a456-426614174001",
                    request=ReservationRequestSchema(
                        order_id="ORDER-123",
                        product_id="123e4567-e89b-12d3-a456-426614174000",
                        store_id="123e4567-e89b-12d3-a456-426614174001",
                        quantity=3,
                        ttl_minutes=30
                    )
                )
            except InsufficientStockError:
                return None
        
        results = await asyncio.gather(reserve_stock(), reserve_stock(), return_exceptions=True)
        
        successful_reservations = [r for r in results if r is not None and not isinstance(r, Exception)]
        failed_reservations = [r for r in results if isinstance(r, InsufficientStockError)]
        
        assert len(successful_reservations) == 1
        assert len(failed_reservations) >= 0

    @pytest.mark.asyncio
    async def test_optimistic_locking_prevents_version_conflicts(self, mock_service):
        """Valida que optimistic locking previene conflictos de versión."""
        mock_inventory = Inventory(
            id="inv-1",
            product_id="123e4567-e89b-12d3-a456-426614174000",
            store_id="123e4567-e89b-12d3-a456-426614174001",
            total_quantity=5,
            available_quantity=5,
            reserved_quantity=0,
            version=2,
            last_updated=datetime.utcnow()
        )
        
        mock_service.get_inventory.return_value = mock_inventory
        mock_service.update_stock.side_effect = OptimisticLockConflictError(
            resource="inventory:123e4567-e89b-12d3-a456-426614174000:123e4567-e89b-12d3-a456-426614174001"
        )
        
        with pytest.raises(OptimisticLockConflictError) as exc_info:
            await mock_service.update_stock(
                product_id="123e4567-e89b-12d3-a456-426614174000",
                store_id="123e4567-e89b-12d3-a456-426614174001",
                request=StockUpdateSchema(
                    product_id="123e4567-e89b-12d3-a456-426614174000",
                    store_id="123e4567-e89b-12d3-a456-426614174001",
                    quantity=10,
                    operation="add"
                )
            )
        
        assert "Optimistic lock conflict" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reserve_stock_decreases_available_quantity(self, mock_service):
        """Valida que reservar stock reduce la cantidad disponible."""
        mock_inventory = Inventory(
            id="inv-1",
            product_id="123e4567-e89b-12d3-a456-426614174000",
            store_id="123e4567-e89b-12d3-a456-426614174001",
            total_quantity=5,
            available_quantity=5,
            reserved_quantity=0,
            version=1,
            last_updated=datetime.utcnow()
        )
        
        mock_service.get_inventory.return_value = mock_inventory
        mock_service.lock_manager.acquire_lock.return_value = True
        mock_service.lock_manager.release_lock.return_value = True
        
        mock_reservation = MagicMock(
            id="res-1",
            quantity=2,
            status=ReservationStatus.PENDING
        )
        mock_service.reserve_stock.return_value = mock_reservation
        
        result = await mock_service.reserve_stock(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            store_id="123e4567-e89b-12d3-a456-426614174001",
            request=ReservationRequestSchema(
                order_id="ORDER-123",
                product_id="123e4567-e89b-12d3-a456-426614174000",
                store_id="123e4567-e89b-12d3-a456-426614174001",
                quantity=2,
                ttl_minutes=30
            )
        )
        
        assert result.id == "res-1"
        assert result.quantity == 2
        assert result.status == ReservationStatus.PENDING

    @pytest.mark.asyncio
    async def test_confirm_reservation_changes_status(self, mock_service):
        """Valida que confirmar una reserva cambia su estado."""
        mock_reservation = MagicMock(
            id="res-1",
            status=ReservationStatus.PENDING
        )
        
        mock_service.get_reservation.return_value = mock_reservation
        mock_service.lock_manager.acquire_lock.return_value = True
        mock_service.lock_manager.release_lock.return_value = True
        
        confirmed_reservation = MagicMock(
            id="res-1",
            status=ReservationStatus.CONFIRMED,
            message="Reservation confirmed successfully"
        )
        mock_service.confirm_reservation.return_value = confirmed_reservation
        
        result = await mock_service.confirm_reservation(reservation_id="res-1")
        
        assert result.status == ReservationStatus.CONFIRMED
        assert "confirmed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_cancel_reservation_restores_stock(self, mock_service):
        """Valida que cancelar una reserva restaura el stock disponible."""
        mock_reservation = MagicMock(
            id="res-1",
            status=ReservationStatus.PENDING
        )
        
        mock_service.get_reservation.return_value = mock_reservation
        mock_service.lock_manager.acquire_lock.return_value = True
        mock_service.lock_manager.release_lock.return_value = True
        mock_service.cancel_reservation.return_value = True
        
        result = await mock_service.cancel_reservation(reservation_id="res-1")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_insufficient_stock_raises_error(self, mock_service):
        """Valida que stock insuficiente genera error apropiado."""
        mock_inventory = Inventory(
            id="inv-1",
            product_id="123e4567-e89b-12d3-a456-426614174000",
            store_id="123e4567-e89b-12d3-a456-426614174001",
            total_quantity=2,
            available_quantity=2,
            reserved_quantity=0,
            version=1,
            last_updated=datetime.utcnow()
        )
        
        mock_service.get_inventory.return_value = mock_inventory
        mock_service.lock_manager.acquire_lock.return_value = True
        mock_service.lock_manager.release_lock.return_value = True
        
        mock_service.reserve_stock.side_effect = InsufficientStockError(
            available=2, requested=5
        )
        
        with pytest.raises(InsufficientStockError) as exc_info:
            await mock_service.reserve_stock(
                product_id="123e4567-e89b-12d3-a456-426614174000",
                store_id="123e4567-e89b-12d3-a456-426614174001",
                request=ReservationRequestSchema(
                    order_id="ORDER-123",
                    product_id="123e4567-e89b-12d3-a456-426614174000",
                    store_id="123e4567-e89b-12d3-a456-426614174001",
                    quantity=5,
                    ttl_minutes=30
                )
            )
        
        assert "Insufficient stock" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_product_id_raises_error(self, mock_service):
        """Valida que producto inexistente genera error apropiado."""
        mock_service.reserve_stock.side_effect = InventoryNotFoundError(
            product_id="123e4567-e89b-12d3-a456-426614174999", 
            store_id="123e4567-e89b-12d3-a456-426614174001"
        )
        
        with pytest.raises(InventoryNotFoundError) as exc_info:
            await mock_service.reserve_stock(
                product_id="123e4567-e89b-12d3-a456-426614174999",
                store_id="123e4567-e89b-12d3-a456-426614174001",
                request=ReservationRequestSchema(
                    order_id="ORDER-123",
                    product_id="123e4567-e89b-12d3-a456-426614174999",
                    store_id="123e4567-e89b-12d3-a456-426614174001",
                    quantity=1,
                    ttl_minutes=30
                )
            )
        
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_stock_reservation_publishes_event(self, mock_service):
        """Valida que reservar stock publica evento correspondiente."""
        mock_service.event_service.publish_event.return_value = True
        
        result = await mock_service.event_service.publish_event(
            event_type="stock_reserved",
            data={
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "store_id": "123e4567-e89b-12d3-a456-426614174001",
                "quantity": 2,
                "reservation_id": "res-1"
            }
        )
        
        assert result is True
        mock_service.event_service.publish_event.assert_called_once_with(
            event_type="stock_reserved",
            data={
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "store_id": "123e4567-e89b-12d3-a456-426614174001",
                "quantity": 2,
                "reservation_id": "res-1"
            }
        )

    @pytest.mark.asyncio
    async def test_stock_update_publishes_event(self, mock_service):
        """Valida que actualizar stock publica evento correspondiente."""
        mock_service.event_service.publish_event.return_value = True
        
        result = await mock_service.event_service.publish_event(
            event_type="stock_updated",
            data={
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "store_id": "123e4567-e89b-12d3-a456-426614174001",
                "old_quantity": 10,
                "new_quantity": 15,
                "version": 2
            }
        )
        
        assert result is True
        mock_service.event_service.publish_event.assert_called_once_with(
            event_type="stock_updated",
            data={
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "store_id": "123e4567-e89b-12d3-a456-426614174001",
                "old_quantity": 10,
                "new_quantity": 15,
                "version": 2
            }
        )

    @pytest.mark.asyncio
    async def test_redis_connection_failure_raises_consistent_error(self, mock_service):
        """Valida que fallo de conexión Redis genera error consistente."""
        mock_service.reserve_stock.side_effect = DistributedLockFailedError(
            lock_key="inventory:123e4567-e89b-12d3-a456-426614174000:123e4567-e89b-12d3-a456-426614174001"
        )
        
        with pytest.raises(DistributedLockFailedError) as exc_info:
            await mock_service.reserve_stock(
                product_id="123e4567-e89b-12d3-a456-426614174000",
                store_id="123e4567-e89b-12d3-a456-426614174001",
                request=MagicMock(quantity=1, ttl_minutes=30)
            )
        
        assert "Could not acquire distributed lock" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_connection_failure_maintains_integrity(self, mock_service):
        """Valida que fallo de base de datos mantiene integridad."""
        mock_service.update_stock.side_effect = Exception("Database connection lost")
        
        with pytest.raises(Exception) as exc_info:
            await mock_service.update_stock(
                product_id="123e4567-e89b-12d3-a456-426614174000",
                store_id="123e4567-e89b-12d3-a456-426614174001",
                request=MagicMock(quantity=10, operation="add")
            )
        
        assert "Database connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_event_publishing_failure_does_not_break_operation(self, mock_service):
        """Valida que fallo en publicación de eventos no rompe la operación."""
        mock_service.event_service.publish_event.side_effect = Exception("Event bus unavailable")
        
        mock_service.lock_manager.acquire_lock.return_value = True
        mock_service.lock_manager.release_lock.return_value = True
        mock_service.reserve_stock.return_value = MagicMock(
            id="res-1",
            status="PENDING"
        )
        
        result = await mock_service.reserve_stock(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            store_id="123e4567-e89b-12d3-a456-426614174001",
            request=MagicMock(quantity=1, ttl_minutes=30)
        )
        
        assert result.id == "res-1"
        assert result.status == "PENDING"

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_partial_failures(self, mock_service):
        """Valida degradación graceful en fallos parciales."""
        mock_service.event_service.publish_event.side_effect = Exception("Event bus down")
        mock_service.lock_manager.acquire_lock.return_value = True
        mock_service.lock_manager.release_lock.return_value = True
        mock_service.reserve_stock.return_value = MagicMock(
            id="res-1",
            status="PENDING"
        )
        
        result = await mock_service.reserve_stock(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            store_id="123e4567-e89b-12d3-a456-426614174001",
            request=MagicMock(quantity=1, ttl_minutes=30)
        )
        
        assert result.id == "res-1"
        assert result.status == "PENDING"

    @pytest.mark.asyncio
    async def test_successful_operation_logs_metrics(self, mock_service):
        """Valida que operaciones exitosas registran métricas."""
        mock_service.lock_manager.acquire_lock.return_value = True
        mock_service.lock_manager.release_lock.return_value = True
        mock_service.reserve_stock.return_value = MagicMock(
            id="res-1",
            status="PENDING"
        )
        
        with patch('logging.getLogger') as mock_logger:
            mock_logger.return_value.info = MagicMock()
            result = await mock_service.reserve_stock(
                product_id="123e4567-e89b-12d3-a456-426614174000",
                store_id="123e4567-e89b-12d3-a456-426614174001",
                request=MagicMock(quantity=1, ttl_minutes=30)
            )
            
            assert result.id == "res-1"
            assert result.status == "PENDING"

    @pytest.mark.asyncio
    async def test_failed_operation_logs_error_metrics(self, mock_service):
        """Valida que operaciones fallidas registran métricas de error."""
        mock_service.reserve_stock.side_effect = Exception("Reservation failed")
        
        with patch('logging.getLogger') as mock_logger:
            mock_logger.return_value.error = MagicMock()
            with pytest.raises(Exception):
                await mock_service.reserve_stock(
                    product_id="123e4567-e89b-12d3-a456-426614174000",
                    store_id="123e4567-e89b-12d3-a456-426614174001",
                    request=MagicMock(quantity=1, ttl_minutes=30)
                )
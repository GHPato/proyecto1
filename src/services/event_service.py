from typing import Dict, Any
from src.interfaces.event_bus import EventBus, EventMessage
from src.utils.logging import get_logger

logger = get_logger(__name__)


class EventService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def publish_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        topic: str = "inventory_events",
        source: str = "inventory_service"
    ) -> None:
        try:
            event_message = EventMessage(
                event_type=event_type,
                payload=payload,
                source=source
            )
            
            await self.event_bus.publish(topic, event_message.to_dict())
            
            logger.info(
                "Event published successfully",
                event_type=event_type,
                topic=topic,
                source=source
            )
        except Exception as e:
            logger.error(
                "Failed to publish event",
                event_type=event_type,
                topic=topic,
                error=str(e)
            )
            raise
    

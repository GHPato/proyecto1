from fastapi import HTTPException, status
from src.exceptions import InventoryServiceBaseException
from src.utils.logging import get_logger
from src.constants import *

logger = get_logger(__name__)


def handle_service_exception(ex: Exception) -> HTTPException:
    if isinstance(ex, InventoryServiceBaseException):
        return HTTPException(
            status_code=ex.status_code,
            detail=ex.error_msg
        )
    else:
        logger.error(f"Unhandled exception type: {type(ex)}")
        return HTTPException(
            status_code=RESP_INTERNAL_SERVER_ERROR,
            detail=str(ex) or SERVER_ERROR
        )

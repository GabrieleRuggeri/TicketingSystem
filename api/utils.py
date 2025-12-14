from uuid import UUID 
from fastapi import HTTPException, status
from logging import Logger
from typing import Literal

entity_type : Literal['user', 'hotel', 'room', 'booking', 'undefined_entity'] = 'undefined_entity'

def _parse_id(
        id: str,
        logger: Logger, 
        entity: Literal['user', 'hotel', 'room', 'booking', 'undefined_entity'] = entity_type
    ) -> UUID:
    """Validate and normalize a GUID identifier for any entity among:
    - user
    - hotel
    - room
    - booking
    - undefined entity.
    """

    try:
        return UUID(id, version=4)
    except ValueError as exc:
        logger.warning(f"Invalid GUID supplied for {entity}_id", extra={f"{entity}_id": id})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The supplied {entity} id is not a valid UUID4.",
        ) from exc
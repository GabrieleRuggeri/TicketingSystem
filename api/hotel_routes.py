"""Hotel-related FastAPI routes."""

import logging
from typing import Any
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from .utils import _parse_id as _parse_hotel_id
from .utils import _parse_id as _parse_room_id

try:  # Supabase dependency used for conflict detection on inserts.
    from postgrest.exceptions import APIError # type: ignore
except Exception:  # pragma: no cover - fallback for environments without Supabase
    class APIError(Exception):
        """Lightweight stand-in when Supabase is not installed."""

        code: str | None = None
        status_code: int | None = None

from Hotels.structure import Hotel, Room
from Database.deps import get_db

from .models import (
    MessageResponse,
    HotelFields,
    HotelResponse,
    RoomFields,
    RoomListResponse,
    RoomResponse,
)

logger = logging.getLogger(__name__)

ROOMS_TABLE_NAME = "rooms"
HOTEL_TABLE_NAME = "hotels"
HOTEL = "hotel"
ROOM = "room"

# mount api router
hotel_router = APIRouter()

async def _fetch_hotel_record(
    db: Any,
    guid: UUID,
    not_found_detail: str,
    failure_detail: str,
    log_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Retrieve a single hotel record or raise an HTTPException.

    Args:
        db: Database client.
        guid: Identifier of the hotel to fetch.
        not_found_detail: Message returned when the hotel does not exist.
        failure_detail: Message returned when the database query fails.
        log_context: Extra context for the log record.

    Returns:
        The first matching hotel record as a dictionary.

    Raises:
        HTTPException: 404 when missing, 500 on query failures.
    """

    try:
        result = await run_in_threadpool(
            lambda: db.table(HOTEL_TABLE_NAME).select("*").eq("id", str(guid)).execute()
        )
    except Exception as exc:
        logger.exception("Failed to fetch hotel", extra=log_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=failure_detail,
        ) from exc

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    return result.data[0]

async def _fetch_hotel_rooms(
    db: Any,
    guid: UUID,
    not_found_detail: str,
    failure_detail: str,
    log_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Retrieve the list of rooms for an hotel record or raise an HTTPException.

    Args:
        db: Database client.
        guid: Identifier of the hotel to fetch.
        not_found_detail: Message returned when the no room is associated to the hotel.
        failure_detail: Message returned when the database query fails.
        log_context: Extra context for the log record.

    Returns:
        The list of rooms for the hotel

    Raises:
        HTTPException: 404 when missing, 500 on query failures.
    """

    try:
        result = await run_in_threadpool(
            lambda: db.table(ROOMS_TABLE_NAME).select("*").eq("hotel_id", str(guid)).execute()
        )
    except Exception as exc:
        logger.exception("Failed to fetch rooms", extra=log_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=failure_detail,
        ) from exc

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    return result.data

def _is_unique_violation(error: Exception) -> bool:
    """
    Determine whether an API error represents a uniqueness constraint violation.

    Args:
        error: Exception raised by the persistence layer.

    Returns:
        True if the error indicates a duplicate/unique constraint conflict.
    """

    error_code = getattr(error, "code", None)
    if error_code == "23505":
        return True

    status_code_value = getattr(error, "status_code", None)
    if status_code_value == status.HTTP_409_CONFLICT:
        return True
    if str(status_code_value) == str(status.HTTP_409_CONFLICT):
        return True

    message = str(error).lower()
    return "duplicate key value" in message or "unique constraint" in message

async def _fetch_room_record(
    db: Any,
    guid: UUID,
    not_found_detail: str,
    failure_detail: str,
    log_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Retrieve a single room record or raise an HTTPException.

    Args:
        db: Database client.
        guid: Identifier of the room to fetch.
        not_found_detail: Message returned when the room does not exist.
        failure_detail: Message returned when the database query fails.
        log_context: Extra context for the log record.

    Returns:
        The first matching room record as a dictionary.

    Raises:
        HTTPException: 404 when missing, 500 on query failures.
    """

    try:
        result = await run_in_threadpool(
            lambda: db.table(ROOMS_TABLE_NAME).select("*").eq("id", str(guid)).execute()
        )
    except Exception as exc:
        logger.exception("Failed to fetch room", extra=log_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=failure_detail,
        ) from exc

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    return result.data[0]

@hotel_router.get("/health", response_model=MessageResponse)
async def health_check() -> MessageResponse:
    """Quick liveness probe for the hotel service."""

    return MessageResponse(status=status.HTTP_200_OK, message="Hotel service is healthy")

@hotel_router.post(
    "",
    response_model=HotelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_hotel(hotel: Hotel, db=Depends(get_db)) -> HotelResponse:
    """
    Add a Hotel to the database if not already present.

    Args:
        hotel: Hotel payload to persist.
        db: Supabase client injected via dependency.

    Returns:
        HotelResponse wrapping the created hotel.
    """

    normalized_hotel = hotel.model_copy(update={"email": hotel.email.strip()})

    try:
        existing = await run_in_threadpool(
            lambda: db.table(HOTEL_TABLE_NAME)
            .select("*")
            .eq("email", normalized_hotel.email)
            .execute()
        )
    except Exception as exc:
        logger.exception(
            "Failed to query existing hotels by email", extra={"email": normalized_hotel.email}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create hotel due to an internal error.",
        ) from exc

    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Hotel with email {normalized_hotel.email} already exists",
        )

    try:
        insert_result = await run_in_threadpool(
            lambda: db.table(HOTEL_TABLE_NAME).insert(normalized_hotel.to_dict()).execute()
        )
    except APIError as exc:
        error_code = getattr(exc, "code", None)
        status_code_value = getattr(exc, "status_code", None)
        if _is_unique_violation(exc):
            logger.info(
                "Duplicate hotel creation blocked by unique constraint",
                extra={
                    "email": normalized_hotel.email,
                    "error_code": error_code,
                    "status_code": status_code_value,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Hotel with email {normalized_hotel.email} already exists",
            ) from exc

        logger.exception(
            "Failed to insert hotel", extra={"email": normalized_hotel.email, "error_code": error_code}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create hotel due to an internal error.",
        ) from exc
    except Exception as exc:
        logger.exception("Failed to insert hotel", extra={"email": normalized_hotel.email})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create hotel due to an internal error.",
        ) from exc

    created_payload = insert_result.data[0] if insert_result.data else normalized_hotel.to_dict()
    created_hotel = Hotel(**created_payload)  # type: ignore
    logger.info(
        "Hotel created", extra={"hotel_id": str(created_hotel.id), "email": created_hotel.email}
    )
    return HotelResponse(status=status.HTTP_201_CREATED, hotel=created_hotel)


@hotel_router.get(
    "/{hotel_id}",
    response_model=HotelResponse,
    status_code=status.HTTP_200_OK,
)
async def get_hotel(hotel_id: str, db=Depends(get_db)) -> HotelResponse:
    """
    Retrieve a single hotel by identifier.

    Args:
        hotel_id: UUID4 of the target hotel (path parameter).
        db: Supabase client injected via dependency.

    Returns:
        HotelResponse wrapping the requested hotel.
    """

    guid = _parse_hotel_id(hotel_id, logger, HOTEL)

    record = await _fetch_hotel_record(
        db,
        guid,
        not_found_detail=f"No hotel found with id {hotel_id}",
        failure_detail="Unable to retrieve hotel due to an internal error.",
        log_context={"hotel_id": hotel_id},
    )

    hotel_record = Hotel(**record)
    logger.info("Hotel retrieved", extra={"hotel_id": hotel_id})
    return HotelResponse(status=status.HTTP_200_OK, hotel=hotel_record)

@hotel_router.put(
    "/{hotel_id}",
    response_model=HotelResponse,
    status_code=status.HTTP_200_OK,
)
async def update_hotel(hotel_id: str, fields: HotelFields, db=Depends(get_db)) -> HotelResponse:
    """
    Update mutable fields on an existing hotel.

    Args:
        hotel_id: UUID4 of the hotel to update.
        fields: Partial update payload with allowed fields.
        db: Supabase client injected via dependency.

    Returns:
        HotelResponse wrapping the updated hotel.
    """

    guid = _parse_hotel_id(hotel_id, logger, HOTEL)
    updates = fields.model_dump(exclude_unset=True, exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update.",
        )

    try:
        updates["last_modified_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        logger.exception("Error in updating last_modified_at field", extra={"hotel_id": hotel_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error for last_modified_at field: {exc}",
        ) from exc

    _ = await _fetch_hotel_record(
        db,
        guid,
        not_found_detail=f"No hotel found with id {hotel_id}",
        failure_detail="Unable to update hotel due to an internal error.",
        log_context={"hotel_id": hotel_id},
    )

    try:
        await run_in_threadpool(
            lambda: db.table(HOTEL_TABLE_NAME)
            .update(updates)
            .eq("id", str(guid))
            .execute()
        )
    except Exception as exc:
        logger.exception("Failed to update hotel", extra={"hotel_id": hotel_id, "updates": updates})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update hotel due to an internal error.",
        ) from exc

    refreshed = await _fetch_hotel_record(
        db,
        guid,
        not_found_detail=f"No hotel found with id {hotel_id}",
        failure_detail="Unable to update hotel due to an internal error.",
        log_context={"hotel_id": hotel_id},
    )
    updated_hotel = Hotel(**refreshed)
    logger.info("Hotel updated", extra={"hotel_id": hotel_id})
    return HotelResponse(status=status.HTTP_200_OK, hotel=updated_hotel)


@hotel_router.delete(
    "/{hotel_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_hotel(hotel_id: str, db=Depends(get_db)) -> MessageResponse:
    """
    Delete an existing hotel by identifier.

    Args:
        hotel_id: UUID4 of the hotel to delete.
        db: Supabase client injected via dependency.

    Returns:
        MessageResponse confirming deletion.
    """

    guid = _parse_hotel_id(hotel_id, logger, HOTEL)

    _ = await _fetch_hotel_record(
        db,
        guid,
        not_found_detail=f"No hotel found with id {hotel_id}",
        failure_detail="Unable to delete hotel due to an internal error.",
        log_context={"hotel_id": hotel_id},
    )

    try:
        await run_in_threadpool(
            lambda: db.table(HOTEL_TABLE_NAME)
            .delete()
            .eq("id", str(guid))
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to delete hotel", extra={"hotel_id": hotel_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete hotel due to an internal error.",
        ) from exc

    logger.info("Hotel deleted", extra={"hotel_id": hotel_id})
    return MessageResponse(status=status.HTTP_200_OK, message=f"Hotel {hotel_id} deleted")

@hotel_router.post(
    "/rooms",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_room(room: Room, db=Depends(get_db)) -> RoomResponse:
    """
    Add a Room to the database if not already present for the hotel.

    Args:
        room: Room payload to persist.
        db: Supabase client injected via dependency.

    Returns:
        RoomResponse wrapping the created room.
    """

    hotel_id = str(room.hotel_id)
    _ = await _fetch_hotel_record(
        db,
        room.hotel_id,
        not_found_detail=f"No hotel found with id {hotel_id}",
        failure_detail="Unable to create room due to an internal error.",
        log_context={"hotel_id": hotel_id},
    )

    try:
        existing = await run_in_threadpool(
            lambda: db.table(ROOMS_TABLE_NAME)
            .select("*")
            .eq("hotel_id", hotel_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Failed to query existing rooms for hotel", extra={"hotel_id": hotel_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create room due to an internal error.",
        ) from exc

    if any(str(row.get("number")) == room.number for row in existing.data):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Room {room.number} already exists for hotel {hotel_id}",
        )

    try:
        insert_result = await run_in_threadpool(
            lambda: db.table(ROOMS_TABLE_NAME).insert(room.to_dict()).execute()
        )
    except APIError as exc:
        error_code = getattr(exc, "code", None)
        status_code_value = getattr(exc, "status_code", None)
        if _is_unique_violation(exc):
            logger.info(
                "Duplicate room creation blocked by unique constraint",
                extra={"hotel_id": hotel_id, "room_number": room.number, "error_code": error_code},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room {room.number} already exists for hotel {hotel_id}",
            ) from exc

        logger.exception(
            "Failed to insert room",
            extra={"hotel_id": hotel_id, "room_number": room.number, "error_code": error_code},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create room due to an internal error.",
        ) from exc
    except Exception as exc:
        logger.exception("Failed to insert room", extra={"hotel_id": hotel_id, "room_number": room.number})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create room due to an internal error.",
        ) from exc

    created_payload = insert_result.data[0] if insert_result.data else room.to_dict()
    created_room = Room(**created_payload)  # type: ignore
    logger.info(
        "Room created",
        extra={"room_id": str(created_room.id), "hotel_id": hotel_id, "room_number": created_room.number},
    )
    return RoomResponse(status=status.HTTP_201_CREATED, room=created_room)


@hotel_router.get(
    "/rooms/{room_id}",
    response_model=RoomResponse,
    status_code=status.HTTP_200_OK,
)
async def get_room(room_id: str, db=Depends(get_db)) -> RoomResponse:
    """
    Retrieve a single room by identifier.

    Args:
        room_id: UUID4 of the target room (path parameter).
        db: Supabase client injected via dependency.

    Returns:
        RoomResponse wrapping the requested room.
    """

    guid = _parse_room_id(room_id, logger, ROOM)

    record = await _fetch_room_record(
        db,
        guid,
        not_found_detail=f"No room found with id {room_id}",
        failure_detail="Unable to retrieve room due to an internal error.",
        log_context={"room_id": room_id},
    )

    room_record = Room(**record)
    logger.info("Room retrieved", extra={"room_id": room_id})
    return RoomResponse(status=status.HTTP_200_OK, room=room_record)


@hotel_router.put(
    "/rooms/{room_id}",
    response_model=RoomResponse,
    status_code=status.HTTP_200_OK,
)
async def update_room(room_id: str, fields: RoomFields, db=Depends(get_db)) -> RoomResponse:
    """
    Update mutable fields on an existing room.

    Args:
        room_id: UUID4 of the room to update.
        fields: Partial update payload with allowed fields.
        db: Supabase client injected via dependency.

    Returns:
        RoomResponse wrapping the updated room.
    """

    guid = _parse_room_id(room_id, logger, ROOM)
    updates = fields.model_dump(exclude_unset=True, exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update.",
        )

    existing_record = await _fetch_room_record(
        db,
        guid,
        not_found_detail=f"No room found with id {room_id}",
        failure_detail="Unable to update room due to an internal error.",
        log_context={"room_id": room_id},
    )
    existing_room = Room(**existing_record)
    updated_payload = {**existing_room.model_dump(), **updates}

    try:
        Room(**updated_payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if "number" in updates and updates["number"] != existing_room.number:
        try:
            existing_rooms = await run_in_threadpool(
                lambda: db.table(ROOMS_TABLE_NAME)
                .select("*")
                .eq("hotel_id", str(existing_room.hotel_id))
                .execute()
            )
        except Exception as exc:
            logger.exception(
                "Failed to query existing rooms for hotel", extra={"hotel_id": str(existing_room.hotel_id)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to update room due to an internal error.",
            ) from exc

        if any(
            str(row.get("number")) == updates["number"] and str(row.get("id")) != str(existing_room.id)
            for row in existing_rooms.data
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room {updates['number']} already exists for hotel {existing_room.hotel_id}",
            )

    try:
        await run_in_threadpool(
            lambda: db.table(ROOMS_TABLE_NAME)
            .update(updates)
            .eq("id", str(guid))
            .execute()
        )
    except APIError as exc:
        error_code = getattr(exc, "code", None)
        status_code_value = getattr(exc, "status_code", None)
        if _is_unique_violation(exc):
            logger.info(
                "Duplicate room update blocked by unique constraint",
                extra={"room_id": room_id, "room_number": updates.get("number"), "error_code": error_code},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to update room due to a unique constraint violation.",
            ) from exc

        logger.exception(
            "Failed to update room", extra={"room_id": room_id, "updates": updates, "error_code": error_code}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update room due to an internal error.",
        ) from exc
    except Exception as exc:
        logger.exception("Failed to update room", extra={"room_id": room_id, "updates": updates})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update room due to an internal error.",
        ) from exc

    refreshed = await _fetch_room_record(
        db,
        guid,
        not_found_detail=f"No room found with id {room_id}",
        failure_detail="Unable to update room due to an internal error.",
        log_context={"room_id": room_id},
    )
    updated_room = Room(**refreshed)
    logger.info("Room updated", extra={"room_id": room_id})
    return RoomResponse(status=status.HTTP_200_OK, room=updated_room)


@hotel_router.delete(
    "/rooms/{room_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_room(room_id: str, db=Depends(get_db)) -> MessageResponse:
    """
    Delete an existing room by identifier.

    Args:
        room_id: UUID4 of the room to delete.
        db: Supabase client injected via dependency.

    Returns:
        MessageResponse confirming deletion.
    """

    guid = _parse_room_id(room_id, logger, ROOM)

    _ = await _fetch_room_record(
        db,
        guid,
        not_found_detail=f"No room found with id {room_id}",
        failure_detail="Unable to delete room due to an internal error.",
        log_context={"room_id": room_id},
    )

    try:
        await run_in_threadpool(
            lambda: db.table(ROOMS_TABLE_NAME)
            .delete()
            .eq("id", str(guid))
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to delete room", extra={"room_id": room_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete room due to an internal error.",
        ) from exc

    logger.info("Room deleted", extra={"room_id": room_id})
    return MessageResponse(status=status.HTTP_200_OK, message=f"Room {room_id} deleted")

@hotel_router.get(
    "/get_rooms/{hotel_id}",
    response_model=RoomListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_rooms(hotel_id: str, db = Depends(get_db)) -> RoomListResponse:
    """
    Retrieve the list of rooms for a single hotel by identifier.

    Args:
        hotel_id: UUID4 of the target hotel (path parameter).
        db: Supabase client injected via dependency.

    Returns:
        RoomListResponse wrapping the requested hotel's rooms.
    """

    guid = _parse_hotel_id(hotel_id, logger, HOTEL)

    records = await _fetch_hotel_rooms(
        db,
        guid,
        not_found_detail=f"No rooms found for hotel with id {hotel_id}",
        failure_detail="Unable to retrieve rooms due to an internal error.",
        log_context={"hotel_id": hotel_id},
    )

    room_records = [Room(**record) for record in records]
    logger.info("Rooms retrieved.", extra={"hotel": hotel_id})
    return RoomListResponse(status=status.HTTP_200_OK, rooms=room_records)
    

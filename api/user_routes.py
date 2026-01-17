"""User-related FastAPI routes."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from .utils import _parse_id as _parse_user_id

try:  # Supabase dependency used for conflict detection on inserts.
    from postgrest.exceptions import APIError # type: ignore
except Exception:  # pragma: no cover - fallback for environments without Supabase
    class APIError(Exception):
        """Lightweight stand-in when Supabase is not installed."""

        code: str | None = None
        status_code: int | None = None

from Users.user import User
from Database.deps import get_db

from .models import MessageResponse, UserFields, UserResponse

logger = logging.getLogger(__name__)

USER_TABLE_NAME = "users"
USER = "user"

# mount api router
user_router = APIRouter()


async def _fetch_user_record(
    db: Any,
    guid: UUID,
    not_found_detail: str,
    failure_detail: str,
    log_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Retrieve a single user record or raise an HTTPException.

    Args:
        db: Database client.
        guid: Identifier of the user to fetch.
        not_found_detail: Message returned when the user does not exist.
        failure_detail: Message returned when the database query fails.
        log_context: Extra context for the log record.

    Returns:
        The first matching user record as a dictionary.

    Raises:
        HTTPException: 404 when missing, 500 on query failures.
    """

    try:
        result = await run_in_threadpool(
            lambda: db.table(USER_TABLE_NAME).select("*").eq("id", str(guid)).execute()
        )
    except Exception as exc:
        logger.exception("Failed to fetch user", extra=log_context)
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


@user_router.get("/health", response_model=MessageResponse)
async def health_check() -> MessageResponse:
    """Quick liveness probe for the user service."""

    return MessageResponse(status=status.HTTP_200_OK, message="User service is healthy")


@user_router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(user: User, db=Depends(get_db)) -> UserResponse:
    """
    Add a User to the database if not already present.

    Args:
        user: User payload to persist.
        db: Supabase client injected via dependency.

    Returns:
        UserResponse wrapping the created user.
    """

    normalized_user = user.model_copy(update={"email": user.email.strip()})

    try:
        existing = await run_in_threadpool(
            lambda: db.table(USER_TABLE_NAME)
            .select("*")
            .eq("email", normalized_user.email)
            .execute()
        )
    except Exception as exc:
        logger.exception(
            "Failed to query existing users by email", extra={"email": normalized_user.email}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create user due to an internal error.",
        ) from exc

    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {normalized_user.email} already exists",
        )

    try:
        insert_result = await run_in_threadpool(
            lambda: db.table(USER_TABLE_NAME).insert(normalized_user.to_dict()).execute()
        )
    except APIError as exc:
        error_code = getattr(exc, "code", None)
        status_code_value = getattr(exc, "status_code", None)
        if _is_unique_violation(exc):
            logger.info(
                "Duplicate user creation blocked by unique constraint",
                extra={
                    "email": normalized_user.email,
                    "error_code": error_code,
                    "status_code": status_code_value,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {normalized_user.email} already exists",
            ) from exc

        logger.exception(
            "Failed to insert user", extra={"email": normalized_user.email, "error_code": error_code}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create user due to an internal error.",
        ) from exc
    except Exception as exc:
        logger.exception("Failed to insert user", extra={"email": normalized_user.email})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create user due to an internal error.",
        ) from exc

    created_payload = insert_result.data[0] if insert_result.data else normalized_user.to_dict()
    created_user = User(**created_payload)  # type: ignore
    logger.info(
        "User created", extra={"user_id": str(created_user.id), "email": created_user.email}
    )
    return UserResponse(status=status.HTTP_201_CREATED, user=created_user)


@user_router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user(user_id: str, db=Depends(get_db)) -> UserResponse:
    """
    Retrieve a single user by identifier.

    Args:
        user_id: UUID4 of the target user (path parameter).
        db: Supabase client injected via dependency.

    Returns:
        UserResponse wrapping the requested user.
    """

    guid = _parse_user_id(user_id, logger, USER)

    record = await _fetch_user_record(
        db,
        guid,
        not_found_detail=f"No user found with id {user_id}",
        failure_detail="Unable to retrieve user due to an internal error.",
        log_context={"user_id": user_id},
    )

    user_record = User(**record)
    logger.info("User retrieved", extra={"user_id": user_id})
    return UserResponse(status=status.HTTP_200_OK, user=user_record)


@user_router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user(user_id: str, fields: UserFields, db=Depends(get_db)) -> UserResponse:
    """
    Update mutable fields on an existing user.

    Args:
        user_id: UUID4 of the user to update.
        fields: Partial update payload with allowed fields.
        db: Supabase client injected via dependency.

    Returns:
        UserResponse wrapping the updated user.
    """

    guid = _parse_user_id(user_id, logger, USER)
    updates = fields.model_dump(exclude_unset=True, exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update.",
        )

    _ = await _fetch_user_record(
        db,
        guid,
        not_found_detail=f"No user found with id {user_id}",
        failure_detail="Unable to update user due to an internal error.",
        log_context={"user_id": user_id},
    )

    try:
        await run_in_threadpool(
            lambda: db.table(USER_TABLE_NAME)
            .update(updates)
            .eq("id", str(guid))
            .execute()
        )
    except Exception as exc:
        logger.exception("Failed to update user", extra={"user_id": user_id, "updates": updates})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update user due to an internal error.",
        ) from exc

    refreshed = await _fetch_user_record(
        db,
        guid,
        not_found_detail=f"No user found with id {user_id}",
        failure_detail="Unable to update user due to an internal error.",
        log_context={"user_id": user_id},
    )
    updated_user = User(**refreshed)
    logger.info("User updated", extra={"user_id": user_id})
    return UserResponse(status=status.HTTP_200_OK, user=updated_user)


@user_router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_user(user_id: str, db=Depends(get_db)) -> MessageResponse:
    """
    Delete an existing user by identifier.

    Args:
        user_id: UUID4 of the user to delete.
        db: Supabase client injected via dependency.

    Returns:
        MessageResponse confirming deletion.
    """

    guid = _parse_user_id(user_id, logger, USER)

    _ = await _fetch_user_record(
        db,
        guid,
        not_found_detail=f"No user found with id {user_id}",
        failure_detail="Unable to delete user due to an internal error.",
        log_context={"user_id": user_id},
    )

    try:
        await run_in_threadpool(
            lambda: db.table(USER_TABLE_NAME)
            .delete()
            .eq("id", str(guid))
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to delete user", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete user due to an internal error.",
        ) from exc

    logger.info("User deleted", extra={"user_id": user_id})
    return MessageResponse(status=status.HTTP_200_OK, message=f"User {user_id} deleted")

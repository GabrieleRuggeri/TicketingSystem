"""Shared API request and response models for the Ticketing System."""

from typing import Optional, Literal

from pydantic import BaseModel

from Users.user import User


class UserFields(BaseModel):
    """Payload accepted when updating an existing user."""

    name: Optional[str] = None
    surname: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None


class MessageResponse(BaseModel):
    """Envelope for simple string responses."""

    status: int
    message: str


class UserResponse(BaseModel):
    """Envelope for responses that include a user resource."""

    status: int
    user: User


# Backwards compatibility for callers still importing TSResponse.
class TSResponse(MessageResponse):
    """Deprecated alias for MessageResponse."""

    pass

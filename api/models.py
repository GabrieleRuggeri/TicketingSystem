"""Shared API request and response models for the Ticketing System."""

from typing import Optional, Literal

from pydantic import BaseModel

from Users.user import User
from Hotels.structure import Hotel, Room


class UserFields(BaseModel):
    """Payload accepted when updating an existing user."""

    name: Optional[str] = None
    surname: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None

class HotelFields(BaseModel):
    """Payload accepted when updating an existing hotel."""

    name : Optional[str] = None 
    phone_number : Optional[str] = None
    email : Optional[str] = None
    address : Optional[str] = None 
    city : Optional[str] = None
    country : Optional[str] = None


class MessageResponse(BaseModel):
    """Envelope for simple string responses."""

    status: int
    message: str


class UserResponse(BaseModel):
    """Envelope for responses that include a user resource."""

    status: int
    user: User

class HotelResponse(BaseModel):
    """Envelope for responses that include a hotel resource."""

    status: int
    hotel: Hotel

class RoomListResponse(BaseModel):
    """Envelope for responses that include a list of rooms resource."""

    status: int
    rooms: list[Room]

# Backwards compatibility for callers still importing TSResponse.
class TSResponse(MessageResponse):
    """Deprecated alias for MessageResponse."""

    pass

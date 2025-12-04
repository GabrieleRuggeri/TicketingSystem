"""Testing guidance for every Pydantic model.

Each test below exercises both the happy-path construction and the validation
errors for a specific model. When introducing a new Pydantic model, add a new
test that instantiates it with valid data and asserts the validators by feeding
invalid payloads as well.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Hotels.booking import Booking, BookingRequestResponse  # noqa: E402
from Hotels.structure import Hotel, Room  # noqa: E402
from Users.user import User  # noqa: E402


def test_user_email_normalization_and_validation() -> None:
    """Ensure a valid User email is normalized to lowercase."""
    user = User(
        name="Ada",
        surname="Lovelace",
        email="Ada.Lovelace@Example.COM",
        phone_number="+1-555-000",
        status="active",
    )

    assert user.email == "ada.lovelace@example.com"


def test_user_invalid_email_raises_value_error() -> None:
    """Ensure User rejects malformed email addresses."""
    with pytest.raises(ValueError, match="Invalid email address format"): # type: ignore
        User(
            name="Ada",
            surname="Lovelace",
            email="invalid-email",
            phone_number="+1-555-000",
            status="active",
        )


def test_room_rejects_non_positive_price() -> None:
    """Ensure the Room validator enforces positive pricing."""
    with pytest.raises(ValueError, match="Room price must be a positive integer"):
        Room(
            hotel_id=uuid4(),
            number="101",
            size="double",
            price=0,
        )


def test_room_accepts_valid_payload() -> None:
    """Ensure Room creation succeeds with a valid payload."""
    room = Room(
        hotel_id=uuid4(),
        number="101",
        size="double",
        price=150,
    )

    assert room.price == 150


def test_hotel_validates_timestamp_ordering() -> None:
    """Ensure Hotel raises when last_modified_at precedes created_at."""
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="date2 must be greater"): # type: ignore
        Hotel(
            name="Palace",
            phone_number="+1-000",
            email="palace@example.com",
            address="1 Main Street",
            city="City",
            country="Country",
            created_at=created_at,
            last_modified_at=created_at - timedelta(hours=1),
        )


def test_hotel_creation_sets_defaults() -> None:
    """Ensure Hotel stores provided metadata and timestamps."""
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    updated_at = created_at + timedelta(hours=1)
    hotel = Hotel(
        name="Palace",
        phone_number="+1-000",
        email="palace@example.com",
        address="1 Main Street",
        city="City",
        country="Country",
        created_at=created_at,
        last_modified_at=updated_at,
    )

    assert hotel.created_at == created_at
    assert hotel.last_modified_at == updated_at


def test_booking_duration_and_status_update() -> None:
    """Ensure Booking computes duration and updates its status."""
    start_date = datetime(2024, 5, 1, tzinfo=timezone.utc)
    end_date = start_date + timedelta(days=3)
    booking = Booking(
        guest_id=uuid4(),
        room_id=uuid4(),
        status="pending",
        start_date=start_date,
        end_date=end_date,
        duration=0,
    )
    prior_last_modified = booking.last_modified_at

    assert booking.duration == 3

    booking.update_status("confirmed")

    assert booking.status == "confirmed"
    assert booking.last_modified_at >= prior_last_modified


def test_booking_validates_dates_and_timestamps() -> None:
    """Ensure Booking enforces both stay range ordering and audit timestamps."""
    start_date = datetime(2024, 5, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="end_date must be strictly greater"): # type: ignore
        Booking(
            guest_id=uuid4(),
            room_id=uuid4(),
            status="confirmed",
            start_date=start_date,
            end_date=start_date,
            duration=0,
        )

    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="has invalid timestamps"): # type: ignore
        Booking(
            guest_id=uuid4(),
            room_id=uuid4(),
            status="pending",
            start_date=start_date,
            end_date=start_date + timedelta(days=1),
            duration=0,
            created_at=created_at,
            last_modified_at=created_at - timedelta(minutes=1),
        )


def test_booking_request_response_handles_optional_reasoning() -> None:
    """Ensure BookingRequestResponse supports optional denial reasons."""
    denied_response = BookingRequestResponse(
        booking_id=uuid4(),
        status="denied",
        reason_for_deny="No rooms available",
    )
    confirmed_response = BookingRequestResponse(
        booking_id=uuid4(),
        status="confirmed",
        reason_for_deny=None,
    )

    assert denied_response.reason_for_deny == "No rooms available"
    assert confirmed_response.reason_for_deny is None

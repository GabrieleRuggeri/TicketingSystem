from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timedelta, timezone  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from Hotels.booking import Booking, BookingPeriod  # noqa: E402
from Hotels.structure import Room, Hotel  # noqa: E402


def _room_kwargs(size: str = "double") -> dict:
    return {"id": uuid4(), "number": "101", "size": size}


def _structure_kwargs(
    *, created_at: datetime | None = None, last_modified_at: datetime | None = None
) -> dict:
    created = created_at or datetime.now(timezone.utc)
    last = last_modified_at or created + timedelta(minutes=5)
    return {
        "id": uuid4(),
        "name": "Test Structure",
        "phone_number": None,
        "email": None,
        "address": "1 Testing Way",
        "bookings": [uuid4()],
        "city": "Test City",
        "country": "Testland",
        "created_at": created,
        "last_modified_at": last,
    }


def _booking_kwargs(
    *,
    status: str = "confirmed",
    created_at: datetime | None = None,
    last_modified_at: datetime | None = None,
    period: BookingPeriod | dict | None = None,
) -> dict:
    created = created_at or datetime.now(timezone.utc)
    last = last_modified_at or created + timedelta(minutes=1)
    booking_period = period or BookingPeriod(start_date=created, end_date=created + timedelta(days=1))
    return {
        "id": uuid4(),
        "guest_id": uuid4(),
        "room_id": uuid4(),
        "period": booking_period,
        "created_at": created,
        "last_modified_at": last,
        "status": status,
    }


@pytest.mark.parametrize("size", ["single", "double", "triple", "quadruple", "multiple"])
def test_room_accepts_each_supported_size(size: str):
    room = Room(**_room_kwargs(size=size))
    assert room.size == size


def test_room_rejects_invalid_size_literal():
    with pytest.raises(ValidationError):
        Room(**_room_kwargs(size="penthouse"))


def test_structure_accepts_optional_contact_fields():
    data = _structure_kwargs()
    data["phone_number"] = "555-1234"
    data["email"] = "hello@example.com"
    structure = Hotel(**data)
    assert structure.phone_number == "555-1234"
    assert structure.email == "hello@example.com"


def test_structure_validates_chronological_timestamps():
    data = _structure_kwargs()
    data["last_modified_at"] = data["created_at"] - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        Hotel(**data)


def test_structure_allows_equal_timestamps():
    created = datetime.now(timezone.utc)
    structure = Hotel(**_structure_kwargs(created_at=created, last_modified_at=created))
    assert structure.created_at == structure.last_modified_at


def test_structure_requires_uuid_bookings():
    data = _structure_kwargs()
    data["bookings"] = ["not-a-uuid"]
    with pytest.raises(ValidationError):
        Hotel(**data)


def test_booking_period_requires_strictly_increasing_dates():
    start = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        BookingPeriod(start_date=start, end_date=start)


def test_booking_period_accepts_valid_range():
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=3)
    period = BookingPeriod(start_date=start, end_date=end)
    assert period.end_date == end


def test_booking_accepts_valid_status_and_timestamps():
    booking = Booking(**_booking_kwargs())
    assert booking.status == "confirmed"
    assert booking.last_modified_at >= booking.created_at


@pytest.mark.parametrize("status", ["confirmed", "pending", "cancelled"])
def test_booking_accepts_all_supported_statuses(status: str):
    booking = Booking(**_booking_kwargs(status=status))
    assert booking.status == status


def test_booking_rejects_unknown_status():
    with pytest.raises(ValidationError):
        Booking(**_booking_kwargs(status="on_hold"))


def test_booking_validates_timestamp_order():
    created = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        Booking(**_booking_kwargs(created_at=created, last_modified_at=created - timedelta(seconds=1)))


def test_booking_accepts_equal_timestamps():
    created = datetime.now(timezone.utc)
    booking = Booking(**_booking_kwargs(created_at=created, last_modified_at=created))
    assert booking.created_at == booking.last_modified_at


def test_booking_rejects_invalid_nested_period():
    start = datetime.now(timezone.utc)
    period = {"start_date": start, "end_date": start}
    with pytest.raises(ValidationError):
        Booking(**_booking_kwargs(period=period))

"""Tests for hotel, booking, user models and helper utilities."""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timedelta, timezone  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from Hotels.booking import Booking, BookingPeriod  # noqa: E402
from Hotels.structure import Room, Hotel  # noqa: E402
from Users.user import User  # noqa: E402
from utils import are_overlapping  # noqa: E402


def _booking_period(
    start: datetime | None = None,
    end: datetime | None = None,
) -> BookingPeriod:
    """Build a booking period with a default one-day span."""
    start_date = start or datetime.now(timezone.utc)
    end_date = end or start_date + timedelta(days=1)
    return BookingPeriod(start_date=start_date, end_date=end_date, duration=0)


def _room_kwargs(size: str = "double", room_number: str = "101") -> dict:
    """Factory for Room kwargs."""
    return {"id": uuid4(), "number": room_number, "size": size, "price": 100.0}


def _booking_kwargs(
    *,
    status: str = "pending",
    created_at: datetime | None = None,
    last_modified_at: datetime | None = None,
    period: BookingPeriod | dict | None = None,
    room_id: UUID | None = None,
    booking_id: UUID | None = None,
) -> dict:
    """Factory for Booking kwargs with defaults suitable for tests."""
    created = created_at or datetime.now(timezone.utc)
    last = last_modified_at or created
    booking_period = period or _booking_period()
    return {
        "id": booking_id or uuid4(),
        "guest_id": uuid4(),
        "room_id": room_id or uuid4(),
        "period": booking_period,
        "created_at": created,
        "last_modified_at": last,
        "status": status,
    }


def _hotel_kwargs(
    *,
    created_at: datetime | None = None,
    last_modified_at: datetime | None = None,
    bookings: list[Booking] | None = None,
    rooms: list[Room] | None = None,
) -> dict:
    """Factory for Hotel kwargs with optional room and booking lists."""
    created = created_at or datetime.now(timezone.utc)
    last = last_modified_at or created + timedelta(minutes=5)
    hotel_rooms = rooms or [Room(**_room_kwargs())]
    return {
        "id": uuid4(),
        "name": "Test Hotel",
        "phone_number": None,
        "email": None,
        "address": "1 Testing Way",
        "bookings": bookings or [],
        "city": "Test City",
        "country": "Testland",
        "created_at": created,
        "last_modified_at": last,
        "rooms": hotel_rooms,
    }


def _user_kwargs(
    *,
    email: str = "john@doe.com",
    bookings: list[Booking] | None = None,
) -> dict:
    """Factory for User kwargs with sensible defaults."""
    return {
        "name": "John",
        "surname": "Doe",
        "email": email,
        "phone_number": None,
        "bookings": bookings,
    }


@pytest.mark.parametrize("size", ["single", "double", "triple", "quadruple", "multiple"])
def test_room_accepts_each_supported_size(size: str):
    """Accept each allowed room size literal."""
    room = Room(**_room_kwargs(size=size))
    assert room.size == size


def test_room_rejects_invalid_size_literal():
    """Reject unsupported room size literal."""
    with pytest.raises(ValidationError):
        Room(**_room_kwargs(size="penthouse"))


def test_structure_accepts_optional_contact_fields():
    """Accept optional phone and email fields."""
    data = _hotel_kwargs()
    data["phone_number"] = "555-1234"
    data["email"] = "hello@example.com"
    structure = Hotel(**data)
    assert structure.phone_number == "555-1234"
    assert structure.email == "hello@example.com"


def test_structure_validates_chronological_timestamps():
    """Reject hotel when last_modified_at precedes created_at."""
    data = _hotel_kwargs()
    data["last_modified_at"] = data["created_at"] - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        Hotel(**data)


def test_structure_allows_equal_timestamps():
    """Allow equal created and modified timestamps."""
    created = datetime.now(timezone.utc)
    structure = Hotel(**_hotel_kwargs(created_at=created, last_modified_at=created))
    assert structure.created_at == structure.last_modified_at


def test_structure_requires_booking_objects():
    """Reject hotel when bookings contain non-Booking entries."""
    data = _hotel_kwargs()
    data["bookings"] = ["not-a-booking"]
    with pytest.raises(ValidationError):
        Hotel(**data)


def test_booking_period_requires_strictly_increasing_dates():
    """Reject booking period with identical start and end."""
    start = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        BookingPeriod(start_date=start, end_date=start, duration=0)


def test_booking_period_computes_duration():
    """Compute duration in days after model init."""
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=3)
    period = BookingPeriod(start_date=start, end_date=end, duration=0)
    assert period.duration == 3


def test_are_overlapping_detects_overlap_and_non_overlap():
    """Validate overlap helper for overlapping and disjoint periods."""
    start = datetime.now(timezone.utc)
    period1 = _booking_period(start=start, end=start + timedelta(days=2))
    period2 = _booking_period(start=start + timedelta(days=3), end=start + timedelta(days=5))
    period3 = _booking_period(start=start + timedelta(days=1), end=start + timedelta(days=4))

    assert are_overlapping(period1, period2) is False
    assert are_overlapping(period1, period3) is True


def test_booking_accepts_valid_status_and_timestamps():
    """Accept booking defaults and timestamp ordering."""
    booking = Booking(**_booking_kwargs())
    assert booking.status == "pending"
    assert booking.last_modified_at >= booking.created_at


@pytest.mark.parametrize("status", ["confirmed", "pending", "cancelled"])
def test_booking_accepts_all_supported_statuses(status: str):
    """Allow all supported booking statuses."""
    booking = Booking(**_booking_kwargs(status=status))
    assert booking.status == status


def test_booking_rejects_unknown_status():
    """Reject unsupported booking status values."""
    with pytest.raises(ValidationError):
        Booking(**_booking_kwargs(status="on_hold"))


def test_booking_validates_timestamp_order():
    """Reject booking when last_modified_at precedes created_at."""
    created = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        Booking(**_booking_kwargs(created_at=created, last_modified_at=created - timedelta(seconds=1)))


def test_booking_accepts_equal_timestamps():
    """Allow equal created and last_modified timestamps."""
    created = datetime.now(timezone.utc)
    booking = Booking(**_booking_kwargs(created_at=created, last_modified_at=created))
    assert booking.created_at == booking.last_modified_at


def test_booking_update_status_sets_status_and_timestamp():
    """Update booking status and refresh timestamp."""
    booking = Booking(**_booking_kwargs(status="pending"))
    before = booking.last_modified_at
    booking.update_status("confirmed")
    assert booking.status == "confirmed"
    assert booking.last_modified_at >= before


def test_booking_rejects_invalid_nested_period():
    """Propagate nested period validation errors."""
    start = datetime.now(timezone.utc)
    period = {"start_date": start, "end_date": start, "duration": 0}
    with pytest.raises(ValidationError):
        Booking(**_booking_kwargs(period=period))


def test_user_email_is_normalized_to_lowercase():
    """Normalize user email to lowercase."""
    user = User(**_user_kwargs(email="JOHN@DOE.COM"))
    assert user.email == "john@doe.com"


def test_user_requires_valid_email():
    """Reject invalid email addresses."""
    with pytest.raises(ValidationError):
        User(**_user_kwargs(email="not-an-email"))


def test_user_add_booking_initializes_when_missing():
    """Initialize bookings list when None and append booking."""
    user = User(**_user_kwargs(bookings=None))
    booking = Booking(**_booking_kwargs())
    user.add_booking(booking)
    assert user.bookings == [booking]


def test_user_remove_booking_when_none_raises():
    """Raise error when removing booking from None bookings list."""
    user = User(**_user_kwargs(bookings=None))
    booking = Booking(**_booking_kwargs())
    with pytest.raises(ValueError):
        user.remove_booking(booking)


def test_user_remove_booking_removes_existing():
    """Remove booking when it exists."""
    booking = Booking(**_booking_kwargs())
    user = User(**_user_kwargs(bookings=[booking]))
    user.remove_booking(booking)
    assert booking not in user.bookings


def test_hotel_book_rejects_non_pending_booking_status():
    """Raise error when booking is not pending."""
    hotel = Hotel(**_hotel_kwargs())
    booking = Booking(**_booking_kwargs(status="confirmed", room_id=hotel.rooms[0].id))
    with pytest.raises(ValueError):
        hotel.book(booking)


def test_hotel_book_denies_duplicate_booking():
    """Deny duplicate booking IDs."""
    hotel = Hotel(**_hotel_kwargs())
    existing = Booking(**_booking_kwargs(status="pending", room_id=hotel.rooms[0].id))
    hotel.bookings.append(existing)

    duplicate = Booking(**_booking_kwargs(status="pending", room_id=hotel.rooms[0].id, booking_id=existing.id))

    response = hotel.book(duplicate)
    assert response.status == "denied"
    assert "already exists" in response.reason_for_deny
    assert len(hotel.bookings) == 1


def test_hotel_book_denies_unknown_room():
    """Deny bookings for rooms not in the hotel."""
    hotel = Hotel(**_hotel_kwargs())
    booking = Booking(**_booking_kwargs(status="pending", room_id=uuid4()))
    response = hotel.book(booking)
    assert response.status == "denied"
    assert "does not exist" in response.reason_for_deny


def test_hotel_book_denies_overlapping_period():
    """Deny bookings when requested period overlaps existing reservations."""
    start = datetime.now(timezone.utc)
    room = Room(**_room_kwargs(room_number="201"))
    existing = Booking(
        **_booking_kwargs(
            status="confirmed",
            room_id=room.id,
            period=_booking_period(start=start, end=start + timedelta(days=2)),
        )
    )
    hotel = Hotel(**_hotel_kwargs(rooms=[room], bookings=[existing]))

    pending_overlap = Booking(
        **_booking_kwargs(
            status="pending",
            room_id=room.id,
            period=_booking_period(start=start + timedelta(days=1), end=start + timedelta(days=3)),
        )
    )
    response = hotel.book(pending_overlap)
    assert response.status == "denied"
    assert "not available" in response.reason_for_deny
    assert len(hotel.bookings) == 1


def test_hotel_book_confirms_when_available():
    """Confirm pending booking when room exists and period is free."""
    start = datetime.now(timezone.utc)
    room = Room(**_room_kwargs(room_number="301"))
    existing = Booking(
        **_booking_kwargs(
            status="confirmed",
            room_id=room.id,
            period=_booking_period(start=start, end=start + timedelta(days=2)),
        )
    )
    hotel = Hotel(**_hotel_kwargs(rooms=[room], bookings=[existing]))

    pending_non_overlap = Booking(
        **_booking_kwargs(
            status="pending",
            room_id=room.id,
            period=_booking_period(start=start + timedelta(days=3), end=start + timedelta(days=4)),
        )
    )
    response = hotel.book(pending_non_overlap)

    assert response.status == "confirmed"
    assert pending_non_overlap in hotel.bookings
    assert pending_non_overlap.status == "confirmed"

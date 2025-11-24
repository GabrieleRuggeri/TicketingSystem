"""User model with booking helpers."""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from email.utils import parseaddr                                  # noqa: E402
from pydantic import BaseModel, Field, field_validator              # noqa: E402
from typing import Optional                                         # noqa: E402
from uuid import UUID, uuid4                                      # noqa: E402
from Hotels.booking import Booking                                # noqa: E402


class User(BaseModel):
    """Application user with contact info and booking references."""

    id: UUID = Field(default_factory=uuid4, frozen=True)
    name: str
    surname: str
    email: str
    phone_number: Optional[str]
    bookings: Optional[list[Booking]] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, value: str) -> str:
        """
        Normalize and validate email to lowercase.

        Args:
            value: Input email string.

        Returns:
            Lowercased email string if valid.

        Raises:
            ValueError: If the email address is malformed.
        """
        lowered = value.lower()
        parsed = parseaddr(lowered)[1]
        if "@" not in parsed or parsed != lowered:
            raise ValueError("Invalid email address format.")
        return lowered

    def add_booking(self, booking: Booking) -> None:
        """Add a booking to the user's bookings list."""
        if self.bookings is None:
            self.bookings = []
        self.bookings.append(booking)

    def remove_booking(self, booking: Booking) -> None:
        """Remove a booking from the user's bookings list."""
        if self.bookings is None:
            raise ValueError("No bookings to remove from.")

        if booking in self.bookings:
            self.bookings.remove(booking)

    def get_bookings(self) -> list[Booking]:
        """Retrieve the user's bookings list."""
        return self.bookings if self.bookings is not None else []
    

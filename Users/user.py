"""User model with booking helpers."""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from email.utils import parseaddr                                  # noqa: E402
from pydantic import BaseModel, Field, field_validator              # noqa: E402
from typing import Literal, Optional                                         # noqa: E402
from uuid import UUID, uuid4                                      # noqa: E402
from Hotels.booking import Booking                                # noqa: E402


class User(BaseModel):
    """Application user with contact info and booking references."""

    id: UUID = Field(default_factory=uuid4, frozen=True)
    name: str
    surname: str
    email: str
    phone_number: str
    status: Literal["active", "inactive"]

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
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "surname": self.surname,
            "email": self.email,
            "phone_number": self.phone_number,
            "status": self.status
            }
    

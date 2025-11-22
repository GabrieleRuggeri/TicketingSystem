from uuid import UUID, uuid4
from typing import Any, Literal, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, model_validator
from utils import validate_timestamps

class BookingPeriod(BaseModel):

    start_date : datetime
    end_date : datetime
    duration : int

    def model_post_init(self, context: Any) -> None:
        self.duration = (self.end_date - self.start_date).days

    @model_validator(mode="after")
    def validate_dates(self):
        # enforce chronological consistency
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be strictly greater than start_date")
        return self
    
class Booking(BaseModel):
    
    id : UUID = Field(default_factory=lambda: uuid4(), frozen=True)
    guest_id : UUID
    room_id : UUID
    period : BookingPeriod
    created_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified_at : datetime
    status : Literal['confirmed', 'pending', 'cancelled']

    @model_validator(mode = "after")
    def validate_booking(self):
        # enforce chronological consistency
        validate_timestamps(self.created_at, self.last_modified_at)
        return self
    
    def update_status(self, new_status: Literal['confirmed', 'cancelled']):
        ''' Update the status of the booking. '''
        self.status = new_status
        self.last_modified_at = datetime.now(timezone.utc)
    
class BookingRequestResponse(BaseModel):

    booking_id : UUID = Field(description="Booking() unique identifier")
    status : Literal['confirmed', 'denied']
    reason_for_deny : Optional[str]
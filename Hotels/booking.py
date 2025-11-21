from uuid import UUID
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, model_validator
from utils import validate_timestamps

class BookingPeriod(BaseModel):

    start_date : datetime
    end_date : datetime

    @model_validator(mode="after")
    def validate_dates(self):
        # enforce chronological consistency
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be strictly greater than start_date")
        return self
    
class Booking(BaseModel):
    
    id : UUID
    guest_id : UUID
    room_id : UUID
    period : BookingPeriod
    created_at : datetime
    last_modified_at : datetime
    status : Literal['confirmed', 'pending', 'cancelled']

    @model_validator(mode = "after")
    def validate_booking(self):
        # enforce chronological consistency
        validate_timestamps(self.created_at, self.last_modified_at)
        return self
'''
Structure class implementation for Hotels module.
'''
from uuid import UUID, uuid4
from typing import Literal, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, model_validator, Field
from utils import validate_timestamps
from Hotels.booking import Booking, BookingRequestResponse
from utils import are_overlapping

class Room(BaseModel):

    id : UUID = Field(default_factory=lambda: uuid4(), frozen=True)
    number : str 
    size : Literal['single', 'double', 'triple', 'quadruple', 'multiple']
    price : float

class Hotel(BaseModel):

    id : UUID = Field(default_factory=lambda: uuid4(), frozen=True)
    name : str 
    phone_number : Optional[str] 
    email : Optional[str]
    address : str 
    bookings : list[Booking]
    city : str
    country : str
    created_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc), frozen=True)
    last_modified_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rooms : list[Room]

    @model_validator(mode="after")
    def validate_structure(self):
        # enforce chronological consistency
        validate_timestamps(self.created_at, self.last_modified_at)
        return self
    
    def book(self, booking: Booking) -> BookingRequestResponse:
        ''' Add a booking to the hotel's bookings list. 

        Prerequisites:
        - if the booking already exists in the list, do not add it again.
        - if the room does not exist in the hotel, raise an error.
        - if the period requested is not available, raise an error.
        '''

        if booking.status in ('confirmed', 'cancelled'):
            raise ValueError(f"Booking {booking.id} status must be 'pending' to proceed with booking.")

        # check if booking already exists
        if booking.id in [reservation.id for reservation in self.bookings]:
            return  BookingRequestResponse(booking_id=booking.id, status='denied', reason_for_deny='Booking already exists.')
        
        # check if room exists in hotel
        if booking.room_id not in [room.id for room in self.rooms]:
            return BookingRequestResponse(booking_id=booking.id, status='denied', reason_for_deny=f'Room {booking.room_id} does not exist in the hotel.')
        
        # check if room is available in the requested period
        booked_periods = [reservation.period for reservation in self.bookings if reservation.room_id == booking.room_id and reservation.status != 'cancelled']
        for period in booked_periods:
            if are_overlapping(period, booking.period):
                return BookingRequestResponse(booking_id=booking.id, status='denied', reason_for_deny='Requested period is not available.')
        
        # if all checks pass, add the booking
        self.bookings.append(booking)
        booking.update_status('confirmed')
        return BookingRequestResponse(booking_id=booking.id, status='confirmed', reason_for_deny=None)


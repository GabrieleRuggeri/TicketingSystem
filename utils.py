from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from Hotels.booking import BookingPeriod
else:
    BookingPeriod = Any

def validate_timestamps(date1: datetime, date2: datetime):
    '''Validate that date2 is greater than date1.'''
    if date2 < date1:
        raise ValueError("date2 must be greater than or equal to date1")

def are_overlapping(period1: BookingPeriod, period2: BookingPeriod) -> bool:
    '''Check if two booking periods overlap.'''
    end1 = period1.start_date + timedelta(days=period1.duration)
    end2 = period2.start_date + timedelta(days=period2.duration)
    return period1.start_date < end2 and period2.start_date < end1

from datetime import datetime

def validate_timestamps(date1: datetime, date2: datetime):
    '''Validate that date2 is greater than date1.'''
    if date2 < date1:
        raise ValueError("date2 must be greater than or equal to date1")

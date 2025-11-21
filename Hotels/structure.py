'''
Structure class implementation for Hotels module.
'''
from uuid import UUID
from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel, model_validator
from utils import validate_timestamps

class Room(BaseModel):

    id : UUID
    number : str 
    size : Literal['single', 'double', 'triple', 'quadruple', 'multiple']

class Hotel(BaseModel):

    id : UUID
    name : str 
    phone_number : Optional[str] 
    email : Optional[str]
    address : str 
    bookings : list[UUID]
    city : str
    country : str
    created_at : datetime
    last_modified_at : datetime

    @model_validator(mode="after")
    def validate_structure(self):
        # enforce chronological consistency
        validate_timestamps(self.created_at, self.last_modified_at)
        return self
    

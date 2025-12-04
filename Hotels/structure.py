'''
Structure class implementation for Hotels module.
'''
from uuid import UUID, uuid4
from typing import Literal
from datetime import datetime, timezone
from pydantic import BaseModel, model_validator, Field
from utils import validate_timestamps

class Room(BaseModel):

    id : UUID = Field(default_factory=lambda: uuid4(), frozen=True)
    hotel_id : UUID = Field(frozen=True)
    number : str 
    size : Literal['single', 'double', 'triple', 'quadruple', 'multiple']
    price : int

    @model_validator(mode="after")
    def validate_structure(self):
        # enforce positive price
        if self.price <= 0:
            raise ValueError("Room price must be a positive integer.")
        return self

class Hotel(BaseModel):

    id : UUID = Field(default_factory=lambda: uuid4(), frozen=True)
    name : str 
    phone_number : str
    email : str
    address : str 
    city : str
    country : str
    created_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc), frozen=True)
    last_modified_at : datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_structure(self):
        # enforce chronological consistency
        validate_timestamps(self.created_at, self.last_modified_at)
        return self


from pydantic import BaseModel
from typing import Optional, Literal

class UserFields(BaseModel):
    '''Campi utent modificabili'''
    name: Optional[str] = None
    surname: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None

class TSResponse(BaseModel):
    '''API response model'''
    status: int
    result: str
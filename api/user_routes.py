from fastapi import APIRouter, HTTPException
from Users.user import User

user_router = APIRouter()

@user_router.get("health")
async def health_check():
    return {"status": "User service is healthy"}
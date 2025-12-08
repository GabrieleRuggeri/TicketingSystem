from fastapi import APIRouter
from postgrest.base_request_builder import APIResponse
from Users.user import User
from Database.db import TicketingDB
import json

# mount api router
user_router = APIRouter()

# create database connection
try:
    db = TicketingDB().client
except Exception as e:
    raise RuntimeError(f"Failed to connect to the database: {e}")

@user_router.get("/health")
async def health_check():
    return {"status": "User service is healthy"}

@user_router.post("/create_user")
async def create_user(user: User) -> str:
    '''
    Add a User to the database if not already present.

    Steps:
    1. check if user already exixts
    2. if not, add user to the database
    '''

    # check for the same email in the db
    result: APIResponse = db.table("users").select("*").eq("email", user.email.strip()).execute()
    if len(result.data) > 0:
        return json.dumps({"result": f"User with email {user.email} already exists","status": 409})
    else:
        result = db.table("users").insert(json.dumps(user)).execute()
        return json.dumps( {"result": f"User {user} created", "status": 200} )


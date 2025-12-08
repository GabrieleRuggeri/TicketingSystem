from fastapi import APIRouter, Depends
from postgrest.base_request_builder import APIResponse
from Users.user import User
from Database.db import TicketingDB
from Database.deps import get_db
from uuid import UUID
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
async def create_user(user: User, db = Depends(get_db)) -> str:
    '''Add a User to the database if not already present.'''

    # check for the same email in the db
    result: APIResponse = db.table("users").select("*").eq("email", user.email.strip()).execute()
    if len(result.data) > 0:
        return json.dumps({"result": f"User with email {user.email} already exists","status": 409})
    else:
        result = db.table("users").insert(user.to_dict()).execute()
        return json.dumps( {"result": f"User {user} created", "status": 200} )
    
@user_router.get("/get_user")
async def get_user(id: str, db = Depends(get_db)) -> str:
    try:
        guid = UUID(id, version=4)
    except Exception as e:
        return json.dumps({"result": f"Input id {id} is not a valid guid: {e}", "status": 400})
    
    # query the database
    result = db.table("users").select("*").eq("id", str(guid)).execute()
    if len(result.data)>0:
        user = result.data[0]
        return json.dumps({"result": f"{user}","status": 200})
    else:
        return json.dumps({"result": f"No user found with id {id}","status": 404})

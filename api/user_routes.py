from uuid import UUID
import json
from .models import TSResponse, UserFields
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi import status

from Users.user import User
from Database.deps import get_db

import logging
logger = logging.getLogger(__name__)

USER_TABLE_NAME = "users"


# mount api router
user_router = APIRouter()

@user_router.get("/health")
async def health_check():
    return {"status": "User service is healthy"}

@user_router.post("/create_user", response_model=TSResponse)
async def create_user(user: User, db = Depends(get_db)) -> TSResponse:
    '''Add a User to the database if not already present.'''

    # check for the same email in the db
    try:
        result = db.table(USER_TABLE_NAME).select("*").eq("email", user.email.strip()).execute()
    except Exception as e:
        logger.error("User retrieve error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}"
        ) from e
    
    if len(result.data) > 0:
        logger.error("User already exists")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user.email} already exists"
        ) 
    else:
        try:
            result = db.table(USER_TABLE_NAME).insert(user.to_dict()).execute()
        except Exception as e:
            logger.error("User creation error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {e}"
            ) from e
        
    logger.info("User created")
    return TSResponse(result=f"User {user} created",status=201) 
    
@user_router.get("/get_user", response_model=TSResponse)
async def get_user(id: str, db = Depends(get_db)) -> TSResponse:

    try:
        guid = UUID(id, version=4)
    except Exception as e:
        logger.exception("Invalid GUID")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input id {id} is not a valid guid: {e}"
        ) from e
        
    # query the database
    try:
        result = db.table(USER_TABLE_NAME).select("*").eq("id", str(guid)).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}"
        ) from e
    
    if len(result.data)>0:
        user = result.data[0]
        logger.info("User retrieved")
        return TSResponse(status=200, result=f"{user}")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with id {id}"
        ) 
        
@user_router.put("/update_user", response_model=TSResponse)
async def update_user(id: str, fields: UserFields,  db = Depends(get_db)) -> TSResponse:

    try:
        guid = UUID(id, version=4)
    except Exception as e:
        logger.exception("Invalid GUID")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input id {id} is not a valid guid: {e}"
        ) from e
    
    # query the database to ensure user exists
    try:
        result = db.table(USER_TABLE_NAME).select("*").eq("id", str(guid)).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}"
        ) from e
    
    if len(result.data)>0:
        user = result.data[0]
        
        # update db
        try:
            db.table(USER_TABLE_NAME).update(fields.model_dump(exclude_unset=True)).eq("id", str(guid)).execute()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {e}"
            ) from e
        
        # retrieve updated user
        result = db.table(USER_TABLE_NAME).select("*").eq("id", str(guid)).execute()
        user = result.data[0]

        return TSResponse(status=200, result=f"{user}")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with id {id}"
        )    

@user_router.delete("/delete_user", response_model=TSResponse)
async def delete_user(id : str, db = Depends(get_db)) -> TSResponse:

    try:
        guid = UUID(id, version=4)
    except Exception as e:
        logger.exception("Invalid GUID")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input id {id} is not a valid guid: {e}"
        ) from e 
    
    try:
        user_data : TSResponse = await get_user(id, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with id {id}: {e}"
        ) from e
    
    try:
        db.table(USER_TABLE_NAME).delete().eq("id",str(guid)).execute()
    except Exception as e:
        logger.exception("Unable to delete user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error {e}"
        ) from e
    
    logger.info("User deleted")
    return TSResponse(status=200, result=f"User {user_data.result} deleted")

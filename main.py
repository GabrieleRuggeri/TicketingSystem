'''
FastAPI application for a Ticketing System.

The app will expose endpoints to manage users, events, and bookings.

Available endpoints:
- /users: Create, read, update, delete users.
- /bookings: Create, read, update, delete bookings.
- /hotels: Create, read, update, delete hotel information.

Each endpoint will support standard HTTP methods (GET, POST, PUT, DELETE)
to perform CRUD operations on the respective resources.
'''

from contextlib import asynccontextmanager
from fastapi import FastAPI

from Database.db import TicketingDB

# routers
from api.user_routes import user_router
# from api.booking_routes import booking_router
# from api.hotel_routes import hotel_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    app.state.db = TicketingDB().client   # create ONCE
    yield 

# Initialize FastAPI app
app = FastAPI(title="Ticketing System API", version="1.0.0", lifespan=lifespan)

app.include_router(user_router, prefix="/users", tags=["Users"])
# app.include_router(booking_router, prefix="/bookings", tags=["Bookings"])
# app.include_router(hotel_router, prefix="/hotels", tags=["Hotels"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Ticketing System API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)


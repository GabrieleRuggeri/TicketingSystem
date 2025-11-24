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

from fastapi import FastAPI
from Users.user import User
from Hotels.booking import Booking
from Hotels.structure import Hotel

# Initialize FastAPI app
app = FastAPI(title="Ticketing System API", version="1.0.0")



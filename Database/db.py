'''
This file contains the database configuration for the Ticketing System.
'''
from pathlib import Path
import sys

from postgrest import APIResponse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Optional  # noqa: E402
from supabase import create_client, Client  # noqa: E402
import os  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from Users.user import User  # noqa: E402
from uuid import UUID  # noqa: E402

class TicketingDB:
    """Database Client"""

    # private interface
    def __init__(self, db_url: str, db_password: str, db_api_key: str):

        self.db_key: Optional[str] = db_password
        self.db_url: Optional[str] = db_url

        load_dotenv()
        self.get_db_endpoint()
        self.get_db_password()
        self.client: Client = create_client(self.db_url, db_api_key) # type: ignore

    def get_db_endpoint(self) -> Optional[str]:
        """Get the database endpoint URL."""
        self.db_url = os.getenv('DB_URL')
    
    def get_db_password(self) -> Optional[str]:
        """Get the database password."""
        self.db_key = os.getenv('DB_PASSWORD')
    
    # TODO public interface
    '''
    This is the list of operatioins that can be performed on the database.
    Each operation corresponds to a method that interacts with the database.
    
    Available operations:
    - /users: Create, read, update, delete users.
    - /bookings: Create, read, update, delete bookings.
    - /hotels: Create, read, update, delete hotel information.
    '''
    def create_user(self, user: User):
        """Create a new user in the database."""
        data = {
            "id": str(user.id),
            "name": user.name,
            "surname": user.surname,
            "email": user.email,
            "phone_number": user.phone_number
        }

        response: APIResponse = self.client.table("users").insert(data).execute()    
        return response
    
    def get_user(self, user_id: UUID) -> Optional[User]:
        """Retrieve a user from the database by ID."""
        response: APIResponse = self.client.table("users").select("*").eq("id", str(user_id)).execute()
        user_data = response.data[0] if response.data else None
        if user_data:
            return User(
                id=UUID(user_data["id"]), # type: ignore
                name=user_data["name"], # type: ignore
                surname=user_data["surname"], # type: ignore
                email=user_data["email"], # type: ignore
                phone_number=user_data["phone_number"] # type: ignore
            )
        return None



        

    
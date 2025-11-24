'''
This file contains the database configuration for the Ticketing System.
'''

from optparse import Option
from typing import Optional
from supabase import create_client, Client
import os
from dotenv import load_dotenv

class TicketingDatabaseConfig:
    """Configuration for connecting to the Ticketing System database."""

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


        

    
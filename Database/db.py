'''
This file contains the database configuration for the Ticketing System.
'''
# from pathlib import Path
# import sys 

# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))

from typing import Optional  # noqa: E402
from supabase import create_client, Client  # noqa: E402
import os  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

class TicketingDB:
    """Database Client"""

    # private interface
    def __init__(self):
        load_dotenv()
        url: Optional[str] = os.environ.get("SUPABASE_URL")
        key: Optional[str] = os.environ.get("SUPABASE_KEY")
        if url is None or key is None:
            raise ValueError("Database URL or Key not found in environment variables.")
        self.client: Client = create_client(url, key)

if __name__ == "__main__":
    db_conn = TicketingDB()

    _ = db_conn.client.table("users").select("*").execute()
    print(_)


        

    
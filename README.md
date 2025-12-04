# TicketingSystem

TicketingSystem provides composable Pydantic models and helpers to manage hotels, rooms, guests, and bookings, plus a FastAPI entry point that can later expose CRUD endpoints. The domain models enforce chronological consistency, normalize contact info, compute booking durations, and ensure that booking requests obey availability and status rules.

## Project Overview

- `Hotels.structure`: `Room` and `Hotel` models plus `Hotel.book`, which validates duplicates, room existence, overlapping reservations, and updates booking statuses.
- `Hotels.booking`: `BookingPeriod`, `Booking`, and `BookingRequestResponse` with validators for date ordering and timestamp integrity.
- `Users.user`: `User` model with email normalization and booking helper methods.
- `utils`: shared validators such as `are_overlapping` and timestamp checks.
- `main.py`: FastAPI stub that will host future REST endpoints.
- `Database/schema.md`: Mermaid ER diagram describing the persisted entities.
- `tests/test_models.py`: pytest suite covering the models and helper utilities.

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for dependency and virtualenv management
- Project dependencies (declared in `pyproject.toml`):
  - `pydantic` for data validation
  - `fastapi` for the future HTTP API
  - `supabase` for persistence integration (planned)
  - `python-dotenv` for configuration
  - Testing extra: `pytest`

## Setup

Install all application and test dependencies with uv (run from the repo root):

```bash
uv sync --extra testing
```

If your environment restricts write access to the default uv cache (e.g., when inside a sandboxed workspace), pin it to a folder inside the repo before syncing:

```bash
UV_CACHE_DIR=.uv-cache uv sync --extra testing
```

## Database Bootstrapping

The project ships with a simple bootstrap script and SQL migrations to create the initial schema in Supabase.

1. Make sure your `.env` file contains the connection details for the Supabase **session pooler**:

   ```env
   user=postgres.<your-project-ref>
   password=<your-real-db-password>
   host=aws-1-eu-central-1.pooler.supabase.com
   port=6543
   dbname=postgres
   ```

   These are the same parameters shown in the Supabase dashboard under **Connect → Connection pooling**.

2. From the repo root, run the bootstrap script:

   ```bash
   uv run bootstrap_script.py
   ```

   The script connects with `psycopg`, ensures a `schema_migrations` bookkeeping table exists, and then applies all `.sql` files in the `migrations/` directory in lexicographical order. The initial `migrations/01_init.sql` file creates the `users`, `hotels`, `rooms`, and `bookings` tables, mirroring the core entities in the ER diagram and Pydantic models.

## Usage Example

Create rooms, hotels, guests, and bookings directly from the provided models. The snippet below demonstrates a happy-path booking flow:

```python
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from Hotels.booking import Booking, BookingPeriod
from Hotels.structure import Hotel, Room
from Users.user import User

room = Room(number="101", size="double", price=120.0)
hotel = Hotel(
    name="Central Hotel",
    phone_number="555-0101",
    email="frontdesk@example.com",
    address="1 City Plaza",
    bookings=[],
    city="Milan",
    country="Italy",
    rooms=[room],
)

guest = User(name="Ada", surname="Byron", email="ada@example.com", phone_number=None)
period = BookingPeriod(
    start_date=datetime.now(timezone.utc),
    end_date=datetime.now(timezone.utc) + timedelta(days=3),
    duration=0,  # duration is recomputed automatically
)
booking = Booking(guest_id=guest.id, room_id=room.id, period=period, status="pending")

response = hotel.book(booking)
if response.status == "confirmed":
    guest.add_booking(booking)
```

The same objects can later be exposed through FastAPI routes (see `main.py`) or persisted via Supabase.

## Entity Relationship Diagram

The ER diagram is stored in `Database/schema.md` as a Mermaid block. Open that file in VS Code and use the Mermaid Chart extension’s preview to render the diagram. It illustrates the relationships among `HOTEL`, `ROOM`, `USER`, and `BOOKING` entities and mirrors the domain models in code.

## Test Suite

`tests/test_models.py` consolidates coverage for every Pydantic model shipped with
the project:

- `User`: ensures email normalization and rejects malformed addresses.
- `Room`: enforces positive pricing via its `model_validator`.
- `Hotel`: validates chronological consistency between `created_at` and `last_modified_at`.
- `Booking`: recomputes `duration`, supports status transitions, and guards both stay and audit timestamps.
- `BookingRequestResponse`: verifies that denial reasons remain optional.

Run the suite with uv:

```bash
uv run pytest tests/test_models.py
```

You can also execute the module directly (pytest discovers the embedded asserts):

```bash
uv run tests/test_models.py
```

Both commands ensure the current code passes all checks before you extend the system.

## Next Steps

- Refactor the main domain models (`User`, `Hotel`, `Room`, `BookingPeriod`, `Booking`, etc.) so that their fields and constraints align with the columns defined in `migrations/01_init.sql` and the ER diagram in `Database/schema.md`.
- Once the models and tables are aligned, introduce a persistence layer that reads/writes these models to the Supabase database instead of relying on in-memory collections.
- Extend `main.py` with real FastAPI routes that expose CRUD operations for users, hotels, rooms, and bookings on top of the database-backed models.

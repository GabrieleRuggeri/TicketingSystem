# TicketingSystem

FastAPI-based starter for a hotel booking system that uses Supabase for persistence. The current implementation exposes `/users` and `/hotels` CRUD APIs while keeping Pydantic domain models for rooms and bookings ready for future routes.

## Current Status

- FastAPI app (`main.py`) wires a Supabase client via the lifespan hook and mounts `api/user_routes.py` and `api/hotel_routes.py`; booking router remains a placeholder.
- Supabase connectivity is handled in `Database/db.py` and exposed to routes through the dependency in `Database/deps.py`.
- Domain validation lives in `Users/user.py`, `Hotels/structure.py`, `Hotels/booking.py`, and `utils.py` (timestamp and overlap helpers).
- SQL schema resides in `migrations/01_init.sql` with a bootstrap runner in `bootstrap_script.py`.
- Tests in `tests/` cover domain validators plus user and hotel APIs using in-memory Supabase doubles, so they run without network access.

## Project Layout

- `api/user_routes.py`: health check plus create/read/update/delete endpoints for `/users`; handles UUID parsing, duplicate email conflicts, and error reporting via `UserResponse`/`MessageResponse`.
- `api/hotel_routes.py`: health check plus create/read/update/delete endpoints for `/hotels`, last-modified tracking, and `GET /hotels/get_rooms/{hotel_id}` for associated rooms.
- `api/models.py`: shared request/response Pydantic schemas for the API layer.
- `Users/user.py`: user model with lowercase email validation and a `to_dict` serializer.
- `Hotels/structure.py`: `Hotel` and `Room` models with timestamp ordering and positive price checks.
- `Hotels/booking.py`: `Booking` with duration computation, status updates, and timestamp validation, plus `BookingRequestResponse`.
- `Database/db.py`, `Database/deps.py`: Supabase client creation and FastAPI dependency injection.
- `bootstrap_script.py`, `migrations/`: apply SQL migrations (users, hotels, rooms, bookings tables and the `schema_migrations` tracker).
- `tests/test_models.py`, `tests/test_user_routes.py`, `tests/test_hotel_routes.py`: pytest coverage for the models and the user and hotel router contracts.

## Requirements

- Python 3.12+
- Supabase project (URL + service key) for runtime API calls
- Dependencies from `pyproject.toml` (FastAPI, Pydantic, Supabase client, psycopg, pytest, etc.)
- [uv](https://github.com/astral-sh/uv) is recommended for dependency management (`uv.lock` is checked in), but `pip` works too.

## Installation

Install all dependencies, including testing tools:

```bash
uv sync --extra testing
# or
pip install -e .[testing]
```

If the environment blocks the default uv cache, scope it to the repo:

```bash
UV_CACHE_DIR=.uv-cache uv sync --extra testing
```

## Environment Configuration

Runtime expects Supabase credentials:

```env
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=<your-supabase-service-role-key>
```

`Database/db.py` loads these via `python-dotenv`, so you can place them in a `.env` file at the repo root.

The migration bootstrapper uses the Supabase session pooler (or any Postgres-compatible DSN) and expects in `.env`:

```env
user=postgres.<project-ref>
password=<database-password>
host=aws-1-<region>.pooler.supabase.com
port=6543
dbname=postgres
```

## Running the API

Apply migrations, ensure the required environment variables are set, then start the server:

```bash
uv run uvicorn main:app --reload
# or
uvicorn main:app --reload
```

The root endpoint returns a welcome message. Routes are available under `/users` and `/hotels`.

## Available User Endpoints

- `GET /users/health`: liveness check returning `{status, message}`.
- `POST /users`: create a user; trims and normalizes email, rejects duplicates by email.
- `GET /users/{user_id}`: fetch a user by UUID4; returns 404 when missing and 400 on invalid IDs.
- `PUT /users/{user_id}`: update mutable fields (`name`, `surname`, `phone_number`, `status`); requires at least one field.
- `DELETE /users/{user_id}`: delete a user record.

All routes rely on a Supabase table named `users` shaped like `migrations/01_init.sql`.

## Available Hotel Endpoints

- `GET /hotels/health`: liveness check returning `{status, message}`.
- `POST /hotels`: create a hotel; trims email, rejects duplicates by email.
- `GET /hotels/{hotel_id}`: fetch a hotel by UUID4; returns 404 when missing and 400 on invalid IDs.
- `PUT /hotels/{hotel_id}`: update mutable fields (`name`, `phone_number`, `email`, `address`, `city`, `country`); requires at least one field and refreshes `last_modified_at`.
- `DELETE /hotels/{hotel_id}`: delete a hotel record.
- `GET /hotels/get_rooms/{hotel_id}`: list rooms associated with a hotel; returns 404 when none are found.

Hotel routes rely on a Supabase table named `hotels` (and `rooms` for room listing) shaped like `migrations/01_init.sql`.

## Database Bootstrapping

Run migrations against your Supabase/Postgres instance:

```bash
uv run bootstrap_script.py
```

The script creates the `schema_migrations` table if absent, then executes each `.sql` file in `migrations/` in order, recording applied filenames.

## Testing

Execute the test suite (no external services required):

```bash
uv run pytest
```

`tests/test_models.py` validates the domain models, `tests/test_user_routes.py` exercises the user endpoints, and `tests/test_hotel_routes.py` exercises the hotel endpoints against in-memory Supabase doubles.

## Next Steps

- Implement booking router and register it in `main.py`.
- Align Pydantic models with the SQL schema (e.g., defaults, unique constraints, nullable fields) and add persistence helpers beyond the user and hotel tables.
- Harden error handling and add integration tests against a live Supabase instance once the additional routes exist.

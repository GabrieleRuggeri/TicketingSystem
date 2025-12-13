# TicketingSystem

FastAPI-based starter for a hotel booking system that uses Supabase for persistence. The current implementation focuses on the `/users` CRUD API while keeping Pydantic domain models for hotels, rooms, and bookings ready for future routes.

## Current Status

- FastAPI app (`main.py`) wires a Supabase client via the lifespan hook and mounts only `api/user_routes.py`; booking and hotel routers are placeholders.
- Supabase connectivity is handled in `Database/db.py` and exposed to routes through the dependency in `Database/deps.py`.
- Domain validation lives in `Users/user.py`, `Hotels/structure.py`, `Hotels/booking.py`, and `utils.py` (timestamp and overlap helpers).
- SQL schema resides in `migrations/01_init.sql` with a bootstrap runner in `bootstrap_script.py`.
- Tests in `tests/` cover domain validators and the user API using an in-memory Supabase double, so they run without network access.

## Project Layout

- `api/user_routes.py`: health check plus create/read/update/delete endpoints for `/users`; handles UUID parsing, duplicate email conflicts, and error reporting via `UserResponse`/`MessageResponse`.
- `api/models.py`: shared request/response Pydantic schemas for the API layer.
- `Users/user.py`: user model with lowercase email validation and a `to_dict` serializer.
- `Hotels/structure.py`: `Hotel` and `Room` models with timestamp ordering and positive price checks.
- `Hotels/booking.py`: `Booking` with duration computation, status updates, and timestamp validation, plus `BookingRequestResponse`.
- `Database/db.py`, `Database/deps.py`: Supabase client creation and FastAPI dependency injection.
- `bootstrap_script.py`, `migrations/`: apply SQL migrations (users, hotels, rooms, bookings tables and the `schema_migrations` tracker).
- `tests/test_models.py`, `tests/test_user_routes.py`: pytest coverage for the models and the user router contract.

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

The root endpoint returns a welcome message, and the user routes are available under `/users`.

## Available User Endpoints

- `GET /users/health`: liveness check returning `{status, message}`.
- `POST /users`: create a user; trims and normalizes email, rejects duplicates by email.
- `GET /users/{user_id}`: fetch a user by UUID4; returns 404 when missing and 400 on invalid IDs.
- `PUT /users/{user_id}`: update mutable fields (`name`, `surname`, `phone_number`, `status`); requires at least one field.
- `DELETE /users/{user_id}`: delete a user record.

All routes rely on a Supabase table named `users` shaped like `migrations/01_init.sql`.

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

`tests/test_models.py` validates the domain models, and `tests/test_user_routes.py` exercises the user endpoints against an in-memory Supabase double.

## Next Steps

- Implement booking and hotel routers and register them in `main.py`.
- Align Pydantic models with the SQL schema (e.g., defaults, unique constraints, nullable fields) and add persistence helpers beyond the user table.
- Harden error handling and add integration tests against a live Supabase instance once the additional routes exist.

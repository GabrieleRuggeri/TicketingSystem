# TicketingSystem

Utilities and models for handling hotel structures, rooms, bookings, and users. The project relies on Pydantic models (`Room`, `Hotel`, `BookingPeriod`, `Booking`, `User`) with custom validators to enforce chronological consistency, normalize/validate emails, compute booking durations, and a `Hotel.book` workflow to validate room existence, duplicates, availability, and booking status transitions.

## Setup

This repository uses [uv](https://github.com/astral-sh/uv) for environment management. Install dependencies once (including the testing extra for pytest):

```bash
uv sync --extra testing
```

## Test Suite

`tests/test_models.py` covers all models and helpers:

- `Room`: parametrized tests ensure every allowed `size` literal is accepted, and invalid literals raise a `ValidationError`.
- `BookingPeriod`: enforces strictly increasing dates and validates the computed `duration`.
- `Booking`: exercises valid/invalid statuses, timestamp ordering (including equality), status updates, and nested period validation.
- `Hotel`: validates contact fields, booking object types, timestamp ordering, duplicate booking detection, missing-room denials, overlap denials, and successful confirmations through `book`.
- `are_overlapping`: verifies overlapping and non-overlapping periods are detected correctly.
- `User`: normalizes emails to lowercase, enforces email validity, and covers add/remove booking helpers.

If your environment restricts access to the default uv cache location, set `UV_CACHE_DIR` inside the repo (e.g., `UV_CACHE_DIR=.uv-cache uv sync --extra testing`) before running tests.

The test module also ensures imports succeed when executed directly by inserting the project root on `sys.path`.

Run the suite from the repo root with uv:

```bash
uv run pytest tests/test_models.py
```

You can also execute the module directly:

```bash
uv run tests/test_models.py
```

Both commands ensure the newly added tests pass against the current codebase.

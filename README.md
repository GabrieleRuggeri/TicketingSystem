# TicketingSystem

Utilities and models for handling hotel structures, rooms, and bookings. The project relies on Pydantic models (`Room`, `Hotel`, `BookingPeriod`, `Booking`) with custom validators to enforce chronological consistency, an `are_overlapping` helper for date ranges, and `Hotel.book` workflow to validate room existence, duplicates, availability, and booking status transitions.

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

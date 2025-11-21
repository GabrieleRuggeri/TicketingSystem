# TicketingSystem

Utilities and models for handling hotel structures, rooms, and bookings. The project relies on Pydantic models (`Room`, `Hotel`, `BookingPeriod`, `Booking`) with custom validators to enforce chronological consistency.

## Setup

This repository uses [uv](https://github.com/astral-sh/uv) for environment management. Install dependencies once (including the testing extra for pytest):

```bash
uv sync --extra testing
```

## Test Suite

`tests/test_models.py` covers every `BaseModel` in the project:

- `Room`: parametrized tests ensure every allowed `size` literal is accepted, and invalid literals raise a `ValidationError`.
- `Hotel`: validates optional contact fields, enforces UUID booking IDs, and checks that the chronological validator accepts equal timestamps but rejects backward timelines.
- `BookingPeriod`: ensures date ranges are strictly increasing while preserving a positive-path example.
- `Booking`: exercises valid/invalid statuses, timestamp ordering (including equality), and propagation of nested `BookingPeriod` validation errors.

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

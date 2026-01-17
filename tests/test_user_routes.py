"""Endpoint tests for the user router using a fake Supabase client."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Database.deps import get_db  # noqa: E402
from Users.user import User  # noqa: E402
from api.user_routes import APIError, user_router  # noqa: E402


class FakeSupabaseResponse:
    """Minimal Supabase-like response wrapper."""

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


def _set_api_error_metadata(error: Exception, code: str, status_code: int) -> None:
    """
    Best-effort setter for API error metadata across implementations.

    Args:
        error: Error instance to enrich.
        code: Database error code (e.g., unique violation).
        status_code: HTTP status code to apply when available.
    """

    for attribute, value in {"code": code, "status_code": status_code}.items():
        try:
            setattr(error, attribute, value)
        except Exception:
            continue


class FakeTable:
    """In-memory table with a Supabase-like interface."""

    def __init__(self, backing_store: list[dict[str, Any]]) -> None:
        self._store = backing_store
        self._action: str | None = None
        self._filter: tuple[str, str] | None = None
        self._payload: dict[str, Any] | list[dict[str, Any]] | None = None

    def select(self, *_: str) -> "FakeTable":
        self._action = "select"
        return self

    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> "FakeTable":
        self._action = "insert"
        self._payload = payload
        return self

    def update(self, payload: dict[str, Any]) -> "FakeTable":
        self._action = "update"
        self._payload = payload
        return self

    def delete(self) -> "FakeTable":
        self._action = "delete"
        return self

    def eq(self, column: str, value: str) -> "FakeTable":
        self._filter = (column, value)
        return self

    def _filter_rows(self) -> list[dict[str, Any]]:
        if not self._filter:
            return list(self._store)
        column, value = self._filter
        return [row for row in self._store if str(row.get(column)) == str(value)]

    def execute(self) -> FakeSupabaseResponse:
        if self._action == "select":
            data = self._filter_rows()
        elif self._action == "insert":
            rows = self._payload if isinstance(self._payload, list) else [self._payload]  # type: ignore[arg-type]
            for row in rows:
                if any(str(existing.get("email")) == str(row.get("email")) for existing in self._store):
                    error = APIError("duplicate key value violates unique constraint")
                    _set_api_error_metadata(error, "23505", status.HTTP_409_CONFLICT)
                    raise error
            self._store.extend(rows)
            data = rows
        elif self._action == "update":
            data = self._filter_rows()
            for row in data:
                row.update(self._payload or {})
        elif self._action == "delete":
            data = self._filter_rows()
            for row in data:
                self._store.remove(row)
        else:
            raise ValueError("Unsupported action for FakeTable.")

        # reset state for the next call
        self._action = None
        self._filter = None
        self._payload = None
        return FakeSupabaseResponse(data)


class FakeDB:
    """Simplified Supabase client exposing the minimal table(...) API."""

    def __init__(self) -> None:
        self.users: list[dict[str, Any]] = []

    def table(self, name: str) -> FakeTable:
        if name != "users":
            raise ValueError(f"Unknown table {name}")
        return FakeTable(self.users)


@pytest.fixture()
def client() -> TestClient:
    """Create a TestClient with a fake database dependency override."""

    fake_db = FakeDB()
    app = FastAPI()
    app.dependency_overrides[get_db] = lambda: fake_db  # type: ignore[assignment]
    app.include_router(user_router, prefix="/users")
    return TestClient(app)


def _build_user_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Ada",
        "surname": "Lovelace",
        "email": "ada@example.com",
        "phone_number": "+1-555-000",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def test_create_user_returns_user_payload(client: TestClient) -> None:
    response = client.post("/users", json=_build_user_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == 201
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["name"] == "Ada"


def test_create_user_rejects_duplicate_email(client: TestClient) -> None:
    payload = _build_user_payload()
    first = client.post("/users", json=payload)
    assert first.status_code == 201

    duplicate = client.post("/users", json=payload)

    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


def test_get_user_by_id(client: TestClient) -> None:
    creation = client.post("/users", json=_build_user_payload(email="bob@example.com", name="Bob"))
    user_id = creation.json()["user"]["id"]

    fetched = client.get(f"/users/{user_id}")

    assert fetched.status_code == 200
    assert fetched.json()["user"]["id"] == user_id
    assert fetched.json()["user"]["name"] == "Bob"


def test_update_user_requires_at_least_one_field(client: TestClient) -> None:
    creation = client.post("/users", json=_build_user_payload(email="carol@example.com"))
    user_id = creation.json()["user"]["id"]

    update = client.put(f"/users/{user_id}", json={})

    assert update.status_code == 400
    assert "At least one field" in update.json()["detail"]


def test_update_user_applies_changes(client: TestClient) -> None:
    creation = client.post("/users", json=_build_user_payload(email="dave@example.com", status="inactive"))
    user_id = creation.json()["user"]["id"]

    update = client.put(f"/users/{user_id}", json={"status": "active", "phone_number": "+1-555-123"})
    body = update.json()

    assert update.status_code == 200
    assert body["user"]["status"] == "active"
    assert body["user"]["phone_number"] == "+1-555-123"


def test_update_user_ignores_none_fields(client: TestClient) -> None:
    creation = client.post("/users", json=_build_user_payload(email="fred@example.com", surname="Original"))
    user_id = creation.json()["user"]["id"]
    original_surname = creation.json()["user"]["surname"]

    update = client.put(
        f"/users/{user_id}", json={"phone_number": "+1-555-789", "surname": None}
    )
    body = update.json()

    assert update.status_code == 200
    assert body["user"]["phone_number"] == "+1-555-789"
    assert body["user"]["surname"] == original_surname


def test_delete_user_returns_confirmation_message(client: TestClient) -> None:
    creation = client.post("/users", json=_build_user_payload(email="eve@example.com"))
    user_id = creation.json()["user"]["id"]

    deletion = client.delete(f"/users/{user_id}")

    assert deletion.status_code == 200
    assert f"User {user_id} deleted" in deletion.json()["message"]


def test_get_user_rejects_invalid_uuid(client: TestClient) -> None:
    response = client.get("/users/not-a-uuid")

    assert response.status_code == 400
    assert "valid UUID4" in response.json()["detail"]


def test_create_user_handles_unique_violation_from_database() -> None:
    """Simulate a race where the DB unique constraint rejects the insert."""

    class RaceyTable(FakeTable):
        def execute(self) -> FakeSupabaseResponse:
            if self._action == "select":
                return FakeSupabaseResponse([])
            return super().execute()

    class RaceyDB(FakeDB):
        def table(self, name: str) -> FakeTable:
            if name != "users":
                raise ValueError(f"Unknown table {name}")
            return RaceyTable(self.users)

    app = FastAPI()
    racey_db = RaceyDB()
    racey_db.users.append(User(**_build_user_payload()).to_dict())
    app.dependency_overrides[get_db] = lambda: racey_db  # type: ignore[assignment]
    app.include_router(user_router, prefix="/users")
    test_client = TestClient(app)

    response = test_client.post("/users", json=_build_user_payload())

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

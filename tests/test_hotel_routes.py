"""Endpoint tests for the hotel router using a fake Supabase client."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Database.deps import get_db  # noqa: E402
from Hotels.structure import Hotel, Room  # noqa: E402
from api.hotel_routes import APIError, hotel_router  # noqa: E402


class FakeSupabaseResponse:
    """Minimal Supabase-like response wrapper."""

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class FakeTable:
    """In-memory table with a Supabase-like interface."""

    def __init__(self, backing_store: list[dict[str, Any]], table_name: str) -> None:
        self._store = backing_store
        self._table_name = table_name
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
            if self._table_name == "hotels":
                for row in rows:
                    if any(str(existing.get("email")) == str(row.get("email")) for existing in self._store):
                        error = APIError("duplicate key value violates unique constraint")
                        error.code = "23505"  # type: ignore[attr-defined]
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

        self._action = None
        self._filter = None
        self._payload = None
        return FakeSupabaseResponse(data)


class FakeDB:
    """Simplified Supabase client exposing the minimal table(...) API."""

    def __init__(self) -> None:
        self.hotels: list[dict[str, Any]] = []
        self.rooms: list[dict[str, Any]] = []

    def table(self, name: str) -> FakeTable:
        if name == "hotels":
            return FakeTable(self.hotels, "hotels")
        if name == "rooms":
            return FakeTable(self.rooms, "rooms")
        raise ValueError(f"Unknown table {name}")


@pytest.fixture()
def client_and_db() -> tuple[TestClient, FakeDB]:
    """Create a TestClient with a fake database dependency override."""

    fake_db = FakeDB()
    app = FastAPI()
    app.dependency_overrides[get_db] = lambda: fake_db  # type: ignore[assignment]
    app.include_router(hotel_router, prefix="/hotels")
    return TestClient(app), fake_db


def _build_hotel_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "Grand Hotel",
        "phone_number": "+1-555-000",
        "email": "info@grand.example",
        "address": "1 Main St",
        "city": "Metropolis",
        "country": "Wonderland",
    }
    payload.update(overrides)
    return payload


def _build_room_payload(hotel_id: str, **overrides: Any) -> dict[str, Any]:
    payload = {
        "hotel_id": hotel_id,
        "number": "101",
        "size": "double",
        "price": 120,
    }
    payload.update(overrides)
    return Room(**payload).to_dict()


def test_create_hotel_returns_hotel_payload(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, _ = client_and_db

    response = client.post("/hotels", json=_build_hotel_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == 201
    assert body["hotel"]["email"] == "info@grand.example"
    assert body["hotel"]["name"] == "Grand Hotel"


def test_create_hotel_rejects_duplicate_email(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, _ = client_and_db
    payload = _build_hotel_payload()
    first = client.post("/hotels", json=payload)
    assert first.status_code == 201

    duplicate = client.post("/hotels", json=payload)

    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


def test_get_hotel_by_id(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, _ = client_and_db
    creation = client.post("/hotels", json=_build_hotel_payload(email="bob@hotel.example", name="Bob's Hotel"))
    hotel_id = creation.json()["hotel"]["id"]

    fetched = client.get(f"/hotels/{hotel_id}")

    assert fetched.status_code == 200
    assert fetched.json()["hotel"]["id"] == hotel_id
    assert fetched.json()["hotel"]["name"] == "Bob's Hotel"


def test_update_hotel_requires_at_least_one_field(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, _ = client_and_db
    creation = client.post("/hotels", json=_build_hotel_payload(email="carol@hotel.example"))
    hotel_id = creation.json()["hotel"]["id"]

    update = client.put(f"/hotels/{hotel_id}", json={})

    assert update.status_code == 400
    assert "At least one field" in update.json()["detail"]


def test_update_hotel_applies_changes_and_updates_timestamp(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, _ = client_and_db
    creation = client.post("/hotels", json=_build_hotel_payload(email="dave@hotel.example", city="Old City"))
    hotel_id = creation.json()["hotel"]["id"]
    original_last_modified = creation.json()["hotel"]["last_modified_at"]

    update = client.put(
        f"/hotels/{hotel_id}",
        json={"city": "New City", "phone_number": "+1-555-123"},
    )
    body = update.json()

    assert update.status_code == 200
    assert body["hotel"]["city"] == "New City"
    assert body["hotel"]["phone_number"] == "+1-555-123"
    assert body["hotel"]["last_modified_at"] != original_last_modified


def test_delete_hotel_returns_confirmation_message(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, _ = client_and_db
    creation = client.post("/hotels", json=_build_hotel_payload(email="eve@hotel.example"))
    hotel_id = creation.json()["hotel"]["id"]

    deletion = client.delete(f"/hotels/{hotel_id}")

    assert deletion.status_code == 200
    assert f"Hotel {hotel_id} deleted" in deletion.json()["message"]


def test_get_hotel_rejects_invalid_uuid(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, _ = client_and_db

    response = client.get("/hotels/not-a-uuid")

    assert response.status_code == 400
    assert "valid UUID4" in response.json()["detail"]


def test_create_hotel_handles_unique_violation_from_database() -> None:
    """Simulate a race where the DB unique constraint rejects the insert."""

    class RaceyTable(FakeTable):
        def execute(self) -> FakeSupabaseResponse:
            if self._action == "select":
                return FakeSupabaseResponse([])
            return super().execute()

    class RaceyDB(FakeDB):
        def table(self, name: str) -> FakeTable:
            if name == "hotels":
                return RaceyTable(self.hotels, "hotels")
            if name == "rooms":
                return FakeTable(self.rooms, "rooms")
            raise ValueError(f"Unknown table {name}")

    app = FastAPI()
    racey_db = RaceyDB()
    racey_db.hotels.append(Hotel(**_build_hotel_payload()).to_dict())
    app.dependency_overrides[get_db] = lambda: racey_db  # type: ignore[assignment]
    app.include_router(hotel_router, prefix="/hotels")
    test_client = TestClient(app)

    response = test_client.post("/hotels", json=_build_hotel_payload())

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_get_rooms_returns_rooms_for_hotel(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, fake_db = client_and_db
    creation = client.post("/hotels", json=_build_hotel_payload(email="rooms@hotel.example"))
    hotel_id = creation.json()["hotel"]["id"]
    fake_db.rooms.append(_build_room_payload(hotel_id, number="201"))
    fake_db.rooms.append(_build_room_payload(hotel_id, number="202", size="triple", price=200))

    response = client.get(f"/hotels/get_rooms/{hotel_id}")

    assert response.status_code == 200
    body = response.json()
    room_numbers = [room["number"] for room in body["rooms"]]
    assert set(room_numbers) == {"201", "202"}
    assert all(room["hotel_id"] == hotel_id for room in body["rooms"])


def test_get_rooms_returns_404_when_no_rooms(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, _ = client_and_db
    creation = client.post("/hotels", json=_build_hotel_payload(email="norooms@hotel.example"))
    hotel_id = creation.json()["hotel"]["id"]

    response = client.get(f"/hotels/get_rooms/{hotel_id}")

    assert response.status_code == 404
    assert "No rooms found" in response.json()["detail"]


def test_get_rooms_rejects_invalid_uuid(client_and_db: tuple[TestClient, FakeDB]) -> None:
    client, _ = client_and_db

    response = client.get("/hotels/get_rooms/not-a-uuid")

    assert response.status_code == 400
    assert "valid UUID4" in response.json()["detail"]

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence
from urllib.parse import quote_plus

from dotenv import load_dotenv
import psycopg
from psycopg import Connection


LOGGER = logging.getLogger(__name__)
MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def load_configuration() -> str:
    """Build a Postgres DSN from environment variables.

    The .env file is expected to define:
    - user
    - password
    - host
    - port
    - dbname

    Returns:
        A Postgres connection URL (DSN) string.

    Raises:
        RuntimeError: If any required variable is missing.
    """

    load_dotenv()
    user = os.getenv("user")
    password = os.getenv("password")
    host = os.getenv("host")
    port = os.getenv("port")
    dbname = os.getenv("dbname")

    if not all([user, password, host, port, dbname]):
        raise RuntimeError(
            "Environment variables 'user', 'password', 'host', 'port', and 'dbname' must all be set."
        )

    # Build a DSN compatible with psycopg.
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{dbname}"
    )


def build_conninfo(db_url: str) -> str:
    """Normalize a Postgres connection string for psycopg.

    Args:
        db_url: Postgres DSN string.

    Returns:
        A Postgres connection string compatible with ``psycopg``.
    """

    if db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql://", 1)
    return db_url


def ensure_schema_migrations_table(connection: Connection[Any]) -> None:
    """Create the ``schema_migrations`` table when it is missing."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )


def fetch_applied_migrations(connection: Connection[Any]) -> set[str]:
    """Fetch the set of already applied migration identifiers."""

    rows = connection.execute("SELECT migration_id FROM schema_migrations;")
    return {row[0] for row in rows}


def discover_migrations(directory: Path) -> Sequence[Path]:
    """Return migration files sorted by filename."""

    return sorted(directory.glob("*.sql"), key=lambda path: path.name)


def run_migration(connection: Connection[Any], migration_path: Path) -> None:
    """Execute a single migration within its own transaction."""

    sql = migration_path.read_text(encoding="utf-8").strip()
    if not sql:
        LOGGER.info("Skipping empty migration %s", migration_path.name)
        return

    with connection.transaction():
        connection.execute(sql) # type: ignore
        connection.execute(
            """
            INSERT INTO schema_migrations (migration_id, applied_at)
            VALUES (%s, NOW())
            ON CONFLICT (migration_id) DO NOTHING;
            """,
            (migration_path.name,),
        )


def apply_pending_migrations(connection: Connection[Any], migrations: Iterable[Path]) -> list[str]:
    """Apply the migrations that have not run yet.

    Args:
        connection: Active Postgres connection.
        migrations: Iterable of migration file paths.

    Returns:
        List of migration filenames that were newly applied.
    """

    ensure_schema_migrations_table(connection)
    applied = fetch_applied_migrations(connection)
    newly_applied: list[str] = []
    for migration in migrations:
        if migration.name in applied:
            LOGGER.info("Migration %s already applied; skipping.", migration.name)
            continue
        LOGGER.info("Applying migration %s", migration.name)
        try:
            run_migration(connection, migration)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("Failed to apply migration %s", migration.name)
            raise RuntimeError(f"Migration {migration.name} failed") from exc
        newly_applied.append(migration.name)
    return newly_applied


def main() -> None:
    """Entry point that orchestrates configuration loading and migrations."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    db_url = load_configuration()
    conninfo = build_conninfo(db_url)
    if not conninfo:
        raise RuntimeError("Failed to build Postgres connection string.")
    migrations = discover_migrations(MIGRATIONS_DIR)
    if not migrations:
        LOGGER.info("No migrations found under %s", MIGRATIONS_DIR)
        return

    LOGGER.info("Connecting to Supabase database.")
    with psycopg.connect(conninfo) as connection:
        applied = apply_pending_migrations(connection, migrations)
        if applied:
            LOGGER.info("Applied migrations: %s", ", ".join(applied))
        else:
            LOGGER.info("Database schema already up to date.")


if __name__ == "__main__":
    main()

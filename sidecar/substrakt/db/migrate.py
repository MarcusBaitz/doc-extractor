"""Apply numbered schema migrations through ``PRAGMA user_version``.

The small schema does not justify shipping an ORM. Each ``NNN_*.sql`` file is
applied once, in numerical order and in a transaction.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

MIGRATIONS = Path(__file__).parent / "migrations"
_FILE_NAME = re.compile(r"^(\d{3})_.+\.sql$")


def _steps() -> list[tuple[int, Path]]:
    """Return migrations in numerical order and reject gaps."""
    found: list[tuple[int, Path]] = []
    for file in sorted(MIGRATIONS.glob("*.sql")):
        match = _FILE_NAME.match(file.name)
        if not match:
            raise ValueError(
                f"Migration {file.name} does not match NNN_name.sql"
            )
        found.append((int(match.group(1)), file))

    numbers = [n for n, _ in found]
    if len(set(numbers)) != len(numbers):
        raise ValueError(f"Duplicate migration numbers: {numbers}")
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        raise ValueError(f"Gap in migration numbers: {numbers}")

    return found


def current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending migrations idempotently and return the resulting version."""
    version = current_version(conn)
    steps = _steps()

    if version > len(steps):
        raise RuntimeError(
            f"Database version {version} is newer than the {len(steps)} "
            "migrations known to this application version."
        )

    for number, file in steps:
        if number <= version:
            continue

        log.info("Applying migration %03d: %s", number, file.name)
        sql = file.read_text(encoding="utf-8")
        try:
            with conn:
                conn.executescript(sql)
                # executescript closes transactions, so set user_version separately.
                conn.execute(f"PRAGMA user_version = {number}")
        except sqlite3.Error as exc:
            raise RuntimeError(f"Migration {file.name} failed: {exc}") from exc

        version = number

    return version


def open_database(path: Path) -> sqlite3.Connection:
    """Open a database, configure pragmas and apply migrations."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # WAL permits reads while background work writes.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    # SQLite foreign keys are disabled per connection unless enabled explicitly.
    conn.execute("PRAGMA foreign_keys = ON")

    migrate(conn)
    return conn

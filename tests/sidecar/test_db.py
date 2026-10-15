"""Tests for db."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from substrakt.db import current_version, migrate, open_database
from substrakt.db.migrate import _steps

TABLES = {
    "document_type",
    "field",
    "field_block",
    "fingerprint",
    "extraction_run",
    "correction",
    "export_profile",
    "audit_log",
    "app_setting",
}


def test_migrations_are_gapless() -> None:
    steps = _steps()
    assert steps, "At least one migration is required"
    assert [n for n, _ in steps] == list(range(1, len(steps) + 1))


def test_all_tables_created(tmp_path: Path) -> None:
    conn = open_database(tmp_path / "test.db")
    try:
        existing = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert existing >= TABLES, f"Fehlend: {TABLES - existing}"
    finally:
        conn.close()


def test_migration_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "test.db"
    conn = open_database(path)
    try:
        version = current_version(conn)
        assert version == len(_steps())

        assert migrate(conn) == version
        assert migrate(conn) == version
    finally:
        conn.close()

    
    conn = open_database(path)
    try:
        assert current_version(conn) == version
    finally:
        conn.close()


def test_foreign_keys_work(tmp_path: Path) -> None:
    conn = open_database(tmp_path / "test.db")
    try:
        conn.execute(
            "INSERT INTO document_type (id, name, created_at, updated_at) "
            "VALUES (1, 'Eingangsrechnung', '2026-07-27T10:00:00+02:00', "
            "'2026-07-27T10:00:00+02:00')"
        )
        conn.execute(
            "INSERT INTO field (document_type_id, name, question) "
            "VALUES (1, 'invoice_number', 'Wie lautet die Rechnungsnummer?')"
        )
        conn.commit()

        assert conn.execute("SELECT count(*) FROM field").fetchone()[0] == 1

        conn.execute("DELETE FROM document_type WHERE id = 1")
        conn.commit()

        assert conn.execute("SELECT count(*) FROM field").fetchone()[0] == 0, (
            "The field should have cascaded — is PRAGMA foreign_keys missing?"
        )
    finally:
        conn.close()


def test_checks(tmp_path: Path) -> None:
    conn = open_database(tmp_path / "test.db")
    try:
        conn.execute(
            "INSERT INTO document_type (id, name, created_at, updated_at) "
            "VALUES (1, 'Typ', '2026-07-27T10:00:00+02:00', '2026-07-27T10:00:00+02:00')"
        )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO field (document_type_id, name, extractor) "
                "VALUES (1, 'a', 'zauberei')"
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO audit_log (occurred_at, action, target, result, mode) "
                "VALUES ('2026-07-27T10:00:00+02:00', 'export', 'x', 'vielleicht', 'airgap')"
            )
    finally:
        conn.close()


def test_duplicate_field_name_abgelehnt(tmp_path: Path) -> None:
    conn = open_database(tmp_path / "test.db")
    try:
        conn.execute(
            "INSERT INTO document_type (id, name, created_at, updated_at) "
            "VALUES (1, 'Typ', '2026-07-27T10:00:00+02:00', '2026-07-27T10:00:00+02:00')"
        )
        conn.execute("INSERT INTO field (document_type_id, name) VALUES (1, 'amount')")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO field (document_type_id, name) VALUES (1, 'amount')")
    finally:
        conn.close()

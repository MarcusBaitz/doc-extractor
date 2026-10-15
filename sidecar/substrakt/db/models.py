"""Store and load named document types with their field definitions.

Nested locator details remain in ``locator_json`` so extending a locator does
not require a schema migration.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from substrakt.extraction.fields import FieldSpec
from substrakt.extraction.labels import LabelRule

OutputFormat = Literal["table", "file"]


class DocumentType(BaseModel):
    """A named set of field definitions."""

    id: int | None = None
    name: str
    description: str = ""
    fields: list[FieldSpec] = Field(default_factory=list)
    updated_at: str = ""
    # Each document becomes either a table row or a separate file.
    output: OutputFormat = "table"
    # The overview needs only the count, avoiding an n+1 query for full fields.
    value_count: int = 0


def _now() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def list_all(conn: sqlite3.Connection) -> list[DocumentType]:
    """List all types without loading their fields."""
    return [
        DocumentType(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            updated_at=row["updated_at"],
            output=row["output"],
            value_count=row["value_count"],
        )
        for row in conn.execute(
            "SELECT t.id, t.name, t.description, t.updated_at, t.output, "
            "       (SELECT COUNT(*) FROM field f WHERE f.document_type_id = t.id) "
            "         AS value_count "
            "FROM document_type t ORDER BY t.updated_at DESC"
        )
    ]


def load(conn: sqlite3.Connection, type_id: int) -> DocumentType | None:
    """Load one type with all of its fields."""
    header = conn.execute(
        "SELECT id, name, description, updated_at, output "
        "FROM document_type WHERE id = ?",
        (type_id,),
    ).fetchone()
    if header is None:
        return None

    fields = []
    for row in conn.execute(
        "SELECT name, question, json_type, required, locator_json, extractor, regex, "
        "normalization FROM field WHERE document_type_id = ? ORDER BY sort_order",
        (type_id,),
    ):
        stored = json.loads(row["locator_json"] or "{}")
        fields.append(
            FieldSpec(
                name=row["name"],
                # The display label is metadata, not a search column.
                label=stored.get("label", ""),
                question=row["question"],
                json_type=row["json_type"],
                required=bool(row["required"]),
                # The column stores the method; JSON stores the extractor name.
                method=row["extractor"],
                extractor=stored.get("extractor"),
                regex=row["regex"],
                normalization=row["normalization"],
                regions=stored.get("regions", []),
                # A kind-specific label rule is nested metadata too.
                label_rule=(
                    LabelRule.model_validate(stored["label_rule"])
                    if stored.get("label_rule")
                    else None
                ),
            )
        )

    return DocumentType(
        id=header["id"],
        name=header["name"],
        description=header["description"],
        fields=fields,
        updated_at=header["updated_at"],
        output=header["output"],
        value_count=len(fields),
    )


def save(conn: sqlite3.Connection, type_: DocumentType) -> DocumentType:
    """Create or replace a type, replacing rather than merging its fields."""
    now = _now()

    with conn:
        existing = conn.execute(
            "SELECT id FROM document_type WHERE name = ?", (type_.name,)
        ).fetchone()

        if existing:
            type_id = existing["id"]
            conn.execute(
                "UPDATE document_type SET description = ?, output = ?, "
                "updated_at = ?, version = version + 1 WHERE id = ?",
                (type_.description, type_.output, now, type_id),
            )
            conn.execute("DELETE FROM field WHERE document_type_id = ?", (type_id,))
        else:
            cursor = conn.execute(
                "INSERT INTO document_type (name, description, output, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (type_.name, type_.description, type_.output, now, now),
            )
            type_id = cursor.lastrowid

        for index, field in enumerate(type_.fields):
            conn.execute(
                "INSERT INTO field (document_type_id, name, question, json_type, required, "
                "locator_json, extractor, regex, normalization, sort_order) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    type_id,
                    field.name,
                    field.question,
                    field.json_type,
                    int(field.required),
                    json.dumps(
                        {
                            "label": field.label,
                            "method": field.method,
                            "extractor": field.extractor,
                            "regions": [r.model_dump() for r in field.regions],
                            "label_rule": (
                                field.label_rule.model_dump() if field.label_rule else None
                            ),
                        },
                        ensure_ascii=False,
                    ),
                    field.method,
                    field.regex,
                    field.normalization,
                    index,
                ),
            )

    loaded = load(conn, type_id)
    assert loaded is not None
    return loaded


def delete(conn: sqlite3.Connection, type_id: int) -> bool:
    """Delete a type; its fields follow through ``ON DELETE CASCADE``."""
    with conn:
        cursor = conn.execute("DELETE FROM document_type WHERE id = ?", (type_id,))
    return cursor.rowcount > 0

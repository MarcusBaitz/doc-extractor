"""Document kinds come from YAML files consumed by the generic core."""

from __future__ import annotations

import importlib.machinery
import json
import sqlite3
import sys
import types
from pathlib import Path

import pytest

from substrakt import document_kinds
from substrakt.db import models, open_database
from substrakt.document_kinds import DocumentKind
from substrakt.errors import DocumentKindInvalid, DocumentKindUnknown
from substrakt.extraction.fields import SAMPLE_FIELDS, FieldSpec, extract, extract_field
from substrakt.extraction.labels import Assignment, LabelRule
from substrakt.model import Document, DocumentMeta, ImageRect, Page, Word

DELIVERY_NOTE = """\
name: delivery_note
title: Lieferschein
boundaries: ['Kundennummer']
fields:
  - name: delivery_note_number
    label: Lieferscheinnummer
    label_rule:
      patterns: ['Lieferschein-?Nr\\.?', 'Delivery\\s+note\\s+no\\.?']
      value: identifier
"""


def document(rows: list[tuple[int, list[tuple[int, str]]]]) -> Document:
    words = []
    for y, entries in rows:
        for x, text in entries:
            for token in text.split():
                width = len(token) * 6
                words.append(Word(text=token, page=0, confidence=0.99,
                    locator=ImageRect(page=0, x0=x, x1=x+width, y0=y, y1=y+10)))
                x += width + 4
    return Document(id="test", filename="test.png", sha256="test", kind="image",
        pages=[Page(number=0, width=600, height=800)], words=words,
        meta=DocumentMeta(size_bytes=1, page_count=1, word_count=len(words), text_source="ocr"))


def write_kind(directory: Path, name: str, content: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.yml"
    path.write_text(content, encoding="utf-8")
    return path


def error_from(directory: Path, name: str) -> DocumentKindInvalid:
    with pytest.raises(DocumentKindInvalid) as info:
        document_kinds.load(name, builtin=directory)
    return info.value


# --- Loading -----------------------------------------------------------------


def test_bundled_invoice_contains_the_existing_invoice_knowledge() -> None:
    invoice = document_kinds.default()
    assert invoice.name == "invoice"
    assert [f.name for f in invoice.fields] == [
        "sender", "document_number", "document_date", "total_amount", "net_amount",
        "tax_amount", "document_kind", "currency", "vat_id", "iban",
    ]
    assert invoice.context().title["invoice"] == "Rechnung"
    assert invoice.context().title["credit note"] == "Gutschrift"
    assert [f.name for f in SAMPLE_FIELDS] == [f.name for f in invoice.fields]


def test_all_bundled_files_are_valid() -> None:
    all_matches = document_kinds.load_all(custom=Path("/does/not/exist"))
    assert "invoice" in all_matches


def test_schema_file_matches_the_model() -> None:
    assert document_kinds.schema_is_current(), (
        "document_kind.schema.json is stale: "
        'uv run python -c "from substrakt import document_kinds; document_kinds.write_schema()"'
    )
    schema = json.loads(document_kinds.schema_text())
    assert schema["additionalProperties"] is False
    assert {"name", "title", "fields"} <= set(schema["required"])


def test_stale_schema_file_is_detected(tmp_path: Path) -> None:
    file = tmp_path / "document_kind.schema.json"
    document_kinds.write_schema(file)
    assert document_kinds.schema_is_current(file)
    file.write_text(
        file.read_text(encoding="utf-8").replace('"title"', '"stale_title"', 1),
        encoding="utf-8",
    )
    assert not document_kinds.schema_is_current(file)
    assert not document_kinds.schema_is_current(tmp_path / "missing.json")


def test_core_is_generic_for_another_document_kind(tmp_path: Path) -> None:
    write_kind(tmp_path, "delivery_note", DELIVERY_NOTE)
    kind = document_kinds.load("delivery_note", builtin=tmp_path)
    doc = document([(20, [(20, "Lieferschein-Nr.:"), (300, "Kundennummer:")]),
                    (38, [(20, "LS-20817"), (300, "K-4711")])])
    run = extract(doc, kind.fields, kind=kind)
    assert run.results[0].value == "LS-20817"
    
    invoice = document([(20, [(20, "Rechnungsnummer: RE-1")])])
    assert extract(invoice, kind.fields, kind=kind).results[0].value is None


def test_older_document_fields_without_rule_use_document_kind_default() -> None:
    alt = FieldSpec(name="document_number", label="Belegnummer", extractor="document_field")
    doc = document([(20, [(20, "Belegnummer: ZX-4839")])])
    assert extract_field(doc, alt).value == "ZX-4839"


# --- Schema errors -------------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "location", "message"),
    [
        ("name: broken\ntitle: K\nfields: []\n", "fields", "at least 1"),
        ("name: broken\ntitle: K\nmodel: granite\nfields: [{name: a}]\n", "model", "Extra inputs"),
        ("name: broken\ntitle: K\nfields: [{name: a, labell: A}]\n", "", "fields.0: unknown keys labell"),
        ("name: broken\ntitle: K\nfields: [{name: a, json_type: unsupported}]\n", "fields.0.json_type", "Input should be"),
        ("name: broken\ntitle: K\nfields: [{name: a, normalization: euro}]\n", "", "unknown normalization"),
        ("name: broken\ntitle: K\nfields: [{name: a}, {name: a}]\n", "", "Duplicate field names: a"),
        ("name: broken\ntitle: K\nfields: [{name: a, label_rule: {patterns: ['(open'], value: identifier}}]\n",
         "fields.0.label_rule", "not a valid regular expression"),
        ("name: broken\ntitle: K\nfields: [{name: a, label_rule: {patterns: [W], value: code}}]\n",
         "fields.0.label_rule", "requires a values list"),
        ("name: broken\ntitle: K\nfields: [{name: a, label_rule: {value: title}}]\n", "", "requires recognition.titles"),
    ],
)
def test_schema_errors_name_file_and_location(tmp_path: Path, content: str, location: str, message: str) -> None:
    write_kind(tmp_path, "broken", content)
    error = error_from(tmp_path, "broken")
    assert error.fields["file"] == "broken.yml"
    assert any(f["location"].startswith(location) and message in f["message"] for f in error.fields["error"]), error.detail
    problem = error.as_problem()
    assert problem["type"].endswith("/document-kind-invalid")
    assert problem["detail"].startswith("broken.yml: ")


def test_broken_yaml_is_reported(tmp_path: Path) -> None:
    write_kind(tmp_path, "broken", "name: broken\nfields: [\n")
    assert "unreadable YAML" in error_from(tmp_path, "broken").detail


def test_name_must_match_file_name(tmp_path: Path) -> None:
    write_kind(tmp_path, "broken", "name: different\ntitle: K\nfields: [{name: a}]\n")
    assert error_from(tmp_path, "broken").fields["error"][0]["location"] == "name"


def test_unknown_document_kind(tmp_path: Path) -> None:
    with pytest.raises(DocumentKindUnknown):
        document_kinds.load("does_not_exist", builtin=tmp_path)


def test_yaml_is_safely_loaded(tmp_path: Path) -> None:
    write_kind(tmp_path, "broken", "name: !!python/object/apply:os.system ['true']\n")
    assert "unreadable YAML" in error_from(tmp_path, "broken").detail





def test_custom_file_replaces_bundled_file(tmp_path: Path) -> None:
    custom = tmp_path / "custom"
    write_kind(custom, "invoice", "name: invoice\ntitle: Hausrechnung\nfields:\n"
             "  - name: document_number\n    label_rule: {patterns: ['Vorgang'], value: identifier}\n")
    write_kind(custom, "delivery_note", DELIVERY_NOTE)

    all_matches = document_kinds.load_all(custom=custom)
    assert all_matches["invoice"].title == "Hausrechnung"
    assert [f.name for f in all_matches["invoice"].fields] == ["document_number"]
    assert set(all_matches) >= {"invoice", "delivery_note"}

    invoice = document_kinds.load("invoice", custom=custom)
    doc = document([(20, [(20, "Vorgang: VG-77")]), (40, [(20, "Belegnummer: ZX-1")])])
    assert extract(doc, invoice.fields, kind=invoice).results[0].value == "VG-77"


def test_changed_file_is_again_read(tmp_path: Path) -> None:
    path = write_kind(tmp_path, "delivery_note", DELIVERY_NOTE)
    assert document_kinds.load("delivery_note", builtin=tmp_path).title == "Lieferschein"
    path.write_text(DELIVERY_NOTE.replace("title: Lieferschein", "title: Warenbegleitschein"),
                    encoding="utf-8")
    assert document_kinds.load("delivery_note", builtin=tmp_path).title == "Warenbegleitschein"


# --- Custom parser -----------------------------------------------------------


@pytest.fixture
def testparser(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def read(doc: Document, field: FieldSpec, kind: DocumentKind) -> Assignment | None:
        calls.append(field.name)
        if field.name != "special_number":
            return None
        word = next(w for w in doc.words if w.text.startswith("SN-"))
        from substrakt.extraction import labels

        return Assignment(word.text, labels._evidence([word]), "")

    module = types.ModuleType(f"{document_kinds.PARSER_PACKAGE}.testparser")
    module.__spec__ = importlib.machinery.ModuleSpec(module.__name__, None)
    module.read = read  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, module.__name__, module)
    return calls


def test_custom_parser_is_found_and_called_before_core(tmp_path: Path, testparser: list[str]) -> None:
    write_kind(tmp_path, "custom", DELIVERY_NOTE.replace("delivery_note\n", "custom\n", 1)
             + "  - name: special_number\nparser: testparser\n")
    kind = document_kinds.load("custom", builtin=tmp_path)
    doc = document([(20, [(20, "Lieferschein-Nr.: LS-1")]), (60, [(400, "SN-99")])])
    run = extract(doc, kind.fields, kind=kind)
    values = {e.field: e.value for e in run.results}
    assert values == {"delivery_note_number": "LS-1", "special_number": "SN-99"}
    
    assert testparser == ["delivery_note_number", "special_number"]


def test_without_parser_entry_runs_only_core(tmp_path: Path, testparser: list[str]) -> None:
    write_kind(tmp_path, "delivery_note", DELIVERY_NOTE)
    kind = document_kinds.load("delivery_note", builtin=tmp_path)
    extract(document([(20, [(20, "Lieferschein-Nr.: LS-1")])]), kind.fields, kind=kind)
    assert testparser == []


@pytest.mark.parametrize("name", ["does_not_exist", "..errors", "os.path", "Invoice"])
def test_unknown_parser_name_is_rejected(tmp_path: Path, name: str) -> None:
    write_kind(tmp_path, "broken", f"name: broken\ntitle: K\nparser: '{name}'\nfields: [{{name: a}}]\n")
    error = error_from(tmp_path, "broken")
    assert any(f["location"] == "(File)" or "parser" in f["message"] for f in error.fields["error"])
    assert "parser" in error.detail


# --- Persistence ---------------------------------------------------------------


def test_template_keeps_label_rule(tmp_path: Path) -> None:
    conn = open_database(tmp_path / "test.db")
    try:
        stored = models.save(conn, models.DocumentType(name="Rechnung Nord", fields=SAMPLE_FIELDS))
        loaded = models.load(conn, stored.id or 0)
        assert loaded is not None
        assert [f.label_rule for f in loaded.fields] == [f.label_rule for f in SAMPLE_FIELDS]
        assert isinstance(loaded.fields[1].label_rule, LabelRule)
    finally:
        conn.close()


def test_template_from_existing_database_without_rule_remains_readable(tmp_path: Path) -> None:
    conn = open_database(tmp_path / "test.db")
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            "INSERT INTO document_type (id, name, created_at, updated_at) "
            "VALUES (1, 'Alt', '2026-07-27T10:00:00+02:00', '2026-07-27T10:00:00+02:00')"
        )
        conn.execute(
            "INSERT INTO field (document_type_id, name, locator_json) VALUES "
            "(1, 'document_number', '{\"label\": \"Belegnummer\", \"extractor\": \"document_field\"}')"
        )
        loaded = models.load(conn, 1)
        assert loaded is not None
        assert loaded.fields[0].label_rule is None
        assert loaded.fields[0].extractor == "document_field"
    finally:
        conn.close()

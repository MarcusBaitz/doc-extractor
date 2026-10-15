"""Tests for manual values."""

from __future__ import annotations

from substrakt.extraction.fields import FieldSpec, extract, extract_field
from substrakt.model import PdfRect
from substrakt.store import DocumentStore


def test_manual_value_beats_search(store: DocumentStore, corpus):
    doc = store.load(corpus / "rechnung_din5008.pdf")
    field = FieldSpec(name="invoice_number", json_type="string", question="Rechnungsnummer?")

    needle = extract_field(doc, field)
    entered = extract_field(doc, field, "R-2026-0001")

    assert entered.value == "R-2026-0001"
    assert entered.source == "manual"
    assert entered.confidence == 1.0
    assert entered.value != needle.value or needle.source == "none"


def test_region_remains_evidence(store: DocumentStore, corpus):
    doc = store.load(corpus / "rechnung_din5008.pdf")
    region = PdfRect(page=0, x0=100, y0=700, x1=300, y1=720)
    field = FieldSpec(name="amount", json_type="number", regions=[region])

    result = extract_field(doc, field, "185,40")

    assert result.locator == region
    assert result.grounded


def test_without_region_has_no_locator(store: DocumentStore, corpus):
    doc = store.load(corpus / "rechnung_din5008.pdf")
    field = FieldSpec(name="note", json_type="string")

    result = extract_field(doc, field, "von Hand")

    assert result.locator is None


def test_normalization_also_applies_to_manual_values(store: DocumentStore, corpus):
    doc = store.load(corpus / "rechnung_din5008.pdf")

    amount = extract_field(doc, FieldSpec(name="b", json_type="number"), "1.234,56")
    assert amount.normalized == 1234.56

    date = extract_field(doc, FieldSpec(name="d", json_type="date"), "31.07.2026")
    assert date.normalized == "2026-07-31"


def test_mismatched_input_is_rejected(store: DocumentStore, corpus):
    doc = store.load(corpus / "rechnung_din5008.pdf")

    result = extract_field(doc, FieldSpec(name="b", json_type="number"), "kein Betrag")

    assert not result.grounded
    assert result.note


def test_empty_input_falls_back_to_search(store: DocumentStore, corpus):
    doc = store.load(corpus / "rechnung_din5008.pdf")
    field = FieldSpec(name="invoice_number", json_type="string", question="Rechnungsnummer?")

    assert extract_field(doc, field, "   ").source != "manual"
    assert extract_field(doc, field, None).source != "manual"


def test_transport_form_is_complete(store: DocumentStore, corpus):
    path = corpus / "transportschein-aok.pdf"
    if not path.exists():
        import pytest

        pytest.skip("Transport form is not in the corpus")

    doc = store.load(path)
    page = doc.pages[0]

    def region(x0: float, y0: float, x1: float, y1: float) -> PdfRect:
        return PdfRect(
            page=0,
            x0=x0 * page.width,
            y0=(1 - y1) * page.height,
            x1=x1 * page.width,
            y1=(1 - y0) * page.height,
        )

    fields = [
        FieldSpec(name="carrier_ik", json_type="string",
             regions=[region(0.049, 0.802, 0.307, 0.829)]),
        FieldSpec(name="document_number", json_type="string",
             regions=[region(0.330, 0.802, 0.622, 0.829)]),
        FieldSpec(name="gross_total", json_type="number",
             regions=[region(0.629, 0.802, 0.796, 0.829)]),
        FieldSpec(name="invoice_number", json_type="string",
             regions=[region(0.049, 0.845, 0.351, 0.872)]),
        FieldSpec(name="copayment", json_type="number",
             regions=[region(0.644, 0.845, 0.796, 0.872)]),
    ]
    manual_values = {
        "carrier_ik": "601234567",
        "document_number": "2026071501",
        "gross_total": "185,40",
        "invoice_number": "R-2026-0001",
        "copayment": "10,00",
    }

    run = extract(doc, fields, manual_values)

    assert run.ungrounded == 0
    assert all(e.locator is not None for e in run.results)

    by_name = {e.field: e for e in run.results}
    assert by_name["gross_total"].normalized == 185.40
    assert by_name["copayment"].normalized == 10.00
    assert by_name["carrier_ik"].value == "601234567"

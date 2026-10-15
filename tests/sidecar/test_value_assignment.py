"""Tests for value assignment."""
import asyncio

from substrakt.extraction.fields import SAMPLE_FIELDS, FieldSpec, extract_field
from substrakt.model import Document, DocumentMeta, ImageRect, Page, Word


def document(rows):
    words = []
    for index, row in enumerate(rows):
        for column, text in enumerate(row.split()):
            words.append(Word(text=text, page=0, confidence=0.97,
                locator=ImageRect(page=0, x0=column*100, x1=column*100+90,
                                  y0=index*30, y1=index*30+10)))
    return Document(id="test", filename="scan.png", sha256="test", kind="image",
        pages=[Page(number=0, width=1000, height=1000)], words=words,
        meta=DocumentMeta(size_bytes=1, page_count=1, word_count=len(words), text_source="ocr"))


def field(name):
    return next(f for f in SAMPLE_FIELDS if f.name == name)


def test_document_number_does_not_take_recipient_from_next_line():
    doc = document(["Belegnummer:", "Fränkische"])
    result = extract_field(doc, field("document_number"))
    assert not result.grounded
    assert result.note


def test_total_amount_does_not_take_unit_price_without_label_match():
    doc = document(["8.450,00", "Gesamtbetrag"])
    result = extract_field(doc, field("total_amount"))
    assert not result.grounded
    assert result.note


def test_unambiguous_matches_remain_grounded():
    doc = document(["Belegnummer: AB-2026-0331", "Gesamtbetrag 22.849,78"])
    number = extract_field(doc, field("document_number"))
    amount = extract_field(doc, field("total_amount"))
    assert number.grounded and number.value == "AB-2026-0331"
    assert amount.grounded and amount.normalized == 22849.78


def test_multiline_candidate_remains_visible_for_review():
    doc = document(["Belegnummer:", "AB-2026-0331"])
    result = extract_field(doc, FieldSpec(name="document_number", regex=r"Belegnummer:\s*(\S+)"))
    assert result.value == "AB-2026-0331"
    assert result.locator is not None
    assert not result.grounded
    assert result.confidence == 0
    assert "multiple text lines" in result.note


def test_manual_correction_has_still_priority():
    doc = document(["Belegnummer:", "Fränkische"])
    result = extract_field(doc, field("document_number"), "AB-2026-0331")
    assert result.grounded and result.source == "manual"
    assert result.value == "AB-2026-0331"


def test_explicit_extractor_method_remains_available():
    doc = document(["8.450,00"])
    definition = FieldSpec(name="total_amount", json_type="number", method="extractor", extractor="amount")
    result = extract_field(doc, definition)
    assert result.grounded and result.source == "extractor"


def test_regex_evidence_to_second_page():
    doc = document(["Belegnummer: AB-2026-0331"])
    for word in doc.words:
        word.page = 1
        word.locator.page = 1
    doc.pages.append(Page(number=1, width=1000, height=1000))
    doc.meta.page_count = 2
    result = extract_field(doc, field("document_number"))
    assert result.grounded
    assert result.locator.page == 1
    assert result.matched_text == "AB-2026-0331"


def test_invalid_pattern_falls_not_to_first_amount_back():
    doc = document(["8.450,00"])
    result = extract_field(doc, FieldSpec(name="total_amount", regex="[", json_type="number"))
    assert not result.grounded
    assert result.value is None


def test_export_excludes_uncertain_values_from_and_keeps_provenance(monkeypatch):
    from substrakt.app import STORE, ExtractionRequest, export

    doc = document(["Belegnummer:", "Fränkische", "8.450,00", "Gesamtbetrag"])
    monkeypatch.setattr(STORE, "get", lambda _doc_id: doc)
    request_data = ExtractionRequest(fields=[field("document_number"), field("total_amount")])
    export = asyncio.run(export(doc.id, request_data, None))
    assert export["data"] == {}
    assert export["run"]["ungrounded"] == 2
    assert export["provenance"]["document_number"]["value"] is None
    for entry in export["provenance"].values():
        assert not entry["grounded"]
        assert entry["note"]

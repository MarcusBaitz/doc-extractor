"""Tests for labelled values."""
from substrakt.extraction.fields import SAMPLE_FIELDS, extract_field
from substrakt.model import Document, DocumentMeta, ImageRect, Page, Word


def document(rows):
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


def read_value(doc, name):
    return extract_field(doc, next(f for f in SAMPLE_FIELDS if f.name == name))


def test_form_values_under_two_labels():
    doc = document([(20, [(20, "Belegnummer:"), (280, "Belegdatum:")]),
                    (38, [(20, "ZX-4839"), (280, "16.08.2026")])])
    assert read_value(doc, "document_number").value == "ZX-4839"
    assert read_value(doc, "document_date").normalized == "2026-08-16"


def test_missing_document_date_does_not_take_delivery_date():
    doc = document([(20, [(20, "Belegdatum:")]),
                    (70, [(20, "Lieferdatum: 03.07.2026")])])
    assert read_value(doc, "document_date").value is None


def test_english_labels_and_negative_total_amount():
    doc = document([(20, [(20, "Invoice number: QZ-908")]),
                    (40, [(20, "Invoice date: 2026-09-12")]),
                    (60, [(20, "Total amount: -4,128.65 USD")])])
    assert read_value(doc, "document_number").value == "QZ-908"
    assert read_value(doc, "document_date").normalized == "2026-09-12"
    assert read_value(doc, "total_amount").normalized == -4128.65


def test_other_date_before_issue_date():
    doc = document([(20, [(20, "Lieferdatum: 03.07.2026")]),
                    (40, [(20, "Belegdatum: 09.07.2026")])])
    assert read_value(doc, "document_date").normalized == "2026-07-09"


def test_skewed_ocr_reads_value_right_instead_date_below():
    doc = document([(20, [(20, "Belegnummer:")]),
                    (14, [(200, "QZ-4839")]),
                    (45, [(20, "Belegdatum:"), (200, "16.08.2026")])])
    assert read_value(doc, "document_number").value == "QZ-4839"


def test_two_different_final_amounts_need_review():
    doc = document([(20, [(20, "Gesamtbetrag 123,45")]),
                    (50, [(20, "Gesamtbetrag 678,90")])])
    result = read_value(doc, "total_amount")
    assert result.value is None and not result.grounded
    assert "Conflicting values" in result.note


def test_vat_id_does_not_take_greeting():
    doc = document([(20, [(20, "VAT ID:")]), (40, [(20, "Sehr geehrte Damen")])])
    assert read_value(doc, "vat_id").value is None


def test_tax_amount_after_percentage_and_currency_am_amount():
    doc = document([(20, [(20, "Umsatzsteuer 19 % 41,80 EUR")])])
    assert read_value(doc, "tax_amount").normalized == 41.8
    assert read_value(doc, "currency").value == "EUR"


def test_complex_currency_not_simply_first_match_choose():
    doc = document([(20, [(20, "123,45 EUR")]), (40, [(20, "100,00 USD")])])
    assert read_value(doc, "currency").value is None

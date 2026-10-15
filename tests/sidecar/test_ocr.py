"""Tests for ocr."""

from __future__ import annotations

import pytest

from substrakt.parsers import ocr
from substrakt.store import DocumentStore

pytestmark = pytest.mark.skipif(
    not ocr.available(), reason="Tesseract or deu.traineddata is unavailable"
)


def test_scan_is_read(store: DocumentStore, corpus):
    doc = store.load(corpus / "rechnung_scan_150dpi.png")

    assert doc.meta.text_source == "ocr"
    assert doc.meta.word_count > 30, "too few words for a complete document"

    text = " ".join(w.text for w in doc.words)
    assert "Rechnung" in text


def test_word_coordinates_lie_on_page(store: DocumentStore, corpus):
    doc = store.load(corpus / "rechnung_scan_150dpi.png")
    page = doc.pages[0]

    for word in doc.words:
        locator = word.locator
        assert 0 <= locator.x0 < locator.x1 <= page.width + 1, f"x outside: {word.text}"
        assert 0 <= locator.y0 < locator.y1 <= page.height + 1, f"y outside: {word.text}"


def test_reading_order_remains_preserved(store: DocumentStore, corpus):
    from substrakt.index import words as windex

    doc = store.load(corpus / "rechnung_scan_150dpi.png")
    text = windex.page_text(doc, 0)

    assert "Nordwind Maschinenbau" in text, f"Reading order reversed:\n{text[:300]}"


def test_without_tesseract_is_warned(store: DocumentStore, corpus, monkeypatch):
    monkeypatch.setattr(ocr, "available", lambda: False)

    doc = store.load(corpus / "rechnung_scan_150dpi.png")

    assert doc.meta.text_source == "none"
    assert any("Tesseract" in w for w in doc.meta.warnings)


def test_weak_recognition_is_reported(store: DocumentStore, corpus):
    path = corpus / "transportschein-aok.pdf"
    if not path.exists():
        pytest.skip("Transport form is not in the corpus")

    doc = store.load(path)

    assert doc.meta.text_source == "ocr"
    assert any("Uncertain text recognition" in w for w in doc.meta.warnings), (
        f"No warning despite handwriting: {doc.meta.warnings}"
    )

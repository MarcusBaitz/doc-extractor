"""Tests for parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from substrakt.errors import DocumentCorrupt, DocumentEmpty
from substrakt.index import words as windex
from substrakt.model import PdfRect, SheetRange
from substrakt.parsers import detect_format
from substrakt.store import DocumentStore

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus" / "out"


# --- Format detection ------------------------------------------------------


def test_signature_beats_extension() -> None:
    assert detect_format(CORPUS / "getarnt.pdf") == "image"
    assert detect_format(CORPUS / "rechnung_din5008.pdf") == "pdf"
    assert detect_format(CORPUS / "positionen.xlsx") == "sheet"
    assert detect_format(CORPUS / "artikel_cp1252.csv") == "sheet"
    assert detect_format(CORPUS / "rechnung_mehrseitig.tiff") == "image"


# --- PDF -------------------------------------------------------------------


def test_pdf_with_text_layer(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "rechnung_din5008.pdf"))

    assert doc.kind == "pdf"
    assert doc.meta.page_count == 1
    assert doc.meta.text_source == "text_layer"
    assert doc.meta.word_count > 40, "An invoice contains more than 40 words"
    assert doc.pages[0].has_text_layer

    text = windex.page_text(doc, 0)
    assert "Rechnungsnummer" in text
    assert "2026-0147" in text
    
    
    assert "25.462,13" in text or "8.450,00" in text
    assert "Frässpindel" in text, "Non-ASCII characters must be preserved"


def test_pdf_multipage(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "rechnung_mehrseitig.pdf"))
    assert doc.meta.page_count == 3
    for index in range(3):
        assert doc.words_on_page(index), f"Page {index} has no words"


def test_pdf_coordinates_lie_on_page(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "rotationen.pdf"))

    for word in doc.words:
        assert isinstance(word.locator, PdfRect)
        page = doc.pages[word.page]
        assert 0 <= word.locator.x0 <= page.width, f"x0 outside: {word.locator.x0}"
        assert 0 <= word.locator.x1 <= page.width, f"x1 outside: {word.locator.x1}"
        assert 0 <= word.locator.y0 <= page.height, f"y0 outside: {word.locator.y0}"
        assert 0 <= word.locator.y1 <= page.height, f"y1 outside: {word.locator.y1}"


def test_region_extraction(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "rechnung_din5008.pdf"))

    
    match = next(w for w in doc.words if "2026-0147" in w.text)
    assert isinstance(match.locator, PdfRect)

    region = PdfRect(
        page=match.locator.page,
        x0=match.locator.x0 - 2,
        y0=match.locator.y0 - 2,
        x1=match.locator.x1 + 2,
        y1=match.locator.y1 + 2,
    )
    assert "2026-0147" in windex.text_from_region(doc, region)


def test_pdf_render(store: DocumentStore) -> None:
    from substrakt.parsers.pdf import render_page

    doc = store.load(str(CORPUS / "rechnung_din5008.pdf"))
    png = render_page(store.path(doc.id), 0, scale=1.0)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 1000


# --- Tabellen --------------------------------------------------------------


def test_xlsx_with_sheets(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "positionen.xlsx"))

    assert doc.kind == "sheet"
    assert doc.meta.text_source == "cells"

    names = [p.sheet_name for p in doc.pages]
    assert "Positionen" in names
    assert "Konditionen" in names

    
    
    positions = next(p for p in doc.pages if p.sheet_name == "Positionen")
    assert positions.width <= 10, f"Zu viele Spalten gemeldet: {positions.width}"

    assert not any("abgeschnitten" in w for w in doc.meta.warnings), (
        f"Falsche Abschneide-Warnung: {doc.meta.warnings}"
    )


def test_xlsx_locator_is_cell_range(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "positionen.xlsx"))
    for word in doc.words:
        assert isinstance(word.locator, SheetRange)
        assert word.locator.sheet
        assert word.locator.a1


def test_cell_range_read(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "positionen.xlsx"))
    kopfzeile = windex.text_from_region(doc, SheetRange(sheet="Positionen", a1="A3:F3"))
    assert "Bezeichnung" in kopfzeile
    assert "Menge" in kopfzeile


def test_csv_cp1252(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "artikel_cp1252.csv"))

    assert doc.meta.delimiter == ";"
    assert doc.meta.encoding is not None
    assert doc.meta.encoding.lower().replace("-", "_") in ("cp1252", "windows_1252")

    text = windex.page_text(doc, 0)
    assert "Währung" in text, f"Non-ASCII text decoded incorrectly: {text[:80]}"
    assert "Frässpindel" in text
    assert "Ölmessstab" in text
    assert "‰" not in text, "Mojibake indicates an incorrect encoding"


def test_csv_utf8(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "artikel_utf8.csv"))
    assert doc.meta.delimiter == ","
    assert doc.meta.encoding is not None
    assert "utf" in doc.meta.encoding.lower()
    assert "Frässpindel" in windex.page_text(doc, 0)


# --- Images ----------------------------------------------------------------


def test_image_without_text_layer(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "rechnung_scan_150dpi.png"))

    assert doc.kind == "image"
    assert not doc.pages[0].has_text_layer, "An image never has an embedded text layer"

    if doc.meta.word_count:
        assert doc.meta.text_source == "ocr", (
            "Recognized text must not be reported as an embedded text layer"
        )
    else:
        
        assert doc.meta.text_source == "none"
        assert doc.meta.warnings, "Missing text must produce a warning"


def test_multipage_tiff(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "rechnung_mehrseitig.tiff"))
    assert doc.kind == "image"
    assert doc.meta.page_count == 2





def test_broken_pdf_raises_clear_errors(store: DocumentStore) -> None:
    with pytest.raises(DocumentCorrupt):
        store.load(str(CORPUS / "defekt.pdf"))


def test_empty_csv(store: DocumentStore) -> None:
    with pytest.raises(DocumentEmpty):
        store.load(str(CORPUS / "leer.csv"))


def test_empty_workbook_does_not_crash(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "empty_workbook.xlsx"))
    assert doc.meta.word_count == 0
    assert doc.meta.warnings


def test_disguised_image_is_read_as_image(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "getarnt.pdf"))
    assert doc.kind == "image"


def test_unknown_path(store: DocumentStore) -> None:
    from substrakt.errors import FileNotFound

    with pytest.raises(FileNotFound):
        store.load("/does/not/exist.pdf")


# --- Store -----------------------------------------------------------------


def test_same_file_is_not_parsed_twice(store: DocumentStore) -> None:
    path = str(CORPUS / "rechnung_din5008.pdf")
    erst = store.load(path)
    zweit = store.load(path)
    assert erst.id == zweit.id
    assert len(store) == 1


def test_document_close(store: DocumentStore) -> None:
    doc = store.load(str(CORPUS / "rechnung_din5008.pdf"))
    assert store.remove(doc.id)
    assert not store.remove(doc.id)

    from substrakt.errors import UnknownDocument

    with pytest.raises(UnknownDocument):
        store.get(doc.id)

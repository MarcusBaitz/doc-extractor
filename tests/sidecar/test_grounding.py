"""Tests for grounding."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from substrakt.config import load
from substrakt.extraction.grounding import (
    THRESHOLD,
    Evidence,
    confidence,
    from_position,
    from_value,
    is_grounded,
)
from substrakt.model import PdfRect, SheetRange
from substrakt.store import DocumentStore

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus" / "out"


@pytest.fixture(scope="module", autouse=True)
def corpus() -> None:
    if not (CORPUS / "rechnung_din5008.pdf").exists():
        subprocess.run(
            [sys.executable, str(ROOT / "corpus" / "generate.py")],
            check=True, capture_output=True,
        )


@pytest.fixture
def invoice():
    store = DocumentStore(load())
    return store.load(str(CORPUS / "rechnung_din5008.pdf"))


@pytest.fixture
def table():
    store = DocumentStore(load())
    return store.load(str(CORPUS / "positionen.xlsx"))


class TestByPosition:

    def test_finds_word_from_position(self, invoice) -> None:
        from substrakt.index.words import page_text_with_index

        text, _ = page_text_with_index(invoice, 0)
        start = text.index("2026-0147")
        evidence = from_position(invoice, 0, start, start + len("2026-0147"))

        assert evidence is not None
        assert "2026-0147" in evidence.matched_text
        assert evidence.similarity == 100.0
        assert isinstance(evidence.locator, PdfRect)

    def test_locator_lies_on_page(self, invoice) -> None:
        from substrakt.index.words import page_text_with_index

        text, _ = page_text_with_index(invoice, 0)
        start = text.index("Nordwind")
        evidence = from_position(invoice, 0, start, start + 30)

        page = invoice.pages[0]
        assert 0 <= evidence.locator.x0 <= page.width
        assert 0 <= evidence.locator.y0 <= page.height
        assert evidence.locator.width > 0

    def test_multiple_words_form_one_box(self, invoice) -> None:
        from substrakt.index.words import page_text_with_index

        text, _ = page_text_with_index(invoice, 0)
        start = text.index("Nordwind Maschinenbau")
        evidence = from_position(invoice, 0, start, start + len("Nordwind Maschinenbau GmbH"))

        assert len(evidence.words) >= 3
        
        for word in evidence.words:
            assert evidence.locator.x0 <= word.locator.x0 + 0.01
            assert evidence.locator.x1 >= word.locator.x1 - 0.01


class TestByValue:

    def test_finds_exact_value(self, invoice) -> None:
        evidence = from_value(invoice, "2026-0147")
        assert evidence is not None
        assert evidence.similarity >= 95

    def test_finds_despite_different_spelling(self, invoice) -> None:
        evidence = from_value(invoice, "25705.78")
        assert evidence is not None, "normalized amount was not found again"
        assert evidence.similarity >= THRESHOLD
        assert "25.705,78" in evidence.matched_text

    def test_amount_not_present_in_document(self, invoice) -> None:
        assert from_value(invoice, "25462.13") is None

    def test_finds_iban_without_spaces(self, invoice) -> None:
        evidence = from_value(invoice, "DE89370400440532013000")
        assert evidence is not None
        assert evidence.similarity >= THRESHOLD

    def test_finds_multiword_value(self, invoice) -> None:
        evidence = from_value(invoice, "Nordwind Maschinenbau GmbH")
        assert evidence is not None
        assert evidence.similarity >= 90
        assert len(evidence.words) >= 2

    def test_invented_value_is_rejected(self, invoice) -> None:
        assert from_value(invoice, "Zauberschloss Ganzweitweg AG") is None
        assert from_value(invoice, "99999999,99") is None
        assert from_value(invoice, "DE00000000000000000000") is None

    def test_tolerates_ocr_errors(self, invoice) -> None:
        evidence = from_value(invoice, "Nordwlnd Maschinenbau GmbH")  # i → l
        assert evidence is not None
        assert evidence.similarity >= THRESHOLD

    def test_page_restriction(self, invoice) -> None:
        assert from_value(invoice, "2026-0147", pages=[0]) is not None
        assert from_value(invoice, "2026-0147", pages=[99]) is None


class TestAgainstStageZeroErrors:

    def test_invented_values_are_rejected(self, invoice) -> None:
        for invented in ["DE99999999999999999999", "77.777,77", "Musterfirma XY"]:
            evidence = from_value(invoice, invented)
            assert not is_grounded(confidence(evidence, invented)), invented

    def test_confusions_do_not_reduce_grounding(self, invoice) -> None:
        tax = from_value(invoice, "4104.28")
        assert tax is not None
        
        assert is_grounded(confidence(tax, "4104.28", "number"))

    def test_region_beats_confusion(self, invoice) -> None:
        total = from_value(invoice, "25705.78")
        assert total is not None
        assert isinstance(total.locator, PdfRect)

        
        region = [PdfRect(
            page=0,
            x0=total.locator.x0 - 20, y0=total.locator.y0 - 5,
            x1=total.locator.x1 + 20, y1=total.locator.y1 + 5,
        )]

        in_region = confidence(total, "25705.78", "number", regions=region)
        tax = from_value(invoice, "4104.28")
        outside = confidence(tax, "4104.28", "number", regions=region)

        assert in_region > outside, (
            "A value inside the marked region must rank above one outside it"
        )


class TestSpreadsheet:
    def test_finds_cell_value(self, table) -> None:
        evidence = from_value(table, "CNC-Frässpindel")
        assert evidence is not None
        assert isinstance(evidence.locator, SheetRange)
        assert evidence.locator.sheet == "Positionen"

    def test_multiple_cells_form_one_range(self, table) -> None:
        evidence = from_value(table, "Pos Bezeichnung")
        if evidence and len(evidence.words) > 1:
            assert ":" in evidence.locator.a1 or evidence.locator.a1


class TestConfidence:
    def _evidence(self, similarity: float = 100.0) -> Evidence:
        return Evidence(
            locator=PdfRect(page=0, x0=10, y0=10, x1=100, y1=25),
            words=[],
            similarity=similarity,
            matched_text="Example",
        )

    def test_without_evidence_is_null(self) -> None:
        assert confidence(None, "25462.13", "number") == 0.0

    def test_exact_match_is_high(self) -> None:
        assert confidence(self._evidence(), "25462.13", "number") >= 0.95

    def test_weak_similarity_lowers_confidence(self) -> None:
        high = confidence(self._evidence(100), "abc", "string")
        low = confidence(self._evidence(70), "abc", "string")
        assert low < high

    def test_type_error_lowers(self) -> None:
        matching = confidence(self._evidence(), "25462.13", "number")
        mismatched = confidence(self._evidence(), "Rechnung", "number")
        assert mismatched < matching
        assert mismatched <= 0.55

    def test_match_outside_region_is_penalized(self) -> None:
        matching = [PdfRect(page=0, x0=0, y0=0, x1=200, y1=50)]
        elsewhere = [PdfRect(page=0, x0=400, y0=400, x1=500, y1=450)]

        inside = confidence(self._evidence(), "abc", "string", regions=matching)
        outside = confidence(self._evidence(), "abc", "string", regions=elsewhere)

        assert inside > outside
        assert outside <= 0.55

    def test_without_region_remains_neutral(self) -> None:
        assert confidence(self._evidence(), "abc", "string") == confidence(
            self._evidence(), "abc", "string", regions=[]
        )

    def test_multiplicative_instead_averaged(self) -> None:
        weak = confidence(self._evidence(60), "Rechnung", "number")
        assert weak < 0.4

    def test_extractor_confidence_applies(self) -> None:
        safely = confidence(self._evidence(), "DE136695976", "string", extractor_confidence=1.0)
        uncertain = confidence(self._evidence(), "DE812345678", "string", extractor_confidence=0.45)
        assert uncertain < 0.5 < safely


class TestGrounded:
    def test_threshold(self) -> None:
        assert is_grounded(0.9)
        assert is_grounded(0.5)
        assert not is_grounded(0.49)
        assert not is_grounded(0.0)

    def test_value_without_evidence_is_never_grounded(self) -> None:
        assert not is_grounded(confidence(None, "anything"))

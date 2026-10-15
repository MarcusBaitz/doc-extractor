"""Tests for fields."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from substrakt.config import load
from substrakt.extraction.fields import SAMPLE_FIELDS, FieldSpec, extract, extract_field
from substrakt.model import PdfRect
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
    return DocumentStore(load()).load(str(CORPUS / "rechnung_din5008.pdf"))


class TestFieldName:
    def test_valid_names(self) -> None:
        for name in ["amount", "gross_amount", "_internal", "field1"]:
            assert FieldSpec(name=name).name == name

    @pytest.mark.parametrize("name", ["1field", "with spaces", "with-dash", "", "ä"])
    def test_invalid_names(self, name: str) -> None:
        with pytest.raises(ValidationError):
            FieldSpec(name=name)


class TestOrder:
    def test_region_beats_regex(self, invoice) -> None:
        
        field = FieldSpec(
            name="sender",
            regex=r"(Südwerk\s+\S+)",  
            regions=[PdfRect(page=0, x0=60, y0=770, x1=400, y1=795)],
        )
        result = extract_field(invoice, field)

        assert result.source == "region"
        assert "Nordwind" in (result.value or "")

    def test_regex_beats_extractor(self, invoice) -> None:
        field = FieldSpec(
            name="document_date",
            json_type="date",
            regex=r"Lieferdatum:\s*(\d{2}\.\d{2}\.\d{4})",
            extractor="date",  
        )
        result = extract_field(invoice, field)

        assert result.source == "regex"
        assert result.normalized == "2026-07-22"  

    def test_extractor_when_nothing_other(self, invoice) -> None:
        result = extract_field(invoice, FieldSpec(name="iban"))
        assert result.source == "extractor"
        assert result.value == "DE89370400440532013000"
        assert result.confidence == 1.0

    def test_method_force(self, invoice) -> None:
        field = FieldSpec(name="iban", method="regex", regex=r"does-not-exist-(\d+)")
        result = extract_field(invoice, field)
        assert result.source == "none"
        assert not result.grounded


class TestResult:
    def test_every_value_has_a_evidence(self, invoice) -> None:
        run = extract(invoice, SAMPLE_FIELDS)
        for e in run.results:
            if e.grounded:
                assert e.locator is not None, f"{e.field} is grounded but has no evidence"
                assert e.matched_text

    def test_normalization_by_type(self, invoice) -> None:
        amount = extract_field(
            invoice,
            FieldSpec(name="total_amount", json_type="number",
                 regex=r"Gesamtbetrag\s+([\d.]+,\d{2})"),
        )
        assert amount.value == "25.705,78"
        assert amount.normalized == 25705.78  # As represented in exports.

    def test_ungrounded_field_names_the_reason(self, invoice) -> None:
        result = extract_field(invoice, FieldSpec(name="sender"))
        assert not result.grounded
        assert "mark a region" in result.note

    def test_sample_fields_find_the_most(self, invoice) -> None:
        run = extract(invoice, SAMPLE_FIELDS)
        grounded = len(run.results) - run.ungrounded
        
        assert grounded >= len(SAMPLE_FIELDS) - 1

    def test_budget(self, invoice) -> None:
        run = extract(invoice, SAMPLE_FIELDS)
        assert run.duration_ms < 1000, f"{run.duration_ms} ms exceeds the 1000 ms budget"


class TestSpreadsheet:
    def test_cell_range_as_region(self) -> None:
        from substrakt.model import SheetRange

        doc = DocumentStore(load()).load(str(CORPUS / "positionen.xlsx"))
        field = FieldSpec(
            name="first_item",
            regions=[SheetRange(sheet="Positionen", a1="B4")],
        )
        result = extract_field(doc, field)
        assert result.source == "region"
        assert "Frässpindel" in (result.value or "")

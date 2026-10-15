"""Tests for normalization."""

from __future__ import annotations

import pytest

from substrakt.extraction.normalization import (
    amount,
    apply,
    clean_text,
    date,
    for_type,
    percent,
)


class TestAmount:
    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [
            # Deutscher Normalfall
            ("25.462,13", 25462.13),
            ("8.450,00", 8450.0),
            ("1.290,50", 1290.5),
            ("0,5", 0.5),
            ("84,25", 84.25),
            
            ("2400,00", 2400.0),
            ("42", 42.0),
            
            ("25.462", 25462.0),
            ("1.234", 1234.0),
            ("1.234.567", 1234567.0),
            # English month names also occur in exports.
            ("25,462.13", 25462.13),
            ("1,234.56", 1234.56),
            ("8450.00", 8450.0),
            # Signs may be leading or trailing, as in accounting systems.
            ("-1.234,56", -1234.56),
            ("1.234,56-", -1234.56),
            
            ("25.462,13 EUR", 25462.13),
            ("EUR 25.462,13", 25462.13),
            ("€ 1.000,00", 1000.0),
            
            ("25.462,13 EUR", 25462.13),
            ("1 234,56", 1234.56),
        ],
    )
    def test_recognizes_format_from_structure(self, input_value: str, expected: float) -> None:
        assert amount(input_value) == pytest.approx(expected)

    def test_thousands_separator_is_not_to_decimal_separator(self) -> None:
        assert amount("1.234") == 1234.0
        assert amount("25.462") == 25462.0
        
        assert amount("1.23") == 1.23

    @pytest.mark.parametrize("input_value", ["", "   ", "kein Betrag", "EUR", "-", "1.2.3,4,5"])
    def test_prefer_nothing_as_guess(self, input_value: str) -> None:
        assert amount(input_value) is None


class TestPercent:
    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [("19 %", 19.0), ("19%", 19.0), ("2,5 %", 2.5), ("2 % Skonto", 2.0),
         ("Umsatzsteuer 19 %", 19.0)],
    )
    def test_percentages(self, input_value: str, expected: float) -> None:
        assert percent(input_value) == pytest.approx(expected)

    def test_without_sign_is_not_a_percentage(self) -> None:
        assert percent("19") is None


class TestDate:
    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [
            # DIN 5008
            ("25.07.2026", "2026-07-25"),
            ("25.7.2026", "2026-07-25"),
            ("05.06.2026", "2026-06-05"),
            # Two-digit year.
            ("25.07.26", "2026-07-25"),
            ("25.07.95", "1995-07-25"),
            # Other separators.
            ("25/07/2026", "2026-07-25"),
            ("25-07-2026", "2026-07-25"),
            # ISO remains ISO.
            ("2026-07-25", "2026-07-25"),
            # Spelled-out month.
            ("25. Juli 2026", "2026-07-25"),
            ("25.Juli 2026", "2026-07-25"),
            ("1. März 2026", "2026-03-01"),
            ("25. Jul. 2026", "2026-07-25"),
            ("25. Dezember 26", "2026-12-25"),
        ],
    )
    def test_variants(self, input_value: str, expected: str) -> None:
        assert date(input_value) == expected

    @pytest.mark.parametrize(
        "input_value",
        [
            "31.02.2026",   
            "32.01.2026",
            "25.13.2026",
            "25. Schmonzember 2026",
            "irgendwas",
            "",
        ],
    )
    def test_impossible_date_is_abgelehnt(self, input_value: str) -> None:
        assert date(input_value) is None

    def test_year_boundary(self) -> None:
        assert date("01.01.69").startswith("2069")
        assert date("01.01.70").startswith("1970")


class TestText:
    def test_normalizes_spaces(self) -> None:
        assert clean_text("  viel   Platz \n hier ") == "viel Platz hier"

    def test_nonbreaking_spaces(self) -> None:
        assert clean_text("Nordwind Maschinenbau") == "Nordwind Maschinenbau"
        assert clean_text("25 462") == "25 462"


class TestAssignment:
    def test_apply_by_names(self) -> None:
        assert apply("amount", "25.462,13") == pytest.approx(25462.13)
        assert apply("date", "25.07.2026") == "2026-07-25"
        assert apply("gross", "abc") == "ABC"

    def test_unknown_name_leaves_value_unchanged(self) -> None:
        assert apply("zauberei", "25.462,13") == "25.462,13"
        assert apply(None, "unverändert") == "unverändert"

    def test_default_by_json_type(self) -> None:
        assert for_type("date") == "date"
        assert for_type("number") == "amount"
        assert for_type("boolean") is None

"""Tests for extractors."""

from __future__ import annotations

import pytest

from substrakt.extraction.extractors import (
    amounts,
    bic,
    date,
    iban,
    iban_valid,
    payment_terms,
    percentages,
    postcode_city,
    suggestion_for,
    tax_number,
    vat_id,
    vat_id_valid,
)


class TestIban:
    
    @pytest.mark.parametrize(
        "number",
        [
            "DE89370400440532013000",
            "DE89 3704 0044 0532 0130 00",
            "DE79600501010002034567",
            "AT611904300234573201",
            "CH9300762011623852957",
        ],
    )
    def test_valid_iban(self, number: str) -> None:
        assert iban_valid(number)

    @pytest.mark.parametrize(
        ("number", "reason"),
        [
            ("DE89370400440532013001", "last digit changed"),
            ("DE88370400440532013000", "check digit changed"),
            ("DE8937040044053201300", "one digit too short"),
            ("DE893704004405320130000", "one digit too long"),
            ("XX89370400440532013000", "missing country code"),
            ("", "empty"),
        ],
    )
    def test_invalid_iban(self, number: str, reason: str) -> None:
        assert not iban_valid(number), reason

    def test_finds_iban_in_text(self) -> None:
        text = "Bankverbindung: IBAN DE89 3704 0044 0532 0130 00 · BIC COBADEFFXXX"
        matches = iban(text)
        assert len(matches) == 1
        assert matches[0].value == "DE89370400440532013000"
        assert matches[0].confidence == 1.0
        assert text[matches[0].start : matches[0].end].replace(" ", "") == matches[0].value

    def test_wrong_checksum_is_not_a_match(self) -> None:
        assert iban("IBAN DE89 3704 0044 0532 0130 01") == []


class TestVatId:
    def test_check_digit(self) -> None:
        
        assert vat_id_valid("DE136695976")
        assert not vat_id_valid("DE136695977")
        assert not vat_id_valid("DE12345678")  

    def test_invalid_is_reported_but_weak(self) -> None:
        matches = vat_id("USt-IdNr.: DE812345678")
        assert len(matches) == 1
        assert matches[0].confidence < 0.5

    def test_valid_has_full_confidence(self) -> None:
        matches = vat_id("USt-IdNr.: DE136695976")
        assert matches[0].confidence == 1.0


class TestBic:
    def test_finds_bic(self) -> None:
        matches = bic("BIC COBADEFFXXX für die Überweisung")
        assert any(f.value == "COBADEFFXXX" for f in matches)

    def test_common_word_is_not_a_bic(self) -> None:
        assert not any(f.value == "RECHNUNG" for f in bic("RECHNUNG NR 4711"))


class TestDate:
    def test_finds_and_normalizes(self) -> None:
        matches = date("Rechnungsdatum: 25.07.2026, Lieferdatum: 22.07.2026")
        assert [f.value for f in matches] == ["2026-07-25", "2026-07-22"]

    def test_impossible_date_is_not_reported(self) -> None:
        assert date("Stichtag 31.02.2026") == []

    def test_spelled_out(self) -> None:
        assert date("Berlin, 25. Juli 2026")[0].value == "2026-07-25"


class TestAmounts:
    def test_finds_amounts(self) -> None:
        text = "Nettobetrag 21.601,50 EUR\nUmsatzsteuer 19 % 4.104,28 EUR"
        values = [f.value for f in amounts(text)]
        assert "21601.50" in values
        assert "4104.28" in values

    def test_quantity_is_not_an_amount(self) -> None:
        values = [f.value for f in amounts("Menge 2 Stück, Pos 12")]
        assert values == []

    def test_without_currency(self) -> None:
        assert any(f.value == "8450.00" for f in amounts("Einzelpreis 8.450,00"))


class TestPercent:
    def test_finds_rates(self) -> None:
        values = [f.value for f in percentages("Umsatzsteuer 19 %, Skonto 2,5 %")]
        assert "19" in values
        assert "2.5" in values


class TestPaymentTerms:
    def test_discount_and_net(self) -> None:
        matches = payment_terms("Zahlungsbedingungen: 14 Tage 2 % Skonto, 30 Tage netto.")
        kinds = {f.kind: f.value for f in matches}
        assert kinds["skonto"] == "14/2"
        assert kinds["netto"] == "30"


class TestPostcodeCity:
    def test_finds_postcode_and_city(self) -> None:
        matches = postcode_city("Am Grubenrand 12\n70565 Stuttgart")
        assert matches[0].value == "70565 Stuttgart"

    def test_multiword_city_name(self) -> None:
        assert postcode_city("24103 Kiel Holtenau")[0].value.startswith("24103 Kiel")


class TestTaxNumber:
    def test_regional_form(self) -> None:
        assert tax_number("Steuernummer: 20/123/45678")[0].value == "20/123/45678"


class TestSuggestion:
    @pytest.mark.parametrize(
        ("field_name", "expected"),
        [
            ("iban", "iban"),
            ("rechnungsdatum", "date"),
            ("total_amount", "amount"),
            ("betrag_brutto", "amount"),
            ("USt-IdNr", "vat_id"),
            ("rechnung_gesamtbetrag_brutto", "amount"),
            ("sender", None),
        ],
    )
    def test_maps_field_names_to(self, field_name: str, expected: str | None) -> None:
        assert suggestion_for(field_name) == expected


class TestAgainstRealDocument:

    DOCUMENT = """Nordwind Maschinenbau GmbH
Industriestraße 47 · 24103 Kiel
Südwerk Präzisionstechnik AG
Am Grubenrand 12
70565 Stuttgart
Rechnungsnummer: 2026-0147
Rechnungsdatum: 25.07.2026
USt-IdNr.: DE136695976
Nettobetrag 21.601,50 EUR
Umsatzsteuer 19 % 4.104,28 EUR
Gesamtbetrag 25.705,78 EUR
Zahlungsbedingungen: 14 Tage 2 % Skonto, 30 Tage netto.
Bankverbindung: IBAN DE89 3704 0044 0532 0130 00 · BIC COBADEFFXXX
Steuernummer: 20/123/45678"""

    def test_finds_all_core_fields(self) -> None:
        assert iban(self.DOCUMENT)[0].value == "DE89370400440532013000"
        assert vat_id(self.DOCUMENT)[0].confidence == 1.0
        assert date(self.DOCUMENT)[0].value == "2026-07-25"
        assert tax_number(self.DOCUMENT)[0].value == "20/123/45678"
        assert "25705.78" in [f.value for f in amounts(self.DOCUMENT)]
        assert {f.kind for f in payment_terms(self.DOCUMENT)} == {"skonto", "netto"}
        assert postcode_city(self.DOCUMENT)[0].value == "24103 Kiel"

    def test_positions_point_to_the_correct_text(self) -> None:
        for evidence in iban(self.DOCUMENT) + date(self.DOCUMENT) + amounts(self.DOCUMENT):
            substring = self.DOCUMENT[evidence.start : evidence.end]
            assert substring.strip(), "Evidence zeigt auf clear Text"

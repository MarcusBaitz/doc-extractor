"""Extract structured values from German business documents."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from substrakt.extraction import normalization


@dataclass(frozen=True)
class Match:

    value: str
    start: int
    end: int
    confidence: float
    kind: str

    @property
    def length(self) -> int:
        return self.end - self.start


# --- IBAN ------------------------------------------------------------------


_IBAN = re.compile(
    r"\b([A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?)\b"
)



_IBAN_LENGTH = {
    "DE": 22, "AT": 20, "CH": 21, "LI": 21, "LU": 20, "NL": 18, "BE": 16,
    "FR": 27, "IT": 27, "ES": 24, "PL": 28, "CZ": 24, "DK": 18, "SE": 24,
    "GB": 22, "IE": 22, "PT": 25, "FI": 18, "NO": 15, "HU": 28,
}


def iban_valid(candidate: str) -> bool:
    raw = re.sub(r"\s", "", candidate).upper()
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]+$", raw):
        return False

    expected_length = _IBAN_LENGTH.get(raw[:2])
    if expected_length and len(raw) != expected_length:
        return False
    if not 15 <= len(raw) <= 34:
        return False

    rearranged = raw[4:] + raw[:4]
    digits = "".join(
        str(ord(z) - 55) if z.isalpha() else z for z in rearranged
    )
    return int(digits) % 97 == 1


def iban(text: str) -> list[Match]:
    match = []
    for m in _IBAN.finditer(text.upper()):
        candidate = m.group(1)
        if iban_valid(candidate):
            match.append(Match(
                value=re.sub(r"\s", "", candidate),
                start=m.start(1), end=m.end(1),
                confidence=1.0,  
                kind="iban",
            ))
    return match


# --- BIC -------------------------------------------------------------------


_BIC = re.compile(r"\b([A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b")



_NOT_BIC = {"RECHNUNG", "LIEFERUNG", "ABTEILUNG", "BESTELLUNG", "ZAHLUNG"}


def bic(text: str) -> list[Match]:
    match = []
    for m in _BIC.finditer(text.upper()):
        candidate = m.group(1)
        if candidate in _NOT_BIC:
            continue
        
        if not candidate[4:6].isalpha() or candidate[6] == "O":
            continue
        match.append(Match(
            value=candidate, start=m.start(1), end=m.end(1),
            confidence=0.75, kind="bic",
        ))
    return match


# --- USt-IdNr. -------------------------------------------------------------

_USTID = re.compile(r"\b(DE\s?\d{9})\b")


def vat_id_valid(number: str) -> bool:
    digits = re.sub(r"\D", "", number)
    if len(digits) != 9:
        return False

    product = 10
    for character in digits[:8]:
        sum_ = (int(character) + product) % 10
        if sum_ == 0:
            sum_ = 10
        product = (2 * sum_) % 11

    check_digit = (11 - product) % 10
    return check_digit == int(digits[8])


def vat_id(text: str) -> list[Match]:
    match = []
    for m in _USTID.finditer(text.upper()):
        raw = m.group(1).replace(" ", "")
        valid = vat_id_valid(raw)
        match.append(Match(
            value=raw, start=m.start(1), end=m.end(1),
            confidence=1.0 if valid else 0.45,
            kind="vat_id",
        ))
    return match


# --- Tax number ------------------------------------------------------------


_TAX_NUMBER = re.compile(r"\b(\d{2,3}/\d{3}/\d{4,5})\b")


def tax_number(text: str) -> list[Match]:
    return [
        Match(value=m.group(1), start=m.start(1), end=m.end(1),
                confidence=0.85, kind="tax_number")
        for m in _TAX_NUMBER.finditer(text)
    ]


# --- Date ------------------------------------------------------------------

_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}\.\s?(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September"
    r"|Oktober|November|Dezember|Jan|Feb|Mrz|Apr|Jun|Jul|Aug|Sep|Okt|Nov|Dez)\.?"
    r"\s?\d{2,4})\b",
    re.IGNORECASE,
)


def date(text: str) -> list[Match]:
    match = []
    for m in _DATE_PATTERN.finditer(text):
        iso = normalization.date(m.group(1))
        if iso:
            match.append(Match(
                value=iso, start=m.start(1), end=m.end(1),
                confidence=0.9, kind="date",
            ))
    return match




_AMOUNT = re.compile(
    r"(?<![\d.,])(-?\d{1,3}(?:[.\s]\d{3})*,\d{2}|-?\d+,\d{2})"
    r"\s*(?:EUR|€)?(?![\d,])",
    re.IGNORECASE,
)


def amounts(text: str) -> list[Match]:
    match = []
    for m in _AMOUNT.finditer(text):
        value = normalization.amount(m.group(1))
        if value is not None:
            match.append(Match(
                value=f"{value:.2f}", start=m.start(1), end=m.end(1),
                confidence=0.85, kind="amount",
            ))
    return match




_PERCENT = re.compile(r"\b(\d{1,2}(?:,\d{1,2})?)\s*%")


def percentages(text: str) -> list[Match]:
    match = []
    for m in _PERCENT.finditer(text):
        value = normalization.amount(m.group(1))
        if value is not None:
            match.append(Match(
                value=f"{value:g}", start=m.start(1), end=m.end(1),
                confidence=0.9, kind="percent",
            ))
    return match


# --- Payment terms ---------------------------------------------------------

_SKONTO = re.compile(
    r"(\d{1,3})\s*Tage?n?\s*(\d{1,2}(?:,\d{1,2})?)\s*%\s*Skonto",
    re.IGNORECASE,
)
_NETTO = re.compile(r"(\d{1,3})\s*Tage?n?\s*netto", re.IGNORECASE)


def payment_terms(text: str) -> list[Match]:
    match = []
    for m in _SKONTO.finditer(text):
        days, percent = m.group(1), m.group(2).replace(",", ".")
        match.append(Match(
            value=f"{days}/{percent}", start=m.start(), end=m.end(),
            confidence=0.9, kind="skonto",
        ))
    for m in _NETTO.finditer(text):
        match.append(Match(
            value=m.group(1), start=m.start(), end=m.end(),
            confidence=0.9, kind="netto",
        ))
    return match






_PLZ_ORT = re.compile(
    r"\b(\d{5})[ \t]+([A-ZÄÖÜ][\wÄÖÜäöüß.\-]+(?:[ \t][A-ZÄÖÜ][\wÄÖÜäöüß.\-]+)*)"
)


def postcode_city(text: str) -> list[Match]:
    match = []
    for m in _PLZ_ORT.finditer(text):
        postcode = m.group(1)
        if postcode.startswith("00"):
            continue
        match.append(Match(
            value=f"{postcode} {m.group(2)}", start=m.start(), end=m.end(),
            confidence=0.8, kind="postcode_city",
        ))
    return match


# --- Registry --------------------------------------------------------------

EXTRACTORS: dict[str, Callable[[str], list[Match]]] = {
    "iban": iban,
    "bic": bic,
    "vat_id": vat_id,
    "tax_number": tax_number,
    "date": date,
    "amount": amounts,
    "percent": percentages,
    "payment_terms": payment_terms,
    "postcode_city": postcode_city,
}



NAME_TO_KIND = {
    "iban": "iban",
    "bic": "bic",
    "ust_idnr": "vat_id", "vat_id": "vat_id", "umsatzsteuer_id": "vat_id",
    "tax_number": "tax_number",
    "rechnungsdatum": "date", "belegdatum": "date", "date": "date",
    "document_date": "date",
    "lieferdatum": "date", "faelligkeit": "date",
    "amount": "amount", "gesamtbetrag": "amount", "nettobetrag": "amount",
    "total_amount": "amount", "net_amount": "amount", "tax_amount": "amount",
    "bruttobetrag": "amount", "betrag_brutto": "amount", "betrag_netto": "amount",
    "steuersatz": "percent", "mwst_satz": "percent",
    "payment_terms": "payment_terms", "skonto": "payment_terms",
    "postcode": "postcode_city", "location": "postcode_city",
}


def all_matches(text: str, kinds: list[str] | None = None) -> dict[str, list[Match]]:
    selected = kinds or list(EXTRACTORS)
    return {
        kind: EXTRACTORS[kind](text)
        for kind in selected
        if kind in EXTRACTORS
    }


def suggestion_for(field_name: str) -> str | None:
    name = field_name.strip().lower().replace("-", "_").replace(" ", "_")
    if name in NAME_TO_KIND:
        return NAME_TO_KIND[name]
    
    for key, kind in NAME_TO_KIND.items():
        if key in name:
            return kind
    return None

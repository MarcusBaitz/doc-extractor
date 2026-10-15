"""Normalize formats found in German business documents."""

from __future__ import annotations

import re
import unicodedata
from datetime import date as date_type

_NUR_ZIFFERN = re.compile(r"^-?\d+$")

_GRUPPIERT_PUNKT = re.compile(r"^-?\d{1,3}(?:\.\d{3})+$")
_GRUPPIERT_KOMMA = re.compile(r"^-?\d{1,3}(?:,\d{3})+$")

_WAEHRUNG = re.compile(r"(?:EUR|USD|CHF|GBP|€|\$|£|CHF)\s*", re.IGNORECASE)


def amount(text: str) -> float | None:
    if not text:
        return None

    raw = _WAEHRUNG.sub("", str(text)).strip()
    
    raw = raw.replace(" ", "").replace(" ", "").replace(" ", "")
    # Minus in verschiedenen Schreibweisen, auch nachgestellt (1.234,56-)
    raw = raw.replace("−", "-").replace("–", "-")
    if raw.endswith("-"):
        raw = "-" + raw[:-1]

    if not raw or not re.search(r"\d", raw):
        return None

    if not re.match(r"^-?[\d.,]+$", raw):
        return None

    hat_punkt = "." in raw
    hat_komma = "," in raw

    try:
        
        
        if hat_punkt and hat_komma:
            if raw.rfind(",") > raw.rfind("."):
                return float(raw.replace(".", "").replace(",", "."))
            return float(raw.replace(",", ""))

        
        
        
        
        
        if hat_punkt:
            if _GRUPPIERT_PUNKT.match(raw):
                return float(raw.replace(".", ""))
            return float(raw)  # 8450.00, 1.23 → Dezimalpunkt

        if hat_komma:
            if _GRUPPIERT_KOMMA.match(raw):
                return float(raw.replace(",", ""))
            return float(raw.replace(",", "."))  # 0,5 · 84,25 → Dezimalkomma

        if _NUR_ZIFFERN.match(raw):
            return float(raw)
    except ValueError:
        return None

    return None


def percent(text: str) -> float | None:
    if not text:
        return None
    match = re.search(r"(-?[\d.,]+)\s*%", str(text))
    if not match:
        return None
    return amount(match.group(1))


# --- Date ------------------------------------------------------------------

_MONTHS = {
    "januar": 1, "jänner": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
    "oktober": 10, "november": 11, "dezember": 12,
    "jan": 1, "feb": 2, "mrz": 3, "mär": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "okt": 10, "nov": 11, "dez": 12,
}

_NUMERISCH = re.compile(r"^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})\.?$")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_SPELLED_OUT = re.compile(r"^(\d{1,2})\.?\s*([A-Za-zÄÖÜäöüß]+)\.?\s*(\d{2,4})$")


def _complete_year(year: int) -> int:
    if year >= 100:
        return year
    return 2000 + year if year < 70 else 1900 + year


def date(text: str) -> str | None:
    if not text:
        return None

    raw = str(text).strip().replace(" ", " ")
    raw = re.sub(r"\s+", " ", raw)

    if match := _ISO.match(raw):
        year, month, day = (int(group) for group in match.groups())
    elif match := _NUMERISCH.match(raw):
        day, month, year = (int(group) for group in match.groups())
        year = _complete_year(year)
    elif match := _SPELLED_OUT.match(raw):
        day = int(match.group(1))
        month_name = unicodedata.normalize("NFC", match.group(2)).lower()
        if month_name not in _MONTHS:
            return None
        month = _MONTHS[month_name]
        year = _complete_year(int(match.group(3)))
    else:
        return None

    try:
        return date_type(year, month, day).isoformat()
    except ValueError:
        return None


# --- Text ------------------------------------------------------------------


def clean_text(value: str) -> str:
    if not value:
        return ""
    cleaned = str(value).replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def remove_line_breaks(value: str) -> str:
    return clean_text(str(value).replace("\n", " "))


def uppercase(value: str) -> str:
    return clean_text(value).upper()


def lowercase(value: str) -> str:
    return clean_text(value).lower()


# --- Assignment -------------------------------------------------------------


NORMALIZERS = {
    "text": clean_text,
    "rows": remove_line_breaks,
    "gross": uppercase,
    "klein": lowercase,
    "amount": amount,
    "percent": percent,
    "date": date,
}


def apply(name: str | None, value: str) -> object:
    if not name or name not in NORMALIZERS:
        return value
    return NORMALIZERS[name](value)


def for_type(json_type: str) -> str | None:
    return {
        "date": "date",
        "number": "amount",
        "integer": "amount",
        "string": "text",
    }.get(json_type)

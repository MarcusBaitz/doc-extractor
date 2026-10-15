"""Field definitions and extraction orchestration."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from substrakt.extraction import extractors, grounding, labels, normalization
from substrakt.index import words as windex
from substrakt.model import Document, Locator
from substrakt.parsers import ocr

if TYPE_CHECKING:
    from substrakt.document_kinds import DocumentKind

JsonType = Literal["string", "number", "integer", "date", "boolean"]
Method = Literal["auto", "region", "regex", "extractor"]

_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class FieldSpec(BaseModel):
    """Definition of one value to extract."""

    name: str = Field(description="JSON output key")
    label: str = Field(default="", description="Display name for the interface")
    question: str = ""
    json_type: JsonType = "string"
    required: bool = False
    method: Method = "auto"
    regex: str | None = None
    extractor: str | None = None
    normalization: str | None = None
    regions: list[Locator] = Field(default_factory=list)
    # A document-kind YAML file may define how to locate the adjacent value.
    label_rule: labels.LabelRule | None = None

    @field_validator("name")
    @classmethod
    def _valid_identifier(cls, value: str) -> str:
        """Require a name that can be used as a JSON key."""
        if not _IDENTIFIER.match(value):
            raise ValueError(
                f"{value!r} is not a valid field name. Use letters, digits and "
                "underscores, starting with a letter or underscore."
            )
        return value


class ExtractionResult(BaseModel):
    """An extracted value together with verification details."""

    field: str
    value: str | None = None
    normalized: str | float | bool | None = None
    confidence: float = 0.0
    source: Literal["region", "regex", "extractor", "manual", "none"] = "none"
    locator: Locator | None = None
    matched_text: str = ""
    grounded: bool = False
    note: str = ""


class ExtractionRun(BaseModel):

    results: list[ExtractionResult] = Field(default_factory=list)
    duration_ms: int = 0
    ungrounded: int = 0


# --- Extraction by field ----------------------------------------------------


def _from_region(doc: Document, field: FieldSpec) -> tuple[str, Locator, float] | None:
    for region in field.regions:
        text = windex.text_from_region(doc, region).strip()
        if text:
            return text, region, 1.0
    return None


@dataclass(frozen=True)
class _RegexMatch:
    text: str
    page: int
    start: int
    end: int
    multiline: bool


def _from_regex(doc: Document, field: FieldSpec) -> _RegexMatch | None:
    if not field.regex:
        return None
    try:
        patterns = re.compile(field.regex, re.IGNORECASE | re.MULTILINE)
    except re.error:
        return None

    for page in range(len(doc.pages)):
        text, _ = windex.page_text_with_index(doc, page)
        if match := patterns.search(text):
            group = 1 if match.groups() else 0
            return _RegexMatch(
                text=match.group(group),
                page=page,
                start=match.start(group),
                end=match.end(group),
                multiline="\n" in match.group(0),
            )
    return None


def _from_extractor(doc: Document, field: FieldSpec) -> tuple[str, int, int, float, int] | None:
    kind = field.extractor or extractors.suggestion_for(field.name)
    if not kind or kind not in extractors.EXTRACTORS:
        return None

    for page in range(len(doc.pages)):
        text, _ = windex.page_text_with_index(doc, page)
        matches = extractors.EXTRACTORS[kind](text)
        if matches:
            
            
            
            best = matches[0]
            return best.value, best.start, best.end, best.confidence, page
    return None


def _manual(field: FieldSpec, value: str) -> ExtractionResult:
    normalizer_name = field.normalization or normalization.for_type(field.json_type)
    normalized = normalization.apply(normalizer_name, value)

    note = ""
    if normalized is None and normalizer_name:
        note = f"Input does not match type {field.json_type!r}"

    return ExtractionResult(
        field=field.name,
        value=value,
        normalized=normalized if isinstance(normalized, (str, float, bool)) else None,
        confidence=1.0,
        source="manual",
        
        
        locator=field.regions[0] if field.regions else None,
        matched_text=value,
        grounded=normalized is not None or not normalizer_name,
        note=note,
    )


def _needs_document_kind(field: FieldSpec) -> bool:
    return field.label_rule is not None or field.extractor == "document_field"


def _standard() -> DocumentKind:
    from substrakt import document_kinds

    return document_kinds.default()


def _from_assignment(
    field: FieldSpec, assignment: labels.Assignment, title: dict[str, str] | None
) -> ExtractionResult:
    if assignment.value is None:
        return ExtractionResult(field=field.name, note=assignment.note)
    result = _build(field, assignment.value, assignment.evidence, "extractor", 0.95)
    if title is not None:
        
        
        result.normalized = title.get(assignment.value.lower())
    if assignment.note:
        result.grounded = False
        result.note = assignment.note
    return result


def extract_field(
    doc: Document,
    field: FieldSpec,
    manual: str | None = None,
    kind: DocumentKind | None = None,
) -> ExtractionResult:
    if manual is not None and manual.strip():
        return _manual(field, manual.strip())

    method = field.method

    
    allow_region = bool(field.regions) and method in ("auto", "region")
    if allow_region and (found := _from_region(doc, field)):
        text, region, quality = found
        evidence = grounding.Evidence(
            locator=region,
            words=windex.words_in_region(doc, region),
            similarity=100.0,
            matched_text=text,
        )
        return _build(field, text, evidence, "region", quality)

    # 2. Regex
    allow_regex = bool(field.regex) and method in ("auto", "regex")
    if allow_regex and (match := _from_regex(doc, field)):
        evidence = grounding.from_position(doc, match.page, match.start, match.end)
        result = _build(field, match.text, evidence, "regex", 0.95)
        if match.multiline:
            
            
            
            result.grounded = False
            result.confidence = 0.0
            result.note = (
                "Pattern spans multiple text lines — review or mark a region"
            )
        return result

    if allow_regex:
        
        
        
        return ExtractionResult(
            field=field.name,
            note="No match for the field pattern — mark a region or enter a value",
        )

    allow_document_kind = method in ("auto", "extractor")

    
    
    if (
        allow_document_kind
        and kind is not None
        and (assignment := kind.read_with_parser(doc, field)) is not None
    ):
        return _from_assignment(field, assignment, None)

    
    if allow_document_kind and _needs_document_kind(field):
        kind = kind if kind is not None else _standard()
        # A generic document-field extractor takes its rule from the kind.
        rule = field.label_rule or kind.rule_for(field.name)
        if rule is None:
            return ExtractionResult(field=field.name, note=labels.Assignment().note)
        context = kind.context()
        assignment = labels.search(doc, field.name, rule, context, field.label)
        return _from_assignment(field, assignment, context.title if rule.value == "title" else None)

    # 5. A built-in extractor returns the normalized value.
    
    
    allow_extractor = method in ("auto", "extractor")
    if allow_extractor and (extractor_match := _from_extractor(doc, field)):
        text, start, end, quality, page = extractor_match
        evidence = grounding.from_position(doc, page, start, end)
        return _build(field, text, evidence, "extractor", quality)

    return ExtractionResult(
        field=field.name,
        note="No value found" + (
            " — mark a region in the document" if not field.regions else ""
        ),
    )


def _build(
    field: FieldSpec,
    text: str,
    evidence: grounding.Evidence | None,
    source: str,
    quality: float,
) -> ExtractionResult:
    """Combine a raw value, evidence and confidence into a result."""
    normalizer_name = field.normalization or normalization.for_type(field.json_type)
    normalized = normalization.apply(normalizer_name, text)

    confidence_value = grounding.confidence(
        evidence,
        value=str(normalized) if normalized is not None else text,
        json_type=field.json_type,
        regions=field.regions,
        extractor_confidence=quality,
    )
    grounded = grounding.is_grounded(confidence_value)

    note = ""
    if not evidence:
        note = "No evidence in the document — value cannot be verified"
    elif not grounded:
        note = "Confidence too low — review required"
    elif normalized is None and normalizer_name:
        note = f"Value does not match type {field.json_type!r}"
    elif (
        (ocr_confidence := evidence.ocr_confidence) is not None
        and ocr_confidence < ocr.THRESHOLD
    ):
        
        
        
        
        
        note = (
            f"Uncertain text recognition ({ocr_confidence:.0%}) — review "
            "or enter the value manually"
        )

    return ExtractionResult(
        field=field.name,
        value=text,
        normalized=normalized if isinstance(normalized, (str, float, bool)) else None,
        confidence=confidence_value,
        source=source,  # type: ignore[arg-type]
        locator=evidence.locator if evidence else None,
        matched_text=evidence.matched_text if evidence else "",
        grounded=grounded,
        note=note,
    )


def extract(
    doc: Document,
    fields: list[FieldSpec],
    manual: dict[str, str] | None = None,
    kind: DocumentKind | None = None,
) -> ExtractionRun:
    start_time = time.perf_counter()
    manual_values = manual or {}
    results = [
        extract_field(doc, field, manual_values.get(field.name), kind) for field in fields
    ]
    return ExtractionRun(
        results=results,
        duration_ms=int((time.perf_counter() - start_time) * 1000),
        ungrounded=sum(1 for e in results if not e.grounded),
    )


# --- Sample fields ---------------------------------------------------------


def __getattr__(name: str) -> list[FieldSpec]:
    if name == "SAMPLE_FIELDS":
        return _standard().fields
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

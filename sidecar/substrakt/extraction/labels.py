"""Find values next to printed labels."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from substrakt.extraction import grounding, normalization
from substrakt.index.words import build_lines
from substrakt.model import Document, ImageRect, PdfRect, Word

BOUNDARY = "<boundary>"

ValueKind = Literal["identifier", "date", "amount", "code", "vat_id", "company", "title"]


class LabelRule(BaseModel):

    model_config = ConfigDict(extra="forbid")

    patterns: list[str] = Field(default_factory=list, description="Label regular expressions")
    value: ValueKind = Field(description="Kind of text accepted as the value")
    values: list[str] = Field(default_factory=list, description="Allowed codes for value: code")
    skip_tax_rate: bool = Field(default=False, description="Skip a tax rate before an amount")
    unlabelled: bool = Field(
        default=False,
        description="Allow one unambiguous code anywhere in the document",
    )
    letterhead_until: list[str] = Field(
        default_factory=list,
        description="Company-name fallback boundaries in the letterhead",
    )

    @model_validator(mode="after")
    def _consistent(self) -> LabelRule:
        for patterns in [*self.patterns, *self.letterhead_until]:
            try:
                re.compile(patterns)
            except re.error as exc:
                raise ValueError(f"Pattern {patterns!r} is not a valid regular expression: {exc}") from None
        if self.value == "code" and not self.values:
            raise ValueError("value: code requires a values list")
        if self.value != "code" and (self.values or self.unlabelled):
            raise ValueError("values and unlabelled apply only to value: code")
        if self.value != "amount" and self.skip_tax_rate:
            raise ValueError("skip_tax_rate applies only to value: amount")
        if self.value != "company" and self.letterhead_until:
            raise ValueError("letterhead_until applies only to value: company")
        if self.value != "title" and not self.patterns and not self.unlabelled:
            raise ValueError("The core cannot find a label without patterns")
        return self


@lru_cache(maxsize=256)
def anchor_pattern(patterns: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile(r"(?<!\w)(?:" + "|".join(patterns) + r")\s*:?(?!\w)", re.I)


@dataclass(frozen=True)
class LabelContext:

    anchors: dict[str, re.Pattern[str]]
    legal_form: re.Pattern[str]
    title: dict[str, str]


def box(word: Word) -> tuple[float, float, float, float]:
    loc = word.locator
    assert isinstance(loc, (ImageRect, PdfRect))
    if isinstance(loc, PdfRect):
        return loc.x0, -loc.y1, loc.x1, -loc.y0
    return loc.x0, loc.y0, loc.x1, loc.y1


@dataclass
class Anchor:
    name: str
    words: list[Word]
    line: int
    start: int
    end: int


@dataclass
class Assignment:
    value: str | None = None
    evidence: grounding.Evidence | None = None
    note: str = "No unambiguous assignment for the field label"


def _evidence(words: list[Word]) -> grounding.Evidence:
    rect = words[0].locator
    for w in words[1:]:
        rect = rect.merged_with(w.locator)
    return grounding.Evidence(locator=rect, words=words, similarity=100,
                               matched_text=" ".join(w.text for w in words))


def _value(rule: LabelRule, context: LabelContext, words: list[Word]) -> tuple[str, list[Word]] | None:
    if not words:
        return None
    if rule.skip_tax_rate:
        for count in (1, 2):
            if re.fullmatch(r"\d+(?:[.,]\d+)?\s*%", " ".join(w.text for w in words[:count])):
                words = words[count:]
                break
        if not words:
            return None
    text = " ".join(w.text for w in words).strip()
    if rule.value == "company":
        return (text, words) if context.legal_form.search(text) else None
    codes = {w.upper() for w in rule.values}
    # Only consume the value, never the rest of its row or the next label.
    for length in range(1, min(4, len(words))+1):
        part = " ".join(w.text for w in words[:length]).strip()
        compact = re.sub(r"\s+", "", part)
        if rule.value == "identifier" and length == 1:
            if re.fullmatch(r"[\w./-]+", part) and re.search(r"\d", part) and normalization.date(part) is None:
                return part, words[:1]
        elif rule.value == "date":
            if normalization.date(part) is not None:
                return part, words[:length]
        elif rule.value == "amount":
            if re.fullmatch(r"[-−–]?[\d.,]+[.,]\d{2}", compact) and normalization.amount(part) is not None:
                return part, words[:length]
        elif (rule.value == "code" and compact.upper() in codes) or (rule.value == "vat_id" and re.fullmatch(r"[A-Z]{2}[A-Z0-9]{8,12}", compact.upper()) and re.search(r"\d", compact)):
            return compact.upper(), words[:length]
    return None


def search(doc: Document, name: str, rule: LabelRule, context: LabelContext,
          label: str = "") -> Assignment:
    patterns = dict(context.anchors)
    if rule.patterns:
        patterns[name] = anchor_pattern(tuple(rule.patterns))
    candidates: list[tuple[str, list[Word], str]] = []
    for page in doc.pages:
        words = [w for w in doc.words_on_page(page.number)
                 if isinstance(w.locator, (ImageRect, PdfRect))]
        lines = build_lines(words, doc.kind == "image")
        anchors = []
        for i, line in enumerate(lines):
            text = " ".join(w.text for w in line)
            spans = []
            pos = 0
            for w in line:
                spans.append((pos, pos+len(w.text), w))
                pos += len(w.text)+1
            for key, pattern in patterns.items():
                for match in pattern.finditer(text):
                    chosen = [w for start, end, w in spans if start < match.end() and end > match.start()]
                    anchors.append(Anchor(key, chosen, i, match.start(), match.end()))
        for anchor in (a for a in anchors if a.name == name):
            left = box(anchor.words[0])[0]
            right = box(anchor.words[-1])[2]
            top = min(box(w)[1] for w in anchor.words)
            bottom = max(box(w)[3] for w in anchor.words)
            height = max(bottom-top, 1)
            center = (top+bottom)/2
            boundary = min((box(a.words[0])[0] for a in anchors
                            if abs(sum(box(a.words[0])[1::2])/2-center) <= height
                            and box(a.words[0])[0] > right), default=page.width)
            # OCR skew can put the value on a different text line. Compare boxes,
            # not line indexes, and keep a sub-line-height tolerance.
            following = sorted([w for w in words if box(w)[0] >= right
                                and box(w)[2] <= boundary
                                and abs((box(w)[1]+box(w)[3])/2-center) <= height*0.85],
                               key=lambda w: box(w)[0])
            found = _value(rule, context, following)
            if found:
                candidates.append((*found, ""))
                continue
            # Prose after a label is not an empty form cell. Do not cross it.
            if following:
                continue
            for j in range(anchor.line+1, len(lines)):
                cell_end = min([boundary]+[box(a.words[0])[0] for a in anchors
                                          if a.line == j and box(a.words[0])[0] > left+height])
                nearby = [w for w in lines[j]
                          if left-height <= box(w)[0] < cell_end and box(w)[1]-bottom <= 2.5*height]
                if not nearby:
                    if min(box(w)[1] for w in lines[j])-bottom > 2.5*height:
                        break
                    continue
                # The first occupied row in the cell must be a value, not another label.
                if any(a.line == j and any(w in nearby for w in a.words) for a in anchors):
                    break
                found = _value(rule, context, nearby) if abs(box(nearby[0])[0]-left) <= 1.5*height else None
                if found:
                    candidates.append((*found, ""))
                break

        if rule.value == "title" and page.number == 0:
            for line in lines:
                for title in context.title:
                    tokens = title.split()
                    # A title is a separate line or precedes a company heading.
                    if ([w.text.lower() for w in line[:len(tokens)]] == tokens
                            and (len(line) == len(tokens) or context.legal_form.search(" ".join(w.text for w in line[len(tokens):])))):
                        candidates.append((" ".join(w.text for w in line[:len(tokens)]), line[:len(tokens)], ""))
        if rule.letterhead_until and not candidates and page.number == 0:
            # Letterhead fallback: only above the first recipient label, never its address.
            until = re.compile("|".join(rule.letterhead_until), re.I)
            recipient_lines = [a.line for a in anchors if a.name == BOUNDARY and until.search(" ".join(w.text for w in a.words))]
            limit = min(recipient_lines, default=0)
            for line in lines[:limit]:
                text = " ".join(w.text for w in line)
                match = context.legal_form.search(text)
                if match:
                    chosen = []
                    length = 0
                    for w in line:
                        if length >= match.end():
                            break
                        chosen.append(w)
                        length += len(w.text)+1
                    if chosen and chosen[0].text.lower() in context.title:
                        chosen = chosen[1:]
                    if chosen:
                        candidates.append((" ".join(w.text for w in chosen), chosen,
                                           f"{label or name} from letterhead — review required"))
    if not candidates and rule.unlabelled:
        # A currency next to an amount need not have its own heading. Accept
        # only one distinct explicitly printed code throughout the document.
        codes = {w.upper() for w in rule.values}
        candidates = [(w.text.upper(), [w], "") for w in doc.words
                      if w.text.upper() in codes
                      and isinstance(w.locator, (ImageRect, PdfRect))]
    if not candidates:
        return Assignment()
    def canonical(value: str):
        if rule.value == "date":
            return normalization.date(value)
        if rule.value == "amount":
            return normalization.amount(value)
        return value
    if len({canonical(c[0]) for c in candidates}) != 1:
        return Assignment(note="Conflicting values at multiple field labels — review required")
    value, chosen, note = candidates[0]
    return Assignment(value, _evidence(chosen), note)

"""Word bounding-box index operations."""

from __future__ import annotations

from substrakt.model import (
    Document,
    ImageRect,
    Locator,
    PdfRect,
    SheetRange,
    TextChunk,
    Word,
)
from substrakt.utils.a1 import a1_in_range


def _rect_overlaps(a: PdfRect | ImageRect, b: PdfRect | ImageRect,
                     minimum_fraction: float) -> bool:
    an, bn = a.normalized(), b.normalized()

    width = min(an.x1, bn.x1) - max(an.x0, bn.x0)
    height = min(an.y1, bn.y1) - max(an.y0, bn.y0)
    if width <= 0 or height <= 0:
        return False

    word_area = (an.x1 - an.x0) * (an.y1 - an.y0)
    if word_area <= 0:
        return False

    return (width * height) / word_area >= minimum_fraction


def words_in_region(
    doc: Document, region: Locator, minimum_fraction: float = 0.4
) -> list[Word]:
    if isinstance(region, SheetRange):
        match = [
            w
            for w in doc.words
            if isinstance(w.locator, SheetRange)
            and w.locator.sheet == region.sheet
            and a1_in_range(w.locator.a1, region.a1)
        ]
        return sorted(match, key=lambda w: _a1_sort_key(w.locator))  # type: ignore[arg-type]

    if isinstance(region, PdfRect):
        match = [
            w
            for w in doc.words
            if isinstance(w.locator, PdfRect)
            and w.locator.page == region.page
            and _rect_overlaps(w.locator, region, minimum_fraction)
        ]
        
        return sorted(match, key=lambda w: (-w.locator.y1, w.locator.x0))  # type: ignore[union-attr]

    if isinstance(region, ImageRect):
        match = [
            w
            for w in doc.words
            if isinstance(w.locator, ImageRect)
            and w.locator.page == region.page
            and _rect_overlaps(w.locator, region, minimum_fraction)
        ]
        
        return sorted(match, key=lambda w: (w.locator.y0, w.locator.x0))  # type: ignore[union-attr]

    return []


def _a1_sort_key(locator: SheetRange) -> tuple[int, int]:
    from substrakt.utils.a1 import a1_to_row_column

    row, column = a1_to_row_column(locator.a1)
    return row, column


def text_from_region(doc: Document, region: Locator, separator: str = " ") -> str:
    return separator.join(w.text for w in words_in_region(doc, region))


def build_lines(words: list[Word], downwards: bool) -> list[list[Word]]:
    rectangles = [w for w in words if not isinstance(w.locator, SheetRange)]
    if not rectangles:
        return []

    def midpoint(w: Word) -> float:
        position = (w.locator.y0 + w.locator.y1) / 2
        return position if downwards else -position

    
    
    heights = [abs(w.locator.y1 - w.locator.y0) for w in rectangles]
    threshold = (sum(heights) / len(heights) / 2) if heights else 6.0

    sorted_words = sorted(rectangles, key=midpoint)
    rows: list[list[Word]] = []
    current: list[Word] = []
    previous: float | None = None

    for word in sorted_words:
        position = midpoint(word)
        if previous is not None and abs(position - previous) > threshold:
            rows.append(sorted(current, key=lambda w: w.locator.x0))
            current = []
        current.append(word)
        previous = position

    if current:
        rows.append(sorted(current, key=lambda w: w.locator.x0))
    return rows


def page_text(doc: Document, page: int) -> str:
    words = doc.words_on_page(page)
    if not words:
        return ""

    if doc.kind == "sheet":
        rows: dict[int, list[tuple[int, str]]] = {}
        for w in words:
            if not isinstance(w.locator, SheetRange):
                continue
            from substrakt.utils.a1 import a1_to_row_column

            row, column = a1_to_row_column(w.locator.a1)
            rows.setdefault(row, []).append((column, w.text))
        return "\n".join(
            "\t".join(text for _, text in sorted(contents))
            for _, contents in sorted(rows.items())
        )

    return "\n".join(
        " ".join(w.text for w in row)
        for row in build_lines(words, doc.kind == "image")
    )


def page_text_with_index(doc: Document, page: int) -> tuple[str, list[tuple[int, int, Word]]]:
    words = doc.words_on_page(page)
    if not words:
        return "", []

    if doc.kind == "sheet":
        from substrakt.utils.a1 import a1_to_row_column

        rows: dict[int, list[tuple[int, Word]]] = {}
        for w in words:
            if not isinstance(w.locator, SheetRange):
                continue
            row, column = a1_to_row_column(w.locator.a1)
            rows.setdefault(row, []).append((column, w))

        parts: list[str] = []
        assignment: list[tuple[int, int, Word]] = []
        position = 0
        for index, (_, contents) in enumerate(sorted(rows.items())):
            if index:
                parts.append("\n")
                position += 1
            for i, (_, word) in enumerate(sorted(contents, key=lambda x: x[0])):
                if i:
                    parts.append("\t")
                    position += 1
                parts.append(word.text)
                assignment.append((position, position + len(word.text), word))
                position += len(word.text)
        return "".join(parts), assignment

    
    
    parts: list[str] = []
    assignment = []
    position = 0

    for line_number, row in enumerate(build_lines(words, doc.kind == "image")):
        if line_number:
            parts.append("\n")
            position += 1
        for i, word in enumerate(row):
            if i:
                parts.append(" ")
                position += 1
            parts.append(word.text)
            assignment.append((position, position + len(word.text), word))
            position += len(word.text)

    return "".join(parts), assignment


def raw_text(doc: Document) -> list[TextChunk]:
    return [
        TextChunk(
            page=p.number,
            text=page_text(doc, p.number),
            sheet_name=p.sheet_name,
        )
        for p in doc.pages
    ]

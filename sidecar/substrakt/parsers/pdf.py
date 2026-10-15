"""PDF parser and coordinate conversion."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pdfplumber
import pypdfium2

from substrakt.errors import (
    DocumentCorrupt,
    DocumentPasswordProtected,
)
from substrakt.model import Document, DocumentMeta, Page, PdfRect, Word
from substrakt.parsers import ocr

log = logging.getLogger(__name__)


# Gescannte PDFs enthalten oft ein paar Zeichen Metadaten-Rauschen, aber keinen


MIN_TEXT_LAYER_CHARACTERS = 20


def _to_pdf_rect(word: dict[str, Any], page: int, width: float, height: float,
                 rotation: int) -> PdfRect:
    x0, x1 = float(word["x0"]), float(word["x1"])
    top, bottom = float(word["top"]), float(word["bottom"])

    if rotation == 90:
        nx0, nx1 = top, bottom
        ny0, ny1 = x0, x1
    elif rotation == 180:
        nx0, nx1 = width - x1, width - x0
        ny0, ny1 = top, bottom
    elif rotation == 270:
        nx0, nx1 = height - bottom, height - top
        ny0, ny1 = width - x1, width - x0
    else:  # 0
        nx0, nx1 = x0, x1
        ny0, ny1 = height - bottom, height - top

    return PdfRect(
        page=page,
        x0=min(nx0, nx1),
        y0=min(ny0, ny1),
        x1=max(nx0, nx1),
        y1=max(ny0, ny1),
    )


def _normalize_rotation(value: Any) -> int:
    """Normalize rotation to 0/90/180/270; PDFs can contain negative values."""
    try:
        rot = int(value or 0) % 360
    except (TypeError, ValueError):
        return 0
    return rot if rot in (0, 90, 180, 270) else 0


def parse(path: Path, doc_id: str, sha256: str, size_bytes: int) -> Document:
    pages: list[Page] = []
    words: list[Word] = []
    warnings: list[str] = []

    try:
        pdf = pdfplumber.open(str(path))
    except Exception as exc:  # pdfminer raises several exception types for malformed files.
        message = str(exc).lower()
        if "password" in message or "encrypt" in message:
            raise DocumentPasswordProtected(
                "The PDF is encrypted and cannot be read without its password."
            ) from exc
        raise DocumentCorrupt(f"PDF could not be opened: {exc}") from exc

    try:
        with pdf:
            for index, page in enumerate(pdf.pages):
                rotation = _normalize_rotation(page.rotation)
                width = float(page.width)
                height = float(page.height)

                try:
                    rohwoerter = page.extract_words(
                        use_text_flow=False,
                        keep_blank_chars=False,
                        extra_attrs=["upright"],
                    )
                except Exception as exc:
                    
                    log.warning("Page %d cannot be read: %s", index, exc)
                    warnings.append(f"Page {index + 1} could not be read.")
                    rohwoerter = []

                character = sum(len(w.get("text", "")) for w in rohwoerter)
                hat_text = character >= MIN_TEXT_LAYER_CHARACTERS

                for w in rohwoerter:
                    text = (w.get("text") or "").strip()
                    if not text:
                        continue
                    words.append(
                        Word(
                            text=text,
                            page=index,
                            locator=_to_pdf_rect(w, index, width, height, rotation),
                            confidence=None,  
                        )
                    )

                pages.append(
                    Page(
                        number=index,
                        width=width,
                        height=height,
                        rotation=rotation,  # type: ignore[arg-type]
                        has_text_layer=hat_text,
                    )
                )
    except (DocumentCorrupt, DocumentPasswordProtected):
        raise
    except Exception as exc:
        raise DocumentCorrupt(f"PDF could not be processed: {exc}") from exc

    if not pages:
        raise DocumentCorrupt("The PDF contains no pages.")

    
    
    
    without_text = [p for p in pages if not p.has_text_layer]
    source = "text_layer" if words else "none"

    if without_text and ocr.available():
        weak_pages: list[int] = []
        recognized_total = 0

        for page in without_text:
            try:
                recognized = ocr.read_pdf_page(path, page.number, page.width, page.height)
            except Exception as exc:
                log.warning("OCR failed on page %d: %s", page.number, exc)
                warnings.append(
                    f"Page {page.number + 1} could not be recognized."
                )
                continue

            words.extend(recognized.words)
            recognized_total += len(recognized.words)
            if recognized.uncertain and recognized.words:
                weak_pages.append(page.number + 1)

        if recognized_total:
            # Mixed documents can combine a text-layer cover letter with scanned pages.
            source = "ocr"
            warnings.append(
                f"OCR ({recognized_total} words) read {len(without_text)} page(s) "
                "without a text layer."
            )
        else:
            warnings.append(
                f"{len(without_text)} of {len(pages)} pages have no text layer, "
                "and text recognition found nothing there."
            )

        if weak_pages:
            warnings.append(
                f"Uncertain text recognition on page {', '.join(map(str, weak_pages))} "
                f"(unter {ocr.THRESHOLD:.0%} word confidence) — review the values."
            )
    elif without_text:
        warnings.append(
            f"{len(without_text)} of {len(pages)} pages have no usable text layer, "
            "and Tesseract is unavailable."
        )

    return Document(
        id=doc_id,
        filename=path.name,
        sha256=sha256,
        kind="pdf",
        pages=pages,
        words=words,
        meta=DocumentMeta(
            size_bytes=size_bytes,
            page_count=len(pages),
            word_count=len(words),
            text_source=source,  # type: ignore[arg-type]
            warnings=warnings,
        ),
    )


def render_page(path: Path, page: int, scale: float = 2.0) -> bytes:
    scale = max(0.1, min(scale, 8.0))
    try:
        doc = pypdfium2.PdfDocument(str(path))
    except Exception as exc:
        raise DocumentCorrupt(f"PDF could not be rendered: {exc}") from exc

    try:
        if page < 0 or page >= len(doc):
            from substrakt.errors import PageNotFound

            raise PageNotFound(f"Page {page} does not exist.", pages=len(doc))
        bitmap = doc[page].render(scale=scale)
        buffer = bitmap.to_pil()
        import io

        output = io.BytesIO()
        buffer.save(output, format="PNG", optimize=False, compress_level=1)
        return output.getvalue()
    finally:
        doc.close()

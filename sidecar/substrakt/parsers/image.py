"""Image and multi-page TIFF parser."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from substrakt.errors import DocumentCorrupt, PageNotFound
from substrakt.model import Document, DocumentMeta, Page, Word
from substrakt.parsers import ocr

log = logging.getLogger(__name__)




Image.MAX_IMAGE_PIXELS = 300_000_000


def _open_raw(path: Path) -> Image.Image:
    try:
        image = Image.open(path)
        image.load()
    except UnidentifiedImageError as exc:
        raise DocumentCorrupt("The image format was not recognized.") from exc
    except Image.DecompressionBombError as exc:
        raise DocumentCorrupt(
            "The image is unusually large and was rejected for safety."
        ) from exc
    except OSError as exc:
        raise DocumentCorrupt(f"Image cannot be read: {exc}") from exc

    return image


def _transpose(image: Image.Image) -> Image.Image:
    transposed = ImageOps.exif_transpose(image)
    return transposed if transposed is not None else image


def parse(path: Path, doc_id: str, sha256: str, size_bytes: int) -> Document:
    image = _open_raw(path)
    warnings: list[str] = []

    pages: list[Page] = []
    page_count = getattr(image, "n_frames", 1)

    try:
        for index in range(page_count):
            if page_count > 1:
                image.seek(index)
            
            
            
            frame = _transpose(image)
            pages.append(
                Page(
                    number=index,
                    width=float(frame.width),
                    height=float(frame.height),
                    rotation=0,  
                    has_text_layer=False,
                )
            )
    except EOFError:
        pass  
    finally:
        image.close()

    if not pages:
        raise DocumentCorrupt("The image contains no usable pages.")

    if page_count > 1:
        warnings.append(f"Image has {len(pages)} pages.")

    
    # Text recognition follows.
    words: list[Word] = []
    source = "none"

    if ocr.available():
        weak_pages: list[int] = []
        for page_number in range(len(pages)):
            try:
                recognized = _recognize_page(path, page_number, len(pages))
            except Exception as exc:
                log.warning("OCR failed on page %d: %s", page_number, exc)
                warnings.append(f"Page {page_number + 1} could not be read.")
                continue

            words.extend(recognized.words)
            if recognized.uncertain and recognized.words:
                weak_pages.append(page_number + 1)

        if words:
            source = "ocr"
        else:
            warnings.append("Text recognition found no text.")

        if weak_pages:
            
            
            warnings.append(
                f"Uncertain text recognition on page {', '.join(map(str, weak_pages))} "
                f"(below {ocr.THRESHOLD:.0%} word confidence) — review the values."
            )
    else:
        warnings.append(
            "Tesseract is unavailable, so no image text is recognized. "
            "Set it up through ./scripts/setup-dev.sh and ./scripts/fetch-models.sh."
        )

    return Document(
        id=doc_id,
        filename=path.name,
        sha256=sha256,
        kind="image",
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


def _recognize_page(path: Path, page_number: int, pages: int) -> ocr.PageText:
    if pages == 1:
        return ocr.read_image(path, 0)

    import tempfile

    image = _open_raw(path)
    try:
        image.seek(page_number)
        frame = _transpose(image)
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / f"frame_{page_number}.png"
            frame.convert("L").save(file)
            return ocr.read_image(file, page_number)
    finally:
        image.close()


def render_page(path: Path, page: int, scale: float = 1.0) -> bytes:
    scale = max(0.05, min(scale, 8.0))
    image = _open_raw(path)

    try:
        if page > 0:
            try:
                image.seek(page)
            except EOFError as exc:
                raise PageNotFound(f"Page {page} does not exist.") from exc

        image = _transpose(image)

        if scale != 1.0:
            neu = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
            image = image.resize(neu, Image.Resampling.LANCZOS)

        
        
        if image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGB")

        output = io.BytesIO()
        image.save(output, format="PNG", optimize=False, compress_level=1)
        return output.getvalue()
    finally:
        image.close()

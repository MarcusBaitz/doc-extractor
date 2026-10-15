"""Local text recognition through Tesseract 5."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageStat

from substrakt.model import ImageRect, PdfRect, Word

log = logging.getLogger(__name__)


DPI = 150




THRESHOLD = 0.85





_TESSDATA = Path(__file__).resolve().parents[3] / "models" / "tessdata"


@dataclass(frozen=True)
class PageText:

    words: list[Word]
    confidence: float
    """Mean word confidence from 0 to 1, used to escalate the reading stage."""

    @property
    def uncertain(self) -> bool:
        return self.confidence < THRESHOLD


def available() -> bool:
    if shutil.which("tesseract") is None:
        return False
    return (_TESSDATA / "deu.traineddata").exists()


def _environment(threads: int) -> dict[str, str]:
    return {
        **os.environ,
        "TESSDATA_PREFIX": str(_TESSDATA),
        
        "OMP_THREAD_LIMIT": str(threads),
    }


def _tsv(image: Path, language: str, threads: int, psm: int = 3) -> list[dict[str, str]]:
    run = subprocess.run(
        ["tesseract", str(image), "stdout", "-l", language, "--psm", str(psm), "tsv"],
        capture_output=True, text=True, env=_environment(threads), timeout=300,
    )
    if run.returncode != 0:
        raise RuntimeError(f"Tesseract: {run.stderr.strip()[:200]}")

    rows = run.stdout.splitlines()
    if not rows:
        return []

    header = rows[0].split("\t")
    entries = []
    for row in rows[1:]:
        fields = row.split("\t")
        if len(fields) == len(header):
            entries.append(dict(zip(header, fields, strict=True)))
    return entries


def read_image(
    image: Path, page: int = 0, language: str = "deu", threads: int = 4
) -> PageText:
    """Recognize an image using pixel coordinates with a top-left origin."""
    words: list[Word] = []
    confidences: list[float] = []

    rows = _tsv(image, language, threads)

    def quality(rows: list[dict[str, str]]) -> tuple[int, float]:
        values = []
        for row in rows:
            try:
                confidence_value = float(row.get("conf", "-1")) / 100
            except ValueError:
                continue
            if row.get("text", "").strip() and confidence_value >= 0:
                values.append(confidence_value)
        return len(values), sum(values)

    count, confidence_sum = quality(rows)
    grayscale = None
    if image.is_file():
        with Image.open(image) as original:
            grayscale = original.convert("L")
    shaded = grayscale is not None and ImageStat.Stat(grayscale).median[0] < 245
    if shaded or count < 40 or (count and confidence_sum / count < THRESHOLD):
        # One bounded retry for sparse or weak page segmentation. No value
        # correction, dictionary guessing or reference data enters this choice.
        try:
            with tempfile.TemporaryDirectory() as directory:
                candidate = image
                if grayscale is not None:
                    # Adaptive local mean threshold suppresses shading and
                    # paper noise. Size and coordinate system remain unchanged.
                    background = grayscale.filter(ImageFilter.GaussianBlur(20)).point(
                        lambda pixel: int(pixel * 0.8)
                    )
                    cleaned = ImageChops.subtract(grayscale, background).point(
                        lambda pixel: 255 if pixel else 0
                    )
                    candidate = Path(directory) / "cleaned.png"
                    cleaned.save(candidate)
                alternative = _tsv(candidate, language, threads, psm=11)
        except (RuntimeError, subprocess.TimeoutExpired):
            alternative = []  # Keep the first successful recognition.
        if quality(alternative)[1] > confidence_sum * 1.05:
            rows = alternative

    for entry in rows:
        text = entry.get("text", "").strip()
        if not text:
            continue
        try:
            confidence_value = float(entry["conf"])
            left, top = int(entry["left"]), int(entry["top"])
            width, height = int(entry["width"]), int(entry["height"])
        except (KeyError, ValueError):
            continue
        if confidence_value < 0:
            continue  

        confidences.append(confidence_value / 100)
        words.append(
            Word(
                text=text,
                page=page,
                locator=ImageRect(
                    page=page, x0=left, y0=top,
                    x1=left + width, y1=top + height,
                ),
                confidence=confidence_value / 100,
            )
        )

    return PageText(
        words=words,
        confidence=sum(confidences) / len(confidences) if confidences else 0.0,
    )


def read_pdf_page(
    pdf: Path,
    page: int,
    width_pt: float,
    height_pt: float,
    language: str = "deu",
    threads: int = 4,
) -> PageText:
    import pypdfium2

    doc = pypdfium2.PdfDocument(str(pdf))
    try:
        bitmap = doc[page].render(scale=DPI / 72)
        pil = bitmap.to_pil()
    finally:
        doc.close()

    with tempfile.TemporaryDirectory() as directory:
        file = Path(directory) / f"page_{page}.png"
        pil.save(file)
        pixel = read_image(file, page, language, threads)

    
    scale_x = width_pt / pil.width if pil.width else 1.0
    scale_y = height_pt / pil.height if pil.height else 1.0

    converted = []
    for word in pixel.words:
        px = word.locator
        assert isinstance(px, ImageRect)
        converted.append(
            Word(
                text=word.text,
                page=page,
                locator=PdfRect(
                    page=page,
                    x0=px.x0 * scale_x,
                    
                    y0=height_pt - px.y1 * scale_y,
                    x1=px.x1 * scale_x,
                    y1=height_pt - px.y0 * scale_y,
                ),
                confidence=word.confidence,
            )
        )

    return PageText(words=converted, confidence=pixel.confidence)

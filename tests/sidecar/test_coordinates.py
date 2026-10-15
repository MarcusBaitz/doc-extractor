"""Tests for coordinates."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pdfplumber
import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from substrakt.model import PdfRect
from substrakt.parsers.pdf import _normalize_rotation, _to_pdf_rect

WIDTH, HEIGHT = float(A4[0]), float(A4[1])   # 595.2756 × 841.8898
ANCHOR_X, ANCHOR_Y = 100.0, 700.0
TOLERANCE = 0.01

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def rotations_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a PDF with the same word at the same position in all four rotations."""
    path = tmp_path_factory.mktemp("koord") / "rotationen.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    for rotation in (0, 90, 180, 270):
        c.setPageRotation(rotation)
        c.setFont("Helvetica", 12)
        c.drawString(ANCHOR_X, ANCHOR_Y, "ANKER")
        c.showPage()
    c.save()
    return path


def test_all_rotations_return_same_rectangle(rotations_pdf: Path) -> None:
    results: list[PdfRect] = []

    with pdfplumber.open(str(rotations_pdf)) as pdf:
        for index, page in enumerate(pdf.pages):
            rotation = _normalize_rotation(page.rotation)
            word = page.extract_words()[0]
            results.append(
                _to_pdf_rect(word, index, float(page.width), float(page.height), rotation)
            )

    assert len(results) == 4, "All four page rotations must be checked"

    reference = results[0]
    for rotation, rect in zip((0, 90, 180, 270), results, strict=True):
        assert rect.x0 == pytest.approx(reference.x0, abs=TOLERANCE), f"x0 at {rotation}°"
        assert rect.y0 == pytest.approx(reference.y0, abs=TOLERANCE), f"y0 at {rotation}°"
        assert rect.x1 == pytest.approx(reference.x1, abs=TOLERANCE), f"x1 at {rotation}°"
        assert rect.y1 == pytest.approx(reference.y1, abs=TOLERANCE), f"y1 at {rotation}°"

    
    
    assert reference.x0 == pytest.approx(ANCHOR_X, abs=1.0)
    assert reference.y0 == pytest.approx(ANCHOR_Y, abs=5.0)
    assert reference.width > 0
    assert reference.height > 0


def test_rectangle_remains_on_page(rotations_pdf: Path) -> None:
    with pdfplumber.open(str(rotations_pdf)) as pdf:
        for index, page in enumerate(pdf.pages):
            rotation = _normalize_rotation(page.rotation)
            word = page.extract_words()[0]
            rect = _to_pdf_rect(word, index, float(page.width), float(page.height), rotation)

            assert 0 <= rect.x0 <= WIDTH, f"x0 outside at {rotation}°: {rect.x0}"
            assert 0 <= rect.x1 <= WIDTH, f"x1 outside at {rotation}°: {rect.x1}"
            assert 0 <= rect.y0 <= HEIGHT, f"y0 outside at {rotation}°: {rect.y0}"
            assert 0 <= rect.y1 <= HEIGHT, f"y1 outside at {rotation}°: {rect.y1}"


def test_normalize_rotation() -> None:
    assert _normalize_rotation(0) == 0
    assert _normalize_rotation(90) == 90
    assert _normalize_rotation(-90) == 270
    assert _normalize_rotation(450) == 90
    assert _normalize_rotation(None) == 0
    assert _normalize_rotation("krumm") == 0
    assert _normalize_rotation(45) == 0, "Non-right-angle rotation maps to 0"


# --- Screen transformation -------------------------------------------------





def doc_to_screen(
    rect: PdfRect, page_height: float, page_width: float,
    scale: float, rotation: int, dpr: float,
) -> tuple[float, float, float, float]:
    """Map PDF points (bottom-left origin) to screen pixels (top-left origin).

    This mirrors ``docToScreen`` in ``src/viewer/coords.ts``.
    """
    if rotation == 90:
        x, y = page_height - rect.y1, rect.x0
        b, h = rect.height, rect.width
    elif rotation == 180:
        x, y = page_width - rect.x1, rect.y0
        b, h = rect.width, rect.height
    elif rotation == 270:
        x, y = rect.y0, page_width - rect.x1
        b, h = rect.height, rect.width
    else:
        x, y = rect.x0, page_height - rect.y1
        b, h = rect.width, rect.height

    f = scale * dpr
    return x * f, y * f, b * f, h * f


def screen_to_doc(
    x: float, y: float, b: float, h: float,
    page_height: float, page_width: float,
    scale: float, rotation: int, dpr: float,
) -> PdfRect:
    f = scale * dpr
    x, y, b, h = x / f, y / f, b / f, h / f

    if rotation == 90:
        
        
        x0, y0 = y, page_height - x - b
        x1, y1 = y + h, page_height - x
    elif rotation == 180:
        x0, y0 = page_width - x - b, y
        x1, y1 = page_width - x, y + h
    elif rotation == 270:
        x0, y0 = page_width - y - h, x
        x1, y1 = page_width - y, x + b
    else:
        x0, y0 = x, page_height - y - h
        x1, y1 = x + b, page_height - y

    return PdfRect(page=0, x0=x0, y0=y0, x1=x1, y1=y1)


@pytest.mark.parametrize("scale", [0.5, 1.0, 2.5, 4.0])
@pytest.mark.parametrize("dpr", [1.0, 2.0])
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_there_and_back_is_identity(scale: float, dpr: float, rotation: int) -> None:
    rng = random.Random(20260727)

    for _ in range(200):
        x0 = rng.uniform(0, WIDTH - 10)
        y0 = rng.uniform(0, HEIGHT - 10)
        rect = PdfRect(
            page=0,
            x0=x0,
            y0=y0,
            x1=x0 + rng.uniform(1, min(200, WIDTH - x0)),
            y1=y0 + rng.uniform(1, min(200, HEIGHT - y0)),
        )

        sx, sy, sb, sh = doc_to_screen(rect, HEIGHT, WIDTH, scale, rotation, dpr)
        round_trip = screen_to_doc(sx, sy, sb, sh, HEIGHT, WIDTH, scale, rotation, dpr)

        assert round_trip.x0 == pytest.approx(rect.x0, abs=TOLERANCE)
        assert round_trip.y0 == pytest.approx(rect.y0, abs=TOLERANCE)
        assert round_trip.x1 == pytest.approx(rect.x1, abs=TOLERANCE)
        assert round_trip.y1 == pytest.approx(rect.y1, abs=TOLERANCE)


def test_fixture_matches_with_typescript_contract() -> None:
    faelle = []
    for rotation in (0, 90, 180, 270):
        for scale in (1.0, 2.5):
            for dpr in (1.0, 2.0):
                rect = PdfRect(page=0, x0=100.0, y0=697.5, x1=141.34, y1=709.52)
                sx, sy, sb, sh = doc_to_screen(rect, HEIGHT, WIDTH, scale, rotation, dpr)
                faelle.append(
                    {
                        "rotation": rotation,
                        "scale": scale,
                        "dpr": dpr,
                        "page": {"width": WIDTH, "height": HEIGHT},
                        "doc": {"x0": rect.x0, "y0": rect.y0, "x1": rect.x1, "y1": rect.y1},
                        "screen": {
                            "x": round(sx, 4),
                            "y": round(sy, 4),
                        "width": round(sb, 4),
                        "height": round(sh, 4),
                        },
                    }
                )

    file = FIXTURES / "coordinates.json"
    if not file.exists():
        FIXTURES.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(faelle, indent=2), encoding="utf-8")
        pytest.skip("Fixture regenerated — rerun the extraction")

    expected = json.loads(file.read_text(encoding="utf-8"))
    assert faelle == expected, (
        "The coordinate transform changed. If intentional, update "
        "src/viewer/coords.ts and regenerate the fixture."
    )

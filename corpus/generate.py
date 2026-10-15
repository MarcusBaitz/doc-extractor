#!/usr/bin/env python3
"""Synthetic corpus of German business documents following DIN 5008.

A fixed seed keeps failures reproducible. Generated files live in
``corpus/out/`` and are deliberately excluded from the repository. The set
includes text-layer and rasterized PDFs, spreadsheets, CSV files, multi-page
TIFF images, and malformed or empty inputs.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

SEED = 20260727
OUTPUT = Path(__file__).parent / "out"
WIDTH, HEIGHT = A4

# Fictional organizations keep realistic-looking test data harmless.
SENDERS = {
    "name": "Nordwind Maschinenbau GmbH",
    "street": "Industriestraße 47",
    "city": "24103 Kiel",
    "vat_id": "DE812345673",
    "tax_number": "20/123/45678",
    "iban": "DE89 3704 0044 0532 0130 00",
    "bic": "COBADEFFXXX",
}

RECIPIENT = {
    "name": "Südwerk Präzisionstechnik AG",
    "street": "Am Grubenrand 12",
    "city": "70565 Stuttgart",
}

ITEMS = [
    (1, "CNC-Frässpindel HSK-A63", "Stück", 2, 8450.00),
    (2, "Kühlmittelpumpe KP-40", "Stück", 1, 1290.50),
    (3, "Linearführung 25 mm, gehärtet", "Meter", 12, 84.25),
    (4, "Wartungspauschale Jahresvertrag", "Pauschal", 1, 2400.00),
]


def format_euro(amount: float) -> str:
    """Format a number using German thousands and decimal separators."""
    return f"{amount:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


# --- PDF -------------------------------------------------------------------


def invoice_pdf(path: Path, *, pages: int = 1) -> None:
    """Create a DIN 5008 invoice with a text layer."""
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("Rechnung 2026-0147")
    c.setAuthor(SENDERS["name"])

    net = sum(quantity * price for _, _, _, quantity, price in ITEMS)
    tax = net * 0.19
    gross = net + tax

    for page_number in range(pages):
        # The sender line is a stable anchor for later template recognition.
        c.setFont("Helvetica-Bold", 13)
        c.drawString(25 * mm, HEIGHT - 25 * mm, SENDERS["name"])
        c.setFont("Helvetica", 8)
        c.drawString(25 * mm, HEIGHT - 30 * mm, f"{SENDERS['street']} · {SENDERS['city']}")

        # DIN 5008 address block.
        c.setFont("Helvetica", 10)
        for i, line in enumerate(
            [RECIPIENT["name"], RECIPIENT["street"], RECIPIENT["city"]]
        ):
            c.drawString(25 * mm, HEIGHT - 50 * mm - i * 5 * mm, line)

        # Information block on the right.
        c.setFont("Helvetica", 9)
        block = [
            ("Rechnungsnummer:", "2026-0147"),
            ("Rechnungsdatum:", "25.07.2026"),
            ("Lieferdatum:", "22.07.2026"),
            ("Kundennummer:", "K-4711"),
            ("USt-IdNr.:", SENDERS["vat_id"]),
        ]
        for i, (description, value) in enumerate(block):
            y = HEIGHT - 50 * mm - i * 5 * mm
            c.drawString(120 * mm, y, description)
            c.drawString(155 * mm, y, value)

        c.setFont("Helvetica-Bold", 12)
        title = "Rechnung" if pages == 1 else f"Rechnung — Seite {page_number + 1}"
        c.drawString(25 * mm, HEIGHT - 90 * mm, title)

        # Line-item table.
        y = HEIGHT - 100 * mm
        c.setFont("Helvetica-Bold", 8)
        for text, x in [
            ("Pos", 25), ("Bezeichnung", 37), ("Einheit", 110),
            ("Menge", 132), ("Einzelpreis", 150), ("Gesamt", 178),
        ]:
            c.drawString(x * mm, y, text)
        c.line(25 * mm, y - 1.5 * mm, 195 * mm, y - 1.5 * mm)

        c.setFont("Helvetica", 8)
        for pos, description, unit, quantity, price in ITEMS:
            y -= 6 * mm
            c.drawString(25 * mm, y, str(pos))
            c.drawString(37 * mm, y, description)
            c.drawString(110 * mm, y, unit)
            c.drawRightString(145 * mm, y, str(quantity))
            c.drawRightString(172 * mm, y, format_euro(price))
            c.drawRightString(195 * mm, y, format_euro(quantity * price))

        # Totals appear only on the last page.
        if page_number == pages - 1:
            y -= 12 * mm
            c.line(130 * mm, y + 4 * mm, 195 * mm, y + 4 * mm)
            for description, value, bold in [
                ("Nettobetrag", net, False),
                ("Umsatzsteuer 19 %", tax, False),
                ("Gesamtbetrag", gross, True),
            ]:
                c.setFont("Helvetica-Bold" if bold else "Helvetica", 9)
                c.drawString(130 * mm, y, description)
                c.drawRightString(195 * mm, y, f"{format_euro(value)} EUR")
                y -= 5 * mm

            y -= 8 * mm
            c.setFont("Helvetica", 8)
            for line in [
                "Zahlungsbedingungen: 14 Tage 2 % Skonto, 30 Tage netto.",
                f"Bankverbindung: IBAN {SENDERS['iban']} · BIC {SENDERS['bic']}",
                f"Steuernummer: {SENDERS['tax_number']}",
            ]:
                c.drawString(25 * mm, y, line)
                y -= 4.5 * mm

        c.setFont("Helvetica", 7)
        c.drawCentredString(
            WIDTH / 2, 15 * mm, f"Seite {page_number + 1} von {pages}"
        )
        c.showPage()

    c.save()


def rotated_pdf(path: Path) -> None:
    """Create a PDF containing all four right-angle page rotations."""
    c = canvas.Canvas(str(path), pagesize=A4)
    for rotation in (0, 90, 180, 270):
        c.setPageRotation(rotation)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 700, "ANKER")
        c.setFont("Helvetica", 9)
        c.drawString(100, 660, f"Seitenrotation {rotation} Grad")
        c.showPage()
    c.save()


# --- Scans -----------------------------------------------------------------


def as_scan(source: Path, target: Path, dpi: int, rng: random.Random) -> None:
    """Rasterize a PDF and add realistic scan defects."""
    import pypdfium2

    doc = pypdfium2.PdfDocument(str(source))
    try:
        image = doc[0].render(scale=dpi / 72).to_pil().convert("L")
    finally:
        doc.close()

    # Real scanner feeds rarely align pages perfectly.
    angle = rng.uniform(-1.4, 1.4)
    image = image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)

    # Sensor noise.
    array = np.asarray(image, dtype=np.int16)
    generator = np.random.default_rng(SEED)
    array = array + generator.normal(0, 7, array.shape).astype(np.int16)

    # Uneven flatbed illumination.
    _height, width = array.shape
    gradient = np.linspace(-9, 9, width, dtype=np.int16)
    array = array + gradient[None, :]

    image = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), mode="L")
    image.save(target, dpi=(dpi, dpi))


# --- Excel -----------------------------------------------------------------


def items_xlsx(path: Path) -> None:
    """Create a workbook with merged cells, multiple sheets and formulas."""
    wb = Workbook()

    ws = wb.active
    ws.title = "Positionen"
    ws.merge_cells("A1:F1")  # Merged cells are a common parser edge case.
    ws["A1"] = f"Rechnung 2026-0147 — {SENDERS['name']}"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.append([])
    ws.append(["Pos", "Bezeichnung", "Einheit", "Menge", "Einzelpreis", "Gesamt"])
    for cell in ws[3]:
        cell.font = Font(bold=True)

    for pos, description, unit, quantity, price in ITEMS:
        line = ws.max_row + 1
        ws.append([pos, description, unit, quantity, price, f"=D{line}*E{line}"])

    total = ws.max_row + 2
    ws.cell(row=total, column=5, value="Nettobetrag").font = Font(bold=True)
    ws.cell(row=total, column=6, value=f"=SUM(F4:F{ws.max_row})")

    terms = wb.create_sheet("Konditionen")
    for line in [
        ["Zahlungsziel", "30 Tage net"],
        ["Skonto", "2 % bei Zahlung binnen 14 Tagen"],
        ["Lieferbedingung", "frei Haus"],
        ["Währung", "EUR"],
        ["Bearbeiter", "Jörg Wüstenberg"],  # Non-ASCII cell contents.
    ]:
        terms.append(line)

    wb.create_sheet("Leer")  # Deliberately empty sheet.

    wb.save(path)


def empty_workbook(path: Path) -> None:
    wb = Workbook()
    wb.active.title = "Ohne Inhalt"
    wb.save(path)


# --- CSV -------------------------------------------------------------------


def items_csv_cp1252(path: Path) -> None:
    """Create a common German CSV: semicolons and CP1252."""
    lines = ["Artikelnummer;Bezeichnung;Menge;Einzelpreis;Währung"]
    for pos, description, _, quantity, price in ITEMS:
        lines.append(f"A-{pos:04d};{description};{quantity};{format_euro(price)};EUR")
    lines.append("A-0005;Ölmessstab für Späneförderer;3;42,90;EUR")
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("cp1252"))


def items_csv_utf8(path: Path) -> None:
    """Create an international CSV: commas and UTF-8."""
    lines = ["article_no,description,quantity,unit_price,currency"]
    for pos, description, _, quantity, price in ITEMS:
        lines.append(f'A-{pos:04d},"{description}",{quantity},{price:.2f},EUR')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Images ---------------------------------------------------------------


def multipage_tiff(path: Path, sources: list[Path]) -> None:
    images = [Image.open(q).convert("L") for q in sources]
    try:
        images[0].save(path, save_all=True, append_images=images[1:], compression="tiff_lzw")
    finally:
        for b in images:
            b.close()


# --- Error cases ----------------------------------------------------------


def corrupt_pdf(path: Path, template: Path) -> None:
    """Truncate a PDF to reproduce a common real-world defect."""
    raw = template.read_bytes()
    path.write_bytes(raw[: len(raw) // 2])


def wrong_extension(path: Path) -> None:
    """Write PNG bytes under a PDF extension to test signature detection."""
    Image.new("RGB", (600, 400), "white").save(path, format="PNG")


def empty_file(path: Path) -> None:
    path.write_bytes(b"")


# --- Main -----------------------------------------------------------------


def main() -> int:
    rng = random.Random(SEED)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    generated: list[tuple[str, str]] = []

    def report(path: Path, description: str) -> None:
        size = path.stat().st_size
        generated.append((path.name, f"{description} · {size / 1024:.0f} KB"))

    print("Generating test corpus …\n")

    invoice = OUTPUT / "rechnung_din5008.pdf"
    invoice_pdf(invoice)
    report(invoice, "invoice with text layer, 1 page")

    multipage = OUTPUT / "rechnung_mehrseitig.pdf"
    invoice_pdf(multipage, pages=3)
    report(multipage, "invoice with text layer, 3 pages")

    rotated = OUTPUT / "rotationen.pdf"
    rotated_pdf(rotated)
    report(rotated, "four page rotations, anchor at (100, 700)")

    scans = []
    for dpi in (150, 300):
        scan = OUTPUT / f"rechnung_scan_{dpi}dpi.png"
        as_scan(invoice, scan, dpi, rng)
        report(scan, f"rasterized at {dpi} dpi with skew and noise")
        scans.append(scan)

    tiff = OUTPUT / "rechnung_mehrseitig.tiff"
    multipage_tiff(tiff, scans)
    report(tiff, "multi-page TIFF")

    xlsx = OUTPUT / "positionen.xlsx"
    items_xlsx(xlsx)
    report(xlsx, "Excel: merged cells, 3 sheets, formulas")

    empty = OUTPUT / "empty_workbook.xlsx"
    empty_workbook(empty)
    report(empty, "empty Excel workbook")

    csv_de = OUTPUT / "artikel_cp1252.csv"
    items_csv_cp1252(csv_de)
    report(csv_de, "CSV: semicolon, CP1252, non-ASCII text")

    csv_int = OUTPUT / "artikel_utf8.csv"
    items_csv_utf8(csv_int)
    report(csv_int, "CSV: comma, UTF-8, quoted text")

    corrupt = OUTPUT / "defekt.pdf"
    corrupt_pdf(corrupt, invoice)
    report(corrupt, "truncated PDF (error case)")

    disguised = OUTPUT / "getarnt.pdf"
    wrong_extension(disguised)
    report(disguised, "PNG with .pdf extension (error case)")

    nothing = OUTPUT / "leer.csv"
    empty_file(nothing)
    report(nothing, "empty file (error case)")

    print(f"{len(generated)} files in {OUTPUT}:\n")
    for name, description in generated:
        print(f"  {name:<32} {description}")

    print(
        "\nNote: this generator does not create password-protected PDFs. "
        "\nThat would add an encryption library used only for test data; a "
        "\nprepared minimal example covers the error path instead."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

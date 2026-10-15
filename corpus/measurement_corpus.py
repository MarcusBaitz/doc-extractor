#!/usr/bin/env python3
"""Generate the synthetic OCR measurement corpus."""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

SEED = 20260728
OUTPUT = Path(__file__).parent / "measurement"
WIDTH, HEIGHT = A4


@dataclass(frozen=True)
class Quality:
    name: str
    dpi: int
    noise: float
    skew: float
    contrast: float  


QUALITIES = [
    Quality("clean", 300, 0.0, 0.0, 1.00),
    Quality("good", 300, 4.0, 0.3, 0.97),
    Quality("medium", 150, 9.0, 1.1, 0.88),
    Quality("poor", 150, 18.0, 2.2, 0.72),
]




# in ein Repository.
DOCUMENTS = [
    ("Nordwind Maschinenbau GmbH", "Industriestraße 47", "24103 Kiel",
     "Rechnung", "2026-0147", "25.07.2026", "DE89 3704 0044 0532 0130 00", "DE812345673"),
    ("Südwerk Präzisionstechnik AG", "Am Grubenrand 12", "70565 Stuttgart",
     "Rechnung", "R-2026-8842", "18.06.2026", "DE79 6005 0101 0002 0345 67", "DE145889474"),
    ("Ostsee Logistik & Spedition e.K.", "Hafenstraße 9a", "18055 Rostock",
     "Lieferschein", "LS-44012", "02.07.2026", "DE59 1305 0000 0201 1234 56", "DE267341908"),
    ("Rheinland Elektrotechnik GmbH", "Kupferweg 3", "50996 Köln",
     "Auftragsbestätigung", "AB-2026-0331", "11.05.2026", "DE15 3705 0198 0001 2345 67", "DE199442670"),
    ("Alpenblick Werkzeugbau OHG", "Talstraße 118", "83022 Rosenheim",
     "Rechnung", "2026/0912", "29.07.2026", "DE72 7115 0000 0000 1234 56", "DE304118825"),
    ("Hansestadt Kunststoffe GmbH", "Speicherring 22", "20457 Hamburg",
     "Gutschrift", "GS-1188", "07.04.2026", "DE34 2005 0550 1234 5678 90", "DE118273647"),
    ("Fränkische Feinmechanik KG", "Mühlgasse 5", "90403 Nürnberg",
     "Rechnung", "FF-2026-0074", "21.03.2026", "DE10 7605 0101 0001 2345 67", "DE256990180"),
    ("Lausitzer Anlagenbau AG", "Werkstraße 200", "03046 Cottbus",
     "Mahnung", "M-2026-0056", "14.07.2026", "DE96 1805 0000 0190 1234 56", "DE331207759"),
    ("Weserbergland Zerspanung GmbH", "Am Steinbruch 61", "31785 Hameln",
     "Rechnung", "2026-WZ-233", "05.06.2026", "DE69 2545 0110 0000 1234 56", "DE402118367"),
    ("Schwarzwald Sensorik GmbH & Co. KG", "Uhrmacherweg 8", "78120 Furtwangen",
     "Auftragsbestätigung", "AB-9921", "30.06.2026", "DE79 6945 0065 0001 2345 67", "DE288104523"),
]

ITEMS = [
    ("CNC-Frässpindel HSK-A63", "Stück", 2, 8450.00),
    ("Kühlmittelpumpe KP-40", "Stück", 1, 1290.50),
    ("Linearführung 25 mm, gehärtet", "Meter", 12, 84.25),
    ("Wartungspauschale Jahresvertrag", "Pauschal", 1, 2400.00),
    ("Späneförderer-Umrüstsatz", "Satz", 3, 612.80),
]


def format_euro(amount: float) -> str:
    return f"{amount:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def document_pdf(path: Path, number: int) -> None:
    sender, street, city, kind, document_number, document_date, iban, vat_id = DOCUMENTS[number]
    items = ITEMS[: 3 + (number % 3)]
    net = sum(m * p for _, _, m, p in items)
    tax = net * 0.19

    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"{kind} {document_number}")

    c.setFont("Helvetica-Bold", 13)
    c.drawString(25 * mm, HEIGHT - 25 * mm, sender)
    c.setFont("Helvetica", 8)
    c.drawString(25 * mm, HEIGHT - 30 * mm, f"{street} · {city}")

    recipient = DOCUMENTS[(number + 3) % len(DOCUMENTS)]
    c.setFont("Helvetica", 10)
    for i, line in enumerate([recipient[0], recipient[1], recipient[2]]):
        c.drawString(25 * mm, HEIGHT - 50 * mm - i * 5 * mm, line)

    c.setFont("Helvetica", 9)
    for i, (description, value) in enumerate(
        [
            ("Belegnummer:", document_number),
            ("Belegdatum:", document_date),
            ("Kundennummer:", f"K-{4700 + number}"),
            ("USt-IdNr.:", vat_id),
        ]
    ):
        y = HEIGHT - 50 * mm - i * 5 * mm
        c.drawString(120 * mm, y, description)
        c.drawString(155 * mm, y, value)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(25 * mm, HEIGHT - 90 * mm, kind)

    y = HEIGHT - 100 * mm
    c.setFont("Helvetica-Bold", 8)
    for text, x in [("Pos", 25), ("Bezeichnung", 37), ("Einheit", 110),
                    ("Menge", 132), ("Einzelpreis", 150), ("Gesamt", 178)]:
        c.drawString(x * mm, y, text)
    c.line(25 * mm, y - 1.5 * mm, 195 * mm, y - 1.5 * mm)

    c.setFont("Helvetica", 8)
    for i, (description, unit, quantity, price) in enumerate(items, start=1):
        y -= 6 * mm
        c.drawString(25 * mm, y, str(i))
        c.drawString(37 * mm, y, description)
        c.drawString(110 * mm, y, unit)
        c.drawRightString(145 * mm, y, str(quantity))
        c.drawRightString(172 * mm, y, format_euro(price))
        c.drawRightString(195 * mm, y, format_euro(quantity * price))

    y -= 12 * mm
    c.line(130 * mm, y + 4 * mm, 195 * mm, y + 4 * mm)
    for description, value, bold in [("Nettobetrag", net, False),
                            ("Umsatzsteuer 19 %", tax, False),
                            ("Gesamtbetrag", net + tax, True)]:
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 9)
        c.drawString(130 * mm, y, description)
        c.drawRightString(195 * mm, y, f"{format_euro(value)} EUR")
        y -= 5 * mm

    y -= 8 * mm
    c.setFont("Helvetica", 8)
    for line in [
        "Zahlungsbedingungen: 14 Tage 2 % Skonto, 30 Tage netto.",
        f"Bankverbindung: IBAN {iban}",
        f"Steuernummer: {20 + number}/123/4567{number}",
    ]:
        c.drawString(25 * mm, y, line)
        y -= 4.5 * mm

    c.showPage()
    c.save()


def rasterize(source: Path, target: Path, q: Quality, rng: random.Random) -> None:
    import pypdfium2

    doc = pypdfium2.PdfDocument(str(source))
    try:
        image = doc[0].render(scale=q.dpi / 72).to_pil().convert("L")
    finally:
        doc.close()

    if q.skew:
        angle = rng.uniform(-q.skew, q.skew)
        image = image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)

    array = np.asarray(image, dtype=np.float32)

    if q.contrast != 1.0:
        
        array = 255 - (255 - array) * q.contrast

    if q.noise:
        generator = np.random.default_rng(SEED + q.dpi)
        array += generator.normal(0, q.noise, array.shape)
        
        gradient = np.linspace(-q.noise, q.noise, array.shape[1], dtype=np.float32)
        array += gradient[None, :]

    Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), mode="L").save(
        target, dpi=(q.dpi, q.dpi)
    )


def ground_truth(path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(str(path)) as pdf:
        return pdf.pages[0].extract_text() or ""


def main() -> int:
    rng = random.Random(SEED)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "scans").mkdir(exist_ok=True)

    directory = []
    print(f"Generating {len(DOCUMENTS)} documents in {len(QUALITIES)} quality levels …\n")

    for number in range(len(DOCUMENTS)):
        pdf = OUTPUT / f"document_{number:02d}.pdf"
        document_pdf(pdf, number)
        reference = ground_truth(pdf)

        (OUTPUT / f"document_{number:02d}.txt").write_text(reference, encoding="utf-8")

        entry = {
            "index": number,
            "pdf": pdf.name,
            "reference": f"document_{number:02d}.txt",
            "characters": len(reference),
            "words": len(reference.split()),
            "scans": {},
        }

        for q in QUALITIES:
            scan = OUTPUT / "scans" / f"document_{number:02d}_{q.name}.png"
            rasterize(pdf, scan, q, rng)
            entry["scans"][q.name] = {
                "file": f"scans/{scan.name}",
                "dpi": q.dpi,
                "kb": scan.stat().st_size // 1024,
            }

        directory.append(entry)
        print(f"  document_{number:02d}  {entry['characters']:>5} characters, "
              f"{entry['words']:>4} words  ·  "
              + "  ".join(f"{q.name} {entry['scans'][q.name]['kb']:>4} KB"
                          for q in QUALITIES))

    (OUTPUT / "directory.json").write_text(
        json.dumps({"seed": SEED, "documents": directory}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    total = sum(e["characters"] for e in directory)
    print(f"\n{len(directory)} documents · {total} ground-truth characters "
          f"· {len(directory) * len(QUALITIES)} scans")
    print(f"Directory: {OUTPUT / 'directory.json'}")
    print("\nNote: these documents are synthetic, so measured accuracy is an")
    print("upper bound; real scans contain more defects.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

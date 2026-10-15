"""Select a parser from file signatures and extensions."""

from __future__ import annotations

from pathlib import Path

from substrakt.errors import FormatNotSupported
from substrakt.model import DocumentFormat

ENDUNGEN: dict[str, DocumentFormat] = {
    ".pdf": "pdf",
    ".xlsx": "sheet",
    ".xlsm": "sheet",
    ".xls": "sheet",
    ".csv": "sheet",
    ".tsv": "sheet",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tif": "image",
    ".tiff": "image",
    ".bmp": "image",
    ".webp": "image",
}


_SIGNATUREN: list[tuple[bytes, DocumentFormat]] = [
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "image"),
    (b"\xff\xd8\xff", "image"),          # JPEG
    (b"II*\x00", "image"),               # TIFF little endian
    (b"MM\x00*", "image"),               # TIFF big endian
    (b"BM", "image"),                    # BMP
    (b"\xd0\xcf\x11\xe0", "sheet"),      # OLE2 — altes .xls
]


def detect_format(path: Path) -> DocumentFormat:
    try:
        with path.open("rb") as f:
            header = f.read(8)
    except OSError:
        header = b""

    for signatur, kind in _SIGNATUREN:
        if header.startswith(signatur):
            return kind

    
    
    extension = path.suffix.lower()
    if extension in ENDUNGEN:
        return ENDUNGEN[extension]

    raise FormatNotSupported(
        f"Extension {extension or '(none)'} is not supported.",
        unterstuetzt=sorted(ENDUNGEN),
    )

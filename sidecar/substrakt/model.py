"""Shared internal document model."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field

# --- Locator ---------------------------------------------------------------


class PdfRect(BaseModel):
    """Rectangle in PDF points, with a bottom-left origin and zero rotation."""

    kind: Literal["pdf_rect"] = "pdf_rect"
    page: int = Field(ge=0)
    x0: float
    y0: float
    x1: float
    y1: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def width(self) -> float:
        return abs(self.x1 - self.x0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def height(self) -> float:
        return abs(self.y1 - self.y0)

    def normalized(self) -> PdfRect:
        return PdfRect(
            page=self.page,
            x0=min(self.x0, self.x1),
            y0=min(self.y0, self.y1),
            x1=max(self.x0, self.x1),
            y1=max(self.y0, self.y1),
        )

    def merged_with(self, other: PdfRect) -> PdfRect:
        if self.page != other.page:
            raise ValueError(f"Rectangles are on different pages: {self.page} and {other.page}")
        a, b = self.normalized(), other.normalized()
        return PdfRect(
            page=a.page,
            x0=min(a.x0, b.x0),
            y0=min(a.y0, b.y0),
            x1=max(a.x1, b.x1),
            y1=max(a.y1, b.y1),
        )


class ImageRect(BaseModel):
    """Rectangle in image pixels with a top-left origin."""

    kind: Literal["image_rect"] = "image_rect"
    page: int = Field(ge=0)
    x0: int
    y0: int
    x1: int
    y1: int

    def normalized(self) -> ImageRect:
        return ImageRect(
            page=self.page,
            x0=min(self.x0, self.x1),
            y0=min(self.y0, self.y1),
            x1=max(self.x0, self.x1),
            y1=max(self.y0, self.y1),
        )

    def merged_with(self, other: ImageRect) -> ImageRect:
        if self.page != other.page:
            raise ValueError(f"Rectangles are on different pages: {self.page} and {other.page}")
        a, b = self.normalized(), other.normalized()
        return ImageRect(
            page=a.page,
            x0=min(a.x0, b.x0),
            y0=min(a.y0, b.y0),
            x1=max(a.x1, b.x1),
            y1=max(a.y1, b.y1),
        )


class SheetRange(BaseModel):

    kind: Literal["sheet_range"] = "sheet_range"
    sheet: str
    a1: str


Locator = Annotated[PdfRect | ImageRect | SheetRange, Field(discriminator="kind")]


# --- Document structure ----------------------------------------------------

DocumentFormat = Literal["pdf", "sheet", "image"]


class Page(BaseModel):

    number: int = Field(ge=0, description="Zero-based index")
    width: float = Field(gt=0, description="PDF points, pixels or sheet columns")
    height: float = Field(gt=0, description="PDF points, pixels or sheet rows")
    rotation: Literal[0, 90, 180, 270] = 0
    sheet_name: str | None = Field(
        default=None, description="Set only for kind='sheet'"
    )
    has_text_layer: bool = Field(
        default=False,
        description="Whether a PDF page contains usable embedded text",
    )


class Word(BaseModel):

    text: str
    page: int = Field(ge=0)
    locator: Locator
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="None for an exact text layer, set for OCR",
    )


class DocumentMeta(BaseModel):

    size_bytes: int = Field(ge=0)
    page_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    
    # Recorded per document.
    text_source: Literal["text_layer", "ocr", "vlm", "cells", "none"] = "none"
    encoding: str | None = None
    delimiter: str | None = None
    producer: str | None = None
    created: str | None = None
    warnings: list[str] = Field(default_factory=list)


class Document(BaseModel):

    id: str
    filename: str
    sha256: str
    kind: DocumentFormat
    pages: list[Page] = Field(default_factory=list)
    words: list[Word] = Field(default_factory=list)
    meta: DocumentMeta

    def words_on_page(self, page: int) -> list[Word]:
        return [w for w in self.words if w.page == page]

    def to_info(self) -> DocumentInfo:
        return DocumentInfo(
            id=self.id,
            filename=self.filename,
            sha256=self.sha256,
            kind=self.kind,
            pages=self.pages,
            meta=self.meta,
        )


class DocumentInfo(BaseModel):

    id: str
    filename: str
    sha256: str
    kind: DocumentFormat
    pages: list[Page] = Field(default_factory=list)
    meta: DocumentMeta


# --- Rohtext ---------------------------------------------------------------


class TextChunk(BaseModel):

    page: int = Field(ge=0)
    text: str
    sheet_name: str | None = None


class DocumentText(BaseModel):
    chunks: list[TextChunk] = Field(default_factory=list)
    text_source: Literal["text_layer", "ocr", "vlm", "cells", "none"] = "none"

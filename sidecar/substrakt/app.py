"""FastAPI application for the sidecar.

The sidecar is unreachable from outside the machine: it binds to ``127.0.0.1``
on a kernel-assigned port and requires a session token known only to the Rust
shell. The frontend never connects directly; every call goes through a Tauri
command in ``src-tauri/src/bridge.rs``.

Handshake:

1. The shell creates a token and starts the process with ``SUBSTRAKT_TOKEN``
   in the environment, not as a process-list argument.
2. The sidecar binds to port 0 and writes one JSON line to **stdout**:
   ``{"port": 45231, "pid": 1234, "version": "0.1.0"}``
3. The shell reads the line and polls ``GET /health`` until connected.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import uvicorn
from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from substrakt import config as cfg
from substrakt import document_kinds
from substrakt.db import models
from substrakt.db.models import DocumentType
from substrakt.errors import (
    DocumentEmpty,
    NotAuthorized,
    PageNotFound,
    SubstraktError,
    UnknownDocument,
)
from substrakt.extraction.fields import ExtractionRun, FieldSpec
from substrakt.extraction.fields import extract as run_extraction
from substrakt.index import words as windex
from substrakt.logging_setup import configure as configure_logging
from substrakt.model import DocumentInfo, DocumentText, Word
from substrakt.store import DocumentStore

log = logging.getLogger(__name__)

CONFIG = cfg.load()
STORE = DocumentStore(CONFIG)
# User-defined document kinds override bundled kinds with the same name.
document_kinds.configure(CONFIG.data_dir / "document_kinds")

_beenden = threading.Event()


# --- Authentication -------------------------------------------------------


async def verify_token(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Compare the bearer token with the configured session token."""
    if CONFIG.development and not CONFIG.token:
        return

    expected = f"Bearer {CONFIG.token}"
    # Constant-time comparison avoids disclosing the token character by character.
    import hmac

    if not authorization or not hmac.compare_digest(authorization, expected):
        raise NotAuthorized("No valid session token was provided.")


Auth = Annotated[None, Depends(verify_token)]


# --- Application ----------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Sidecar ready — version %s, mode %s", cfg.VERSION, CONFIG.mode)
    try:
        log.info("Document kinds: %s", ", ".join(document_kinds.load_all()))
    except SubstraktError as exc:
        # Other parts of the app remain usable. The UI receives the problem
        # response when it first requests the invalid kind.
        log.error("Invalid document kind: %s", exc.detail)
    yield
    STORE.clear()
    log.info("Sidecar stopped")


app = FastAPI(
    title="Substrakt Sidecar",
    version=cfg.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if CONFIG.development else None,
    redoc_url=None,
)


@app.middleware("http")
async def local_only(request: Request, call_next):
    """Reject remote requests as a second line of defence."""
    client = request.client.host if request.client else ""
    if client not in ("127.0.0.1", "::1", "localhost", ""):
        log.warning("Rejected request from a non-local address")
        return JSONResponse(
            status_code=403,
            content={
                "type": "https://substrakt.local/problem/not-local",
                "title": "Only local requests are allowed",
                "status": 403,
                "key": "not-local",
            },
            media_type="application/problem+json",
        )
    return await call_next(request)


@app.exception_handler(SubstraktError)
async def substrakt_error(_: Request, exc: SubstraktError) -> JSONResponse:
    """Return domain errors as RFC 9457 ``problem+json`` responses."""
    if exc.status >= 500:
        log.exception("Internal error: %s", exc.key)
    else:
        log.info("Rejected: %s", exc.key)
    return JSONResponse(
        status_code=exc.status,
        content=exc.as_problem(),
        media_type="application/problem+json",
    )


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    """Log unexpected details locally and return a generic public message."""
    log.exception("Unexpected error")
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://substrakt.local/problem/internal-error",
            "title": "Internal error",
            "status": 500,
            "detail": "An unexpected error occurred. Details are in the local log.",
            "key": "internal-error",
        },
        media_type="application/problem+json",
    )


# --- Response models ------------------------------------------------------


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    mode: cfg.OperatingMode
    documents: int = Field(description="Number of documents loaded in this session")


class LoadRequest(BaseModel):
    path: str = Field(description="Absolute path selected through the shell file dialog")


class WordList(BaseModel):
    page: int
    words: list[Word]


class SheetInfo(BaseModel):
    index: int
    name: str
    rows: int
    columns: int


class SheetRaster(BaseModel):
    index: int
    name: str
    rows: list[list[str]]


# --- Endpoints ------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Handshake target without protected information or token requirement."""
    return HealthResponse(version=cfg.VERSION, mode=CONFIG.mode, documents=len(STORE))


@app.post("/documents", response_model=DocumentInfo)
async def load_document(request_data: LoadRequest, _: Auth) -> DocumentInfo:
    """Load a file and return page metadata without the large word index."""
    return STORE.load(request_data.path).to_info()


@app.get("/documents/{doc_id}", response_model=DocumentInfo)
async def document_info(doc_id: str, _: Auth) -> DocumentInfo:
    return STORE.get(doc_id).to_info()


@app.delete("/documents/{doc_id}")
async def close_document(doc_id: str, _: Auth) -> dict[str, bool]:
    return {"removed": STORE.remove(doc_id)}


@app.get("/documents/{doc_id}/pages/{page}/words", response_model=WordList)
async def page_words(doc_id: str, page: int, _: Auth) -> WordList:
    """Return the word bounding-box index for one page."""
    doc = STORE.get(doc_id)
    if page < 0 or page >= len(doc.pages):
        raise PageNotFound(
            f"Page {page} does not exist.", pages=len(doc.pages)
        )
    return WordList(page=page, words=doc.words_on_page(page))


@app.get("/documents/{doc_id}/file")
async def document_file(doc_id: str, _: Auth) -> Response:
    """Return bytes only for a document already loaded in this session."""
    STORE.get(doc_id)
    path = STORE.path(doc_id)

    return Response(
        content=path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/documents/{doc_id}/text", response_model=DocumentText)
async def document_text(doc_id: str, _: Auth) -> DocumentText:
    """Return plain text with page and cell references."""
    doc = STORE.get(doc_id)
    return DocumentText(chunks=windex.raw_text(doc), text_source=doc.meta.text_source)


@app.get("/documents/{doc_id}/pages/{page}/render")
async def render_page(
    doc_id: str,
    page: int,
    _: Auth,
    scale: Annotated[float, Query(ge=0.1, le=8.0)] = 2.0,
) -> Response:
    """Render one page as PNG for images and viewer fallback cases."""
    doc = STORE.get(doc_id)
    path = STORE.path(doc_id)

    if page < 0 or page >= len(doc.pages):
        raise PageNotFound(
            f"Page {page} does not exist.", pages=len(doc.pages)
        )

    if doc.kind == "pdf":
        from substrakt.parsers.pdf import render_page
    elif doc.kind == "image":
        from substrakt.parsers.image import render_page  # type: ignore[no-redef]
    else:
        raise PageNotFound("Spreadsheets are returned as cell grids, not rendered pages.")

    return Response(
        content=render_page(path, page, scale),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/documents/{doc_id}/sheets", response_model=list[SheetInfo])
async def sheets(doc_id: str, _: Auth) -> list[SheetInfo]:
    """Return spreadsheet sheet names and dimensions."""
    doc = STORE.get(doc_id)
    return [
        SheetInfo(
            index=p.number,
            name=p.sheet_name or f"Sheet {p.number + 1}",
            rows=int(p.height),
            columns=int(p.width),
        )
        for p in doc.pages
    ]


@app.get("/documents/{doc_id}/sheets/{index}/raster", response_model=SheetRaster)
async def sheet_raster(doc_id: str, index: int, _: Auth) -> SheetRaster:
    """Return a sheet's cell grid for the viewer."""
    doc = STORE.get(doc_id)
    if index < 0 or index >= len(doc.pages):
        raise PageNotFound(f"Sheet {index} does not exist.", sheets=len(doc.pages))

    from substrakt.parsers.sheet import read_grid

    return SheetRaster(
        index=index,
        name=doc.pages[index].sheet_name or f"Sheet {index + 1}",
        rows=read_grid(STORE.path(doc_id), index),
    )


class ExtractionRequest(BaseModel):
    """Carry field definitions with the request instead of server-side state."""

    fields: list[FieldSpec]
    # Manually entered or corrected values override the automatic result.
    manual: dict[str, str] = {}


@app.post("/documents/{doc_id}/extract", response_model=ExtractionRun)
async def extract(doc_id: str, request_data: ExtractionRequest, _: Auth) -> ExtractionRun:
    """Extract through region, regex and built-in extractors in that order."""
    doc = STORE.get(doc_id)
    return run_extraction(doc, request_data.fields, request_data.manual)


@app.get("/sample-fields", response_model=list[FieldSpec])
async def sample_fields(_: Auth) -> list[FieldSpec]:
    """Return fields from the default document kind's YAML file."""
    return document_kinds.default().fields


@app.post("/documents/{doc_id}/export")
async def export(doc_id: str, request_data: ExtractionRequest, _: Auth) -> dict:
    """Extract and return values separately from their provenance."""
    doc = STORE.get(doc_id)
    run = run_extraction(doc, request_data.fields, request_data.manual)

    data: dict[str, object] = {}
    provenance: dict[str, object] = {}
    for e in run.results:
        if e.grounded:
            data[e.field] = e.normalized if e.normalized is not None else e.value
        provenance[e.field] = {
            "value": e.value,
            "confidence": e.confidence,
            "source": e.source,
            "grounded": e.grounded,
            "locator": e.locator.model_dump() if e.locator else None,
            "matched_text": e.matched_text,
            "note": e.note,
        }

    return {
        "document": {
            "file_name": doc.filename,
            "sha256": doc.sha256,
            "pages": doc.meta.page_count,
            "kind": doc.kind,
        },
        "data": data,
        "provenance": provenance,
        "run": {
            "duration_ms": run.duration_ms,
            "ungrounded": run.ungrounded,
            "fields": len(run.results),
            "version": cfg.VERSION,
        },
    }


# --- Document types -------------------------------------------------------
#
# A named field set persists builder work across restarts. One connection stays
# open after first use because this sidecar serves exactly one user.

_DB: object | None = None


def _db():
    global _DB
    if _DB is None:
        from substrakt.db import open_database

        _DB = open_database(CONFIG.data_dir / "substrakt.db")
    return _DB


@app.get("/document-types", response_model=list[DocumentType])
async def document_types(_: Auth) -> list[DocumentType]:
    """List stored document types without their fields."""
    return models.list_all(_db())


@app.get("/document-types/{type_id}", response_model=DocumentType)
async def document_type(type_id: int, _: Auth) -> DocumentType:
    loaded = models.load(_db(), type_id)
    if loaded is None:
        raise UnknownDocument("This document type does not exist.")
    return loaded


@app.post("/document-types", response_model=DocumentType)
async def save_document_type(type_: DocumentType, _: Auth) -> DocumentType:
    """Create or replace a document type identified by its name."""
    if not type_.name.strip():
        raise DocumentEmpty("A document type requires a name.")
    return models.save(_db(), type_)


@app.delete("/document-types/{type_id}")
async def delete_document_type(type_id: int, _: Auth) -> dict[str, bool]:
    return {"deleted": models.delete(_db(), type_id)}


@app.post("/shutdown")
async def shutdown(_: Auth) -> dict[str, str]:
    """Shut down cleanly when the shell closes its window."""
    log.info("Shutdown requested")
    _beenden.set()
    return {"status": "stopping"}


# --- Watchdog --------------------------------------------------------------


def _watchdog_stdin() -> None:
    """Stop when the shell disappears and inherited stdin reaches EOF."""
    try:
        while True:
            row = sys.stdin.readline()
            if row == "":
                log.info("Parent process disappeared — stopping sidecar")
                _beenden.set()
                return
    except (OSError, ValueError):
        _beenden.set()


def _watchdog_pid(pid: int) -> None:
    """Fall back to parent-PID polling when stdin is unavailable."""
    while not _beenden.wait(2.0):
        try:
            os.kill(pid, 0)
        except OSError:
            log.info("Parent process %d no longer exists", pid)
            _beenden.set()
            return


def _shutdown_on_signal(server: uvicorn.Server) -> None:
    """Stop the server after the shutdown event is set."""
    _beenden.wait()
    server.should_exit = True


# --- Start -----------------------------------------------------------------


def main() -> None:
    configure_logging(CONFIG.log_dir, CONFIG.development)

    # Bind the socket first so the kernel-assigned port is known before startup.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((CONFIG.bind_host, CONFIG.bind_port))
    except OSError as exc:
        print(json.dumps({"error": f"Cannot bind port: {exc}"}), flush=True)
        raise SystemExit(1) from exc

    port = sock.getsockname()[1]
    sock.listen(64)

    # The handshake is exactly one line; nothing writes to stdout afterwards.
    print(
        json.dumps({"port": port, "pid": os.getpid(), "version": cfg.VERSION}),
        flush=True,
    )
    log.info("Sidecar listening on %s:%d", CONFIG.bind_host, port)

    if not CONFIG.development:
        threading.Thread(target=_watchdog_stdin, daemon=True).start()
        if CONFIG.parent_pid:
            threading.Thread(
                target=_watchdog_pid, args=(CONFIG.parent_pid,), daemon=True
            ).start()

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            log_config=None,
            access_log=False,
            # One worker keeps the in-memory document store coherent.
            workers=1,
        )
    )
    threading.Thread(target=_shutdown_on_signal, args=(server,), daemon=True).start()

    server.run(sockets=[sock])


if __name__ == "__main__":
    main()

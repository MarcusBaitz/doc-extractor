"""In-memory document store for the current session.

Document contents are never persisted. SQLite stores only document types,
field definitions and extraction runs, keeping the local data trail small.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from collections import OrderedDict
from pathlib import Path

from substrakt.config import MAX_FILE_BYTES, Config
from substrakt.errors import (
    FileNotFound,
    FileTooLarge,
    PathNotAllowed,
    UnknownDocument,
)
from substrakt.model import Document
from substrakt.parsers import detect_format

log = logging.getLogger(__name__)

# Evict old entries so a long session cannot consume unbounded memory.
MAX_DOCUMENTS = 24

# One MiB balances hashing throughput and memory use for large files.
_HASH_BLOCK = 1024 * 1024


def file_hash(path: Path) -> str:
    """Calculate SHA-256 without reading the entire file into memory."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(_HASH_BLOCK):
            h.update(block)
    return h.hexdigest()


class DocumentStore:
    """Thread-safe store of loaded documents."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._docs: OrderedDict[str, tuple[Document, Path]] = OrderedDict()
        self._lock = threading.Lock()

    # --- Path validation --------------------------------------------------

    def _validate_path(self, raw: str) -> Path:
        """Resolve a path and enforce the read roots selected by the shell."""
        try:
            path = Path(raw).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise FileNotFound(f"Path cannot be resolved: {raw}") from exc

        if not path.is_file():
            raise FileNotFound(f"{path.name} is not a file.")

        roots = self._config.allowed_roots
        if roots and not any(path.is_relative_to(w) for w in roots):
            # Do not copy a rejected path into logs or public error messages.
            log.warning("Rejected access outside the configured read roots")
            raise PathNotAllowed(
                "The file is outside the directories allowed for this session."
            )

        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise FileTooLarge(
                f"The file is {size / 1024 / 1024:.0f} MB. "
                f"The limit is {MAX_FILE_BYTES / 1024 / 1024:.0f} MB.",
                size=size,
                limit=MAX_FILE_BYTES,
            )

        return path

    # --- Loading ----------------------------------------------------------

    def load(self, raw_path: str) -> Document:
        """Read a file and register it in memory."""
        path = self._validate_path(raw_path)
        kind = detect_format(path)
        sha = file_hash(path)
        size = path.stat().st_size

        # Reuse an identical file to avoid repeatedly parsing large PDFs.
        with self._lock:
            for doc, known_path in self._docs.values():
                if doc.sha256 == sha and known_path == path:
                    self._docs.move_to_end(doc.id)
                    return doc

        doc_id = uuid.uuid4().hex[:16]

        if kind == "pdf":
            from substrakt.parsers import pdf as parser
        elif kind == "sheet":
            from substrakt.parsers import sheet as parser  # type: ignore[no-redef]
        else:
            from substrakt.parsers import image as parser  # type: ignore[no-redef]

        doc = parser.parse(path, doc_id, sha, size)

        with self._lock:
            self._docs[doc.id] = (doc, path)
            while len(self._docs) > MAX_DOCUMENTS:
                evicted, _ = self._docs.popitem(last=False)
                log.debug("Evicted document %s from memory", evicted)

        log.info(
            "Document loaded: kind=%s pages=%d words=%d source=%s",
            doc.kind,
            doc.meta.page_count,
            doc.meta.word_count,
            doc.meta.text_source,
        )
        return doc

    # --- Access -----------------------------------------------------------

    def get(self, doc_id: str) -> Document:
        with self._lock:
            entry = self._docs.get(doc_id)
            if entry is None:
                raise UnknownDocument(
                    "The document is not loaded in this session."
                )
            self._docs.move_to_end(doc_id)
            return entry[0]

    def path(self, doc_id: str) -> Path:
        with self._lock:
            entry = self._docs.get(doc_id)
            if entry is None:
                raise UnknownDocument(
                    "The document is not loaded in this session."
                )
            return entry[1]

    def remove(self, doc_id: str) -> bool:
        with self._lock:
            return self._docs.pop(doc_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._docs.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._docs)

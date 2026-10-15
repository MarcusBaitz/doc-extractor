"""Domain errors returned as RFC 9457 ``application/problem+json``.

The frontend receives a stable key and resolves it to translated interface
text. Stack traces remain in the local log, and messages never quote document
contents so that logs do not become a second data trail.
"""

from __future__ import annotations

from typing import Any

BASE = "https://substrakt.local/problem/"


class SubstraktError(Exception):
    """Base class for errors that may cross the sidecar boundary."""

    key: str = "internal-error"
    status: int = 500
    title: str = "Internal error"

    def __init__(self, detail: str = "", **fields: Any) -> None:
        super().__init__(detail or self.title)
        self.detail = detail
        self.fields = fields

    def as_problem(self) -> dict[str, Any]:
        problem: dict[str, Any] = {
            "type": BASE + self.key,
            "title": self.title,
            "status": self.status,
            "key": self.key,
        }
        if self.detail:
            problem["detail"] = self.detail
        problem.update(self.fields)
        return problem


class FileNotFound(SubstraktError):
    key = "file-not-found"
    status = 404
    title = "File not found"


class FormatNotSupported(SubstraktError):
    key = "format-not-supported"
    status = 415
    title = "File format is not supported"


class FileTooLarge(SubstraktError):
    key = "file-too-large"
    status = 413
    title = "File is too large"


class DocumentCorrupt(SubstraktError):
    key = "document-corrupt"
    status = 422
    title = "Document is corrupt or unreadable"


class DocumentPasswordProtected(SubstraktError):
    key = "document-password-protected"
    status = 422
    title = "Document is password protected"


class DocumentEmpty(SubstraktError):
    key = "document-empty"
    status = 422
    title = "Document contains no usable content"


class UnknownDocument(SubstraktError):
    key = "unknown-document"
    status = 404
    title = "Document is not loaded in this session"


class PageNotFound(SubstraktError):
    key = "page-not-found"
    status = 404
    title = "Page does not exist"


class NotAuthorized(SubstraktError):
    key = "not-authorized"
    status = 401
    title = "Session token is invalid"


class PathNotAllowed(SubstraktError):
    """Reject paths outside the roots granted by the Rust shell."""

    key = "path-not-allowed"
    status = 403
    title = "Access to this path is not allowed"


class EgressDenied(SubstraktError):
    key = "egress-denied"
    status = 403
    title = "Network access is not allowed in the current mode"


class DocumentKindInvalid(SubstraktError):
    """A document-kind YAML file violates the packaged schema."""

    key = "document-kind-invalid"
    status = 500
    title = "Document-kind description is invalid"


class DocumentKindUnknown(SubstraktError):
    key = "document-kind-unknown"
    status = 404
    title = "Document kind is not described"

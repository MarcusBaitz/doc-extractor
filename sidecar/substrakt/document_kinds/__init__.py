"""Document-kind knowledge stored as validated YAML rather than Python code.

Bundled files may be replaced, but not merged, by a same-named file in the
user data directory. A kind may select at most one bundled custom parser.
Model and quantization choices do not belong in document-kind data.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator

from substrakt.errors import DocumentKindInvalid, DocumentKindUnknown
from substrakt.extraction import extractors, normalization
from substrakt.extraction.fields import FieldSpec
from substrakt.extraction.labels import (
    BOUNDARY,
    Assignment,
    LabelContext,
    LabelRule,
    anchor_pattern,
)
from substrakt.model import Document

BUILTIN = Path(__file__).parent
PARSER_PACKAGE = f"{__name__}.parser"
EXTENSION = ".yml"

# Used for fields without an explicitly selected kind until stage 3 recognition.
DEFAULT = "invoice"

_NAME = re.compile(r"^[a-z][a-z0-9_]*$")

# Configured by app.py so implicit default access sees user overrides.
_custom: Path | None = None

Parser = Callable[[Document, FieldSpec, "DocumentKind"], Assignment | None]


class Recognition(BaseModel):
    """Features used to recognize a document of this kind."""

    model_config = ConfigDict(extra="forbid")

    titles: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Canonical value mapped to printed document titles",
    )


class DocumentKind(BaseModel):
    """A complete document-kind definition from YAML."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Must equal the file name without its extension")
    title: str = Field(description="Display name for the interface")
    description: str = ""
    recognition: Recognition = Field(default_factory=Recognition)
    legal_forms: list[str] = Field(
        default_factory=list,
        description="Patterns that identify legal forms in company names",
    )
    boundaries: list[str] = Field(
        default_factory=list,
        description="Labels that end another field's search area",
    )
    fields: list[FieldSpec] = Field(min_length=1)
    parser: str | None = Field(
        default=None,
        description="Bundled module name under substrakt/document_kinds/parser/",
    )

    _context: LabelContext | None = PrivateAttr(default=None)

    @model_validator(mode="before")
    @classmethod
    def _reject_unknown_field_keys(cls, raw: Any) -> Any:
        """Reject field-key typos in human-authored YAML."""
        if isinstance(raw, dict) and isinstance(raw.get("fields"), list):
            allowed = set(FieldSpec.model_fields)
            for index, field in enumerate(raw["fields"]):
                if isinstance(field, dict) and (unknown := sorted(set(field) - allowed)):
                    raise ValueError(
                        f"fields.{index}: unknown keys {', '.join(unknown)}"
                    )
        return raw

    @model_validator(mode="after")
    def _consistent(self) -> DocumentKind:
        if not _NAME.match(self.name):
            raise ValueError(
                f"name {self.name!r}: use lowercase letters, digits and underscores"
            )
        names = [f.name for f in self.fields]
        if duplicates := sorted({n for n in names if names.count(n) > 1}):
            raise ValueError(f"Duplicate field names: {', '.join(duplicates)}")
        for patterns in [*self.legal_forms, *self.boundaries]:
            try:
                re.compile(patterns)
            except re.error as exc:
                raise ValueError(f"Pattern {patterns!r} is not a valid regular expression: {exc}") from None
        for field in self.fields:
            if field.normalization and field.normalization not in normalization.NORMALIZERS:
                raise ValueError(f"{field.name}: unknown normalization {field.normalization!r}")
            if field.extractor and field.extractor not in extractors.EXTRACTORS and field.extractor != "document_field":
                raise ValueError(f"{field.name}: unknown extractor {field.extractor!r}")
            if field.regex:
                try:
                    re.compile(field.regex)
                except re.error as exc:
                    raise ValueError(f"{field.name}: invalid regex: {exc}") from None
            rule = field.label_rule
            if rule and rule.value == "title" and not self.recognition.titles:
                raise ValueError(f"{field.name}: value: title requires recognition.titles")
            if rule and rule.value == "company" and not self.legal_forms:
                raise ValueError(f"{field.name}: value: company requires legal_forms")
        if self.parser is not None:
            # Report a bad parser at load time rather than on the first document.
            _load_parser(self.parser)
        return self

    def rule_for(self, name: str) -> LabelRule | None:
        return next((f.label_rule for f in self.fields if f.name == name), None)

    def context(self) -> LabelContext:
        """Compile labels, legal forms and titles once per file revision."""
        if self._context is None:
            anchors = {
                f.name: anchor_pattern(tuple(f.label_rule.patterns))
                for f in self.fields
                if f.label_rule and f.label_rule.patterns
            }
            if self.boundaries:
                anchors[BOUNDARY] = anchor_pattern(tuple(self.boundaries))
            legal_form = (
                re.compile(r"\b(?:" + "|".join(self.legal_forms) + r")\b", re.I)
                if self.legal_forms
                else re.compile(r"(?!)")
            )
            title = {
                printed.lower(): canonical_value
                for canonical_value, printed_values in self.recognition.titles.items()
                for printed in printed_values
            }
            self._context = LabelContext(anchors=anchors, legal_form=legal_form, title=title)
        return self._context

    def read_with_parser(self, doc: Document, field: FieldSpec) -> Assignment | None:
        """Ask the custom parser; ``None`` delegates back to the core."""
        if self.parser is None:
            return None
        return _load_parser(self.parser)(doc, field, self)


@lru_cache(maxsize=16)
def _load_parser(name: str) -> Parser:
    """Find a bundled parser after validating its import-safe name."""
    if not _NAME.match(name):
        raise ValueError(f"parser {name!r}: use lowercase letters, digits and underscores")
    module_name = f"{PARSER_PACKAGE}.{name}"
    try:
        found = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, ValueError):
        found = None
    if found is None:
        raise ValueError(f"parser {name!r} does not exist under substrakt/document_kinds/parser/")
    module = importlib.import_module(module_name)
    read = getattr(module, "read", None)
    if not callable(read):
        raise ValueError(f"parser {name!r} has no read(doc, field, kind) function")
    return read


# --- Loading --------------------------------------------------------------


def _error_location(error: dict[str, Any]) -> str:
    return ".".join(str(part) for part in error["loc"]) or "(file)"


@lru_cache(maxsize=64)
def _read(path: Path, _revision: tuple[int, int]) -> DocumentKind:
    """Read and validate a file; ``_revision`` invalidates the cache."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise DocumentKindInvalid(
            f"{path.name}: unreadable YAML ({type(exc).__name__})",
            file=path.name,
            error=[{"location": "(file)", "message": str(exc).splitlines()[0] if str(exc) else ""}],
        ) from None
    if not isinstance(raw, dict):
        raise DocumentKindInvalid(
            f"{path.name}: expected a mapping with name, title and fields",
            file=path.name,
            error=[{"location": "(file)", "message": "not a mapping"}],
        )
    try:
        kind = DocumentKind.model_validate(raw)
    except ValidationError as exc:
        error = [
            {"location": _error_location(f), "message": f["msg"].removeprefix("Value error, ")}
            for f in exc.errors(include_input=False, include_url=False)
        ]
        raise DocumentKindInvalid(
            f"{path.name}: " + "; ".join(f"{f['location']}: {f['message']}" for f in error),
            file=path.name,
            error=error,
        ) from None
    if kind.name != path.stem:
        raise DocumentKindInvalid(
            f"{path.name}: name {kind.name!r} must match the file name",
            file=path.name,
            error=[{"location": "name", "message": "does not match the file name"}],
        )
    return kind


def _state(path: Path) -> tuple[int, int]:
    # Size disambiguates file systems with coarse modification timestamps.
    info = path.stat()
    return info.st_mtime_ns, info.st_size


def _files(directory: Path | None) -> dict[str, Path]:
    if directory is None or not directory.is_dir():
        return {}
    return {p.stem: p for p in sorted(directory.glob(f"*{EXTENSION}")) if p.is_file()}


def configure(custom: Path | None) -> None:
    """Set the user override directory during application startup."""
    global _custom
    _custom = custom


def custom_directory() -> Path | None:
    return _custom


def _sources(builtin: Path, custom: Path | None) -> dict[str, Path]:
    sources = _files(builtin)
    sources.update(_files(custom if custom is not None else _custom))
    return sources


def load_all(builtin: Path = BUILTIN, custom: Path | None = None) -> dict[str, DocumentKind]:
    """Load all kinds by name and report any invalid file."""
    return {
        name: _read(path, _state(path))
        for name, path in sorted(_sources(builtin, custom).items())
    }


def load(name: str, builtin: Path = BUILTIN, custom: Path | None = None) -> DocumentKind:
    """Load one kind by name without reading unrelated files."""
    path = _sources(builtin, custom).get(name)
    if path is None:
        raise DocumentKindUnknown(f"No file named {name}{EXTENSION}", kind=name)
    return _read(path, _state(path))


def default() -> DocumentKind:
    return load(DEFAULT)


SCHEMA_FILE = BUILTIN / "document_kind.schema.json"


def schema_text() -> str:
    """Generate the editor schema from the authoritative Pydantic model."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$comment": "Generated from substrakt.document_kinds.DocumentKind with write_schema(); do not edit by hand.",
        **DocumentKind.model_json_schema(),
    }
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def write_schema(target: Path = SCHEMA_FILE) -> None:
    target.write_text(schema_text(), encoding="utf-8")


def schema_is_current(file: Path = SCHEMA_FILE) -> bool:
    return file.is_file() and file.read_text(encoding="utf-8") == schema_text()

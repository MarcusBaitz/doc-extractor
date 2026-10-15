# Sidecar

Status: 2026-10-15

This file applies to changes under `sidecar/` and to contracts that reach
from the Python sidecar into the frontend. It keeps errors, endpoints,
migrations and dependencies together so that no process boundary is changed
only halfway.

## Error contract

Errors leave the sidecar as RFC 9457 `application/problem+json` with a stable
`key`, never as a stack trace. `sidecar/substrakt/errors.py`
defines the domain errors; the stack trace belongs only in the local log,
because technical internals and document contents must not reach the
interface.

The frontend resolves the key through the active dictionary in `src/i18n/`.
A new domain error is therefore complete only when its stable key and the
matching German and English interface texts exist together. The TestClient
case belongs in `tests/sidecar/test_api.py`.

Error messages and logs never quote document contents. File name, hash and
technical details are enough for diagnosis; contents of a document would
otherwise form an unnecessary second data trail through log files.

## No network path of its own

The sidecar talks only to the local process and imports no network library
for outbound traffic. Ruff forbids the runtime imports `requests`,
`urllib.request` and `httpx` under
`[tool.ruff.lint.flake8-tidy-imports.banned-api]`; `scripts/check-egress.sh`
additionally finds imports that slipped past the linter through a comment.

`httpx` is allowed only as a development dependency for the FastAPI
TestClient. A runtime call belongs in the Rust shell's egress chokepoint,
because only there do mode, allowlist and audit log act together.

## Adding an endpoint completely

A new endpoint passes through five places. None of them is generated:

1. The Pydantic model goes into `sidecar/substrakt/model.py` or
   `sidecar/substrakt/db/models.py`, depending on responsibility.
2. The FastAPI endpoint goes into `sidecar/substrakt/app.py` and names its
   `response_model`.
3. The matching TypeScript type is added to `src/api/types.ts` by hand.
   OpenAPI type generation is deliberately still open.
4. `src-tauri/src/bridge.rs` gets the Tauri command, and
   `src-tauri/src/lib.rs` registers it in `invoke_handler`.
5. `src/api/client.ts` wraps the call for the frontend.

This chain keeps port and session token out of the frontend. The egress gate
rejects a supposedly shorter path via `fetch`; API tests and typecheck secure
the contract on both language sides.

## Document kinds

Knowledge about a document kind belongs in its YAML file under
`sidecar/substrakt/document_kinds/`, not in Python. `labels.py` and
`fields.py` work generically with what `DocumentKind` delivers from the file;
`invoice.yml` is the pattern. A new label or document kind is therefore a
file change; the 84-PDF run measures whether recognition changes as a result
(see `docs/document-types.md`, section „Measuring a change“).

A key goes into the Pydantic model `DocumentKind` or `LabelRule` first.
Then `document_kind.schema.json` is regenerated with
`document_kinds.write_schema()`; `tests/sidecar/test_document_kinds.py` rejects
an outdated schema file. If a new key reaches the frontend,
`src/api/types.ts` is updated by hand.

A custom parser is the exception, for when the core is not enough: a module
under `document_kinds/parser/` with `read(doc, field, kind)`, named in the
YAML file with `parser:`. A second parser for the same kind, or a parser that
loads code from the user directory, would destroy the reviewability of the
file. Invalid files end as `document-kind-invalid`; its texts are in both
dictionaries under `src/i18n/`.

## Migrations

Schema changes are not improvised at runtime. They get a new file
`sidecar/substrakt/db/migrations/NNN_name.sql`, a gap-free three-digit number
and a short reason in the header. The pattern is `002_output_format.sql`.

Migrations are meant to be idempotent and run through `PRAGMA user_version`
exactly once, in numerical order and in one transaction. An error must not
leave the database half-migrated. Tests in `tests/sidecar/test_db.py` check
fresh setup, order and repetition.

Exception for the English switch only: by the owner's decision of
15 October 2026, the existing migrations 001 and 002 are rewritten in place
with English names, as if they had been English from the start, and no
renaming migration is added. Substrakt has no released version, so only
development databases are affected; they are deleted and rebuilt. After that
switch the rule above applies again without exception.

SQLite stores types, fields and runs, not loaded document contents. This
boundary comes from `sidecar/substrakt/store.py` and keeps the data trail
small; a migration must not shift it in passing.

## Style and tests

Ruff checks `E`, `F`, `I`, `UP`, `B`, `SIM` and `RUF`. `RUF001` to `RUF003`
are deliberately disabled, because characters such as „…“, dashes and
multiplication signs are correct typography in German interface texts and in
the German sample content of synthetic documents.

Sidecar tests are under `tests/sidecar/`. `test_api.py` shows the pattern for
endpoints with the FastAPI TestClient; `test_fields.py` shows the domain
checks of field definitions. Property-style tests use `random.Random(seed)`,
so that failures stay reproducible and Hypothesis under MPL-2.0 does not open
an additional licence question.

The tests run without manually set `SUBSTRAKT_DEV=1`:
`tests/sidecar/conftest.py` sets the necessary environment at module level,
before `app.py` loads its configuration during collection. A fixture would be
too late at that point.

## Dependencies

Before every new runtime dependency, `licenses/policy.toml` is read and the
licence, including transitive packages, is checked. The licence is written as
a comment next to the entry in `sidecar/pyproject.toml`; the policy and
`docs/decisions.md` are updated with the reason.

The licence gate treats runtime and development differently: whatever ends up
in the bundle must be on the allowlist; development tools are checked against
the denylist. Moving a package between `dependencies` and `dependency-groups`
requires an explicit new assessment.

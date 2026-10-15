# Tests and gates

Status: 2026-10-15

This file applies to every check and to changes of promised properties.
Tests demonstrate behaviour; gates reject forbidden states. Both must be
designed so that a green run actually achieves the claimed property.

## Gate map

| Gate | Enforcement | Rejects |
|---|---|---|
| Egress (ESLint) | `eslint.config.js` | `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `navigator.sendBeacon` and imports of `axios` and `@tauri-apps/plugin-http` in `src/` |
| Egress (Ruff) | `sidecar/pyproject.toml`, section `banned-api` | `requests`, `urllib.request` and `httpx` in the shipped sidecar |
| Egress (grep) | `scripts/check-egress.sh` | network paths that slipped past the language gates through lint comments or new places |
| Colours | `eslint.config.js` | Tailwind default colour names such as `bg-slate-800` in `src/`; components use tokens from `src/design/tokens.css` |
| Words | `tests/frontend/places.test.tsx`, `FORBIDDEN_DE` and `FORBIDDEN_EN` | engine-room terms, German text in English and `snake_case` in the rendered markup of the four places |
| Licences | `scripts/check-licenses.py`, `licenses/policy.toml`, `cargo deny` | runtime dependencies outside the allowlist and packages forbidden by name; development is checked against the denylist |
| Coordinates | shared fixture and tests in Python and TypeScript | divergence of `parsers/pdf.py` and `src/viewer/coords.ts` |
| Rust | CI job `shell` | deviations from `cargo fmt --check` and Clippy warnings through `-D warnings` |
| Evaluation corpus | CI job `evaluation-corpus` | missing LFS objects, changed frozen data or reports, and scoring that no longer reproduces the archived results |

A gate is not a request. Whoever bypasses a rule through a comment, an
alternative API or an untested special path breaks the same product property
the gate is meant to protect.

## Test locations and local commands

- `tests/frontend/` holds Vitest tests for coordinates, image rotation and
  the four places. They run with `npm run test`.
- `tests/sidecar/` holds pytest tests for parsers, API, migrations,
  extractors, normalisation, grounding, OCR, manual values and document kinds.
  They run with `npm run test:sidecar`.
- Rust unit tests live next to the modules under `src-tauri/src/` and run
  with `cd src-tauri && cargo test`.
- `npm run lint` checks the frontend including colour and egress rules; Ruff
  runs in the sidecar CI job.
- `npm run typecheck` checks the hand-maintained TypeScript contract.
- `npm run licenses` and `npm run egress` run the two repository-wide
  promise gates.
- `npm run check` combines typecheck, frontend lint, both test suites,
  licence check and egress check.

As of 15 October 2026, 80 TypeScript, 282 Python and 8 Rust tests are green.
Test counts are orientation, not a target: an additional test counts only if
it demonstrably rejects a relevant failure state.

## CI jobs

**`sidecar`** installs all uv groups and runs Ruff, corpus generation, pytest
and the non-strict benchmark.

**`frontend`** installs with `npm ci` and checks TypeScript, ESLint and Vitest
including the shared coordinate fixture.

**`shell`** installs the Tauri system dependencies and requires rustfmt,
Clippy without warnings and all Rust tests.

**`licenses`** checks Python and npm dependencies, runs `cargo deny` over
licences, bans and sources, and produces the SBOM.

**`egress`** runs the coarse grep gate, which also finds disabled linter
rules and new network places.

**`evaluation-corpus`** checks the LFS objects, the integrity and offline
scoring of `corpus/evaluation/v1`, and the archived reports against their
checksums.

The full air-gap CI test is planned for stage 4 and requires the installer.
Its absence is openly documented until then and is no invitation to treat the
existing egress gates more loosely.

## Three lessons from the stage 1 report

**A green test can secure nothing.** In `docs/status.md`, section “What
the first start revealed”, the path check
test set its own roots while the started process received none. The image
rotation test only checked `rotation: 0`. New tests must therefore run the
production path and the negative variants, not merely a helper function in
the success case.

**Timing measurements are no build gate.** Also in `docs/status.md`: the
benchmark runs after a warm-up; a broken budget only aborts locally with
`--strict`. Shared runners vary too much to turn a timing into a reliable
release gate.

**What is not built locally is hoped for.** Before setup, the Rust part was
the only part not checked locally and held the worst bugs, as
`docs/status.md`, section “What CI revealed”,
records. A sandbox or tool problem is reported, not reinterpreted as green
evidence.

## New safeguards

A new gate gets a negative test: the deliberately forbidden state must make
the gate fail. The existing egress gate was checked with a built-in `fetch`,
the colour gate with a default colour name. Only that proves that not merely
the current, already clean tree is green.

Measurements are filed under `docs/measurements/` as a protocol with
environment, input, procedure and result. An assumption without a measurement
remains an estimate and may justify neither a performance budget nor an
architecture rule as a supposedly proven fact.

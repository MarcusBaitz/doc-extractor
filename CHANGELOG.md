# Changelog

All notable changes to Substrakt are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Substrakt has no
released version yet; the manifests carry `0.1.0` as a placeholder. Until the
first release, changes are grouped by development stage.

## [Unreleased]

### Added

- `LICENSE` (Apache-2.0), `NOTICE`, `SECURITY.md`, `CONTRIBUTING.md`, this
  changelog, `.editorconfig`, and issue and pull request templates.
- Release readiness report in `docs/release-readiness.md`.
- Architecture diagram in `docs/architecture/`, as SVG with a Mermaid source.
- Synthetic evaluation corpus `corpus/evaluation/v1` (84 PDFs, Git LFS) and a
  reproducible comparison with a cloud OCR service on that corpus.
- `npm start` sets up the development environment, fetches models and starts
  the app in one command.
- Document kinds are described in YAML files; the core has no invoice
  knowledge in code.
- English interface, switchable under Settings → Language; German stays the
  default.
- `tests/frontend/places.test.tsx` checks the word list in both languages and
  rejects German copy in the English interface.

### Changed

- Documentation, agent rules, code, database schema, API and error keys,
  scripts, licence policy and CI are English; the interface stays German by
  default.
- Renamed commands and settings: `npm run corpus` (was `korpus`),
  `scripts/start.sh --fresh` (was `--neu`), `SUBSTRAKT_MODE` (was
  `SUBSTRAKT_MODUS`), policy keys `mode` and `inference_server`, and the CI
  job `licenses`.
- granite-docling is downloaded from a pinned Hugging Face revision instead
  of `main`.
- Ambiguous field assignments now require review instead of being accepted
  silently.

### Removed

- `samples/transportschein-aok.pdf`, a scanned official form with fictitious
  data that no code used.

## Design language v2 — 30 July 2026

### Changed

- The interface is organised as four places (Overview, Review, Templates,
  Settings) instead of one workbench; setting up a template is a guided path.
- Colour gate: components use semantic tokens from `src/design/tokens.css`.
- Word gate: technical terms stay out of the four everyday screens.

## Stage 2 — 28 July 2026

### Added

- Normalisers and German extractors for amounts, dates, VAT IDs and IBANs.
- Grounding and confidence for every extracted value.
- Field sets persisted in SQLite.
- Tesseract OCR for pages without a text layer.
- Manual values where no recognition can read the document.

## Stage 1 — 28 July 2026

### Added

- Tauri v2 shell, Python sidecar on `127.0.0.1` with session token and stdin
  watchdog, and the egress chokepoint `Egress::request` with Air-gap as
  default.
- PDF parser and coordinate conversion, checked on both sides against one
  shared fixture.
- Document viewer with overlays.
- Egress, licence, colour and coordinate gates in CI.

### Fixed

- Path checks were ineffective because the started sidecar received no read
  roots; image overlays did not rotate with the page.

## Stage 0 — 28 July 2026

### Added

- Measurements of OCR, a document VLM on CPU, and server throughput,
  recorded under `docs/measurements/`.

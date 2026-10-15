# Product and status

Status: 2026-10-15

This file applies to every change to Substrakt. It places a task within the
product, its promises and its development stages; the source documents are
listed in [`docs/README.md`](../README.md) and are not copied here.

## What Substrakt is

Substrakt is a cross-platform desktop application for intelligent document
extraction. It runs entirely locally and is meant for clerks, not developers.
The target hardware is a standard laptop with 16 GB RAM and no GPU; Windows,
macOS and Linux are supported.

A technical decision that needs a GPU, an external service or developer
knowledge in daily use therefore misses the target profile. This is not an
optimisation for later but the yardstick for every stage.

## The two promises

The binding wording is in [`docs/decisions.md`](../decisions.md):

**1. Nothing leaves the infrastructure.** No document content, no model
call, no telemetry. In case of doubt this promise beats every other
requirement, including convenience and accuracy. If a requirement collides
with it, locality wins, and the conflict is named explicitly instead of being
quietly built around.

**2. Fully permissive licences.** This applies to code *and* model weights
alike. An Apache-2.0 library that loads a CC-BY-NC model is a violation.
Enforced through [`licenses/policy.toml`](../../licenses/policy.toml).

The egress gate in `eslint.config.js`, `sidecar/pyproject.toml` and
`scripts/check-egress.sh` enforces the first promise. The licence gate in
`scripts/check-licenses.py`, `licenses/policy.toml` and `src-tauri/deny.toml`
enforces the second. Both are product properties, not style rules.

## Development stages

| Stage | Content | Status |
|---|---|---|
| 0 | Measurements of OCR, VLM and server throughput | completed 28 July 2026; protocols under `docs/measurements/` |
| 1 | Foundation: parser, coordinates, viewer, sidecar and gates | completed 28 July 2026 |
| 2 | Normalisation, extractors, grounding, confidence, field sets in SQLite, Tesseract OCR and manual values | completed 28 July 2026 |
| — | Design language v2: four places instead of a workbench, colour and word gate | done 30 July 2026 |
| — | Document types as YAML files; the core has no invoice knowledge in code | done 15 October 2026 |
| — | Preparation for public release: licence, project files, English documentation, English code | in progress since 15 October 2026; see `docs/release-readiness.md` |
| 3 | LLM integration with llama.cpp, template recognition and folder watching | open |
| 4 | Export, batch, installer and air-gap CI test | open |

The next product stage is therefore stage 3. A task may implement open points
of that stage if its brief names them; it must not treat their mere absence
as a regression.

## Deliberately open

- `src/api/types.ts` is maintained by hand. Generating it from `openapi.json`
  is still deliberately missing; new contracts must be kept in sync on both
  sides by hand until then.
- The overview says that folders are not watched yet. That is the intended
  interim state until stage 3, not a bug in the interface text.
- An LLM path and automatic template recognition are planned for stage 3.
  There is no LLM client and no watcher yet on which new rules or supposed
  fixes could rely.
- Export, batch, installer and the full air-gap CI test belong to stage 4.
  Existing preparatory tables or endpoints do not change this product status.
- The switch to English is done for code, schema, scripts and
  documentation. German remains where `docs/harness/08-writing.md` keeps it:
  the German interface, synthetic sample content, the frozen evaluation
  corpus and the raw JSON files under `docs/measurements/`.

## Reading the sources

`README.md` is the entry point. `docs/decisions.md` holds the binding
decisions, `docs/design/design-language.md` the visible language, and
`docs/status.md` the lessons from stage 1.

`docs/status.md` is outdated in scope: stage 2, design language v2 and the
document type files are done. Its sections “What CI revealed”, “What the first start
revealed” and “Wrong assumptions” remain valid because they
document measured classes of failure and working rules.

Measurements are under `docs/measurements/`. Figures without a measurement
remain estimates; an estimate does not become a promise by repetition.

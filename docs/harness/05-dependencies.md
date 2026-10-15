# Dependencies and models

Status: 2026-10-15

This file applies to every new Python package, npm package, Rust crate and
model weight. The licence promise covers direct and transitive components; a
technically fitting dependency is unusable without verified distribution
rights.

## Procedure for every addition

1. Read `licenses/policy.toml` first. The file is the single source of truth
   for allowlist, review licences, exceptions and bans by name.
2. Check licence and transitive components from a reliable source. Package
   metadata alone misses bundled binaries and model terms.
3. Decide whether the addition is shipped at runtime or only serves
   development, tests, corpus or build. This boundary determines how strict
   the gate is.
4. Add package, licence and reason to `licenses/policy.toml`. An exception
   also names source and approval; without a reason it is no exception.
5. Write the licence as a comment directly next to the dependency. The pattern
   is in `sidecar/pyproject.toml`; the same traceability applies to
   `package.json` and `src-tauri/Cargo.toml` through their policy references.
6. Update `docs/decisions.md` when the stack, a replacement decision or a
   licence determination changes.
7. Run `npm run licenses`; for Rust additionally
   `cargo deny check licenses bans sources`, or watch the CI job `licenses`.

The licence gate in `scripts/check-licenses.py` checks Python and npm against
`licenses/policy.toml`. `cargo deny` checks crates against
`src-tauri/deny.toml`, whose rules must stay in sync with the central policy.
Runtime dependencies need allowlist approval; development dependencies are at
least checked against the denylist.

## What is not used

The table comes from `README.md`; reasons and replacements are part of the
decision and must not be dropped when proposing an alternative.

| Forbidden | Reason |
|---|---|
| PyMuPDF | AGPL-3.0 |
| OpenCV (PyPI wheels) | bundle FFmpeg under LGPL-2.1 |
| python-Levenshtein, fuzzywuzzy | GPL-2.0, also transitively |
| PyTorch | architecture rule: 1.5 to 4 GB for the framework alone |
| Mistral OCR | proprietary, paid, no open weights |
| RapidOCR | pulls in opencv-python (FFmpeg/LGPL), and measured worse than Tesseract |
| Gemma models, LFM2, CC-BY-NC checkpoints | no OSI licences |

The short version does not replace the policy. It lists further packages by
name, aliases, exceptions and the admissible replacement candidates. A new
package name is also checked transitively, because an allowed direct import
can bring a forbidden component along.

PyTorch stays excluded even with a permissive BSD licence: the ban is an
architecture rule for bundle size and target hardware. OpenCV wheels are
problematic not because of the Python code but because of the bundled FFmpeg.
These differences are why a plain SPDX search is not enough.

## Model weights

A model name is never wired into code. The registry planned for stage 3 makes
models swappable and rejects incomplete entries. Every entry needs:

- repository,
- immutable revision,
- SHA-256 of the weight,
- licence identifier,
- licence URL.

The licence of the runtime code says nothing about the weights. An Apache-2.0
loader with a CC-BY-NC checkpoint breaks the second promise just like a
copyleft library in the bundle.

Models are obtained and checked before shipping, not at runtime.
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` keep libraries offline; the
egress gate additionally guards against own download paths.

`models/` holds local model weights and is not committed.
`scripts/fetch-models.sh` is the intended way to obtain them, with a pinned
revision in every URL (a commit or tag, never `main`) and a SHA-256 per file.
A weight in the repository would be the wrong place both for size and for the
licence record.

Quantisation is a property of the registry entry: GGUF for llama.cpp locally,
compressed-tensors or AWQ on the server. A hard-wired method would prevent
switching models and therefore belongs neither in business logic nor in the
interface.

## Changes to existing versions

An update is a new licence decision as well. For pypdfium2 in particular, the
version-dependent PDFium third-party list must be checked again from the
wheel; for models, licence or terms of use can change between revisions.

Lock files are updated together with the declared version, so that the gate
actually sees the shipped tree. A locally installed but unrecorded version is
no reliable evidence.

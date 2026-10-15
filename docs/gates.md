# Gates

Tests show behaviour; gates reject forbidden states. Each gate protects one of
Substrakt's two promises or a structural rule that keeps them checkable. A
gate is not a request: bypassing it with a lint comment, an alternative API or
an untested special path breaks the same property it protects.

| Gate | Enforced by | Rejects |
|---|---|---|
| Egress (ESLint) | `eslint.config.js` | `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `navigator.sendBeacon`, `axios`, `@tauri-apps/plugin-http` in `src/` |
| Egress (Ruff) | `sidecar/pyproject.toml`, `banned-api` | `requests`, `urllib.request`, `httpx` in the shipped sidecar |
| Egress (grep) | `scripts/check-egress.sh` | network paths that slip past the linters through disabled rules or new places, and `reqwest` outside the shell's three local modules |
| Licences | `scripts/check-licenses.py`, `licenses/policy.toml`, `cargo deny` with `src-tauri/deny.toml` | runtime dependencies outside the allowlist and packages forbidden by name; development tools are checked against the denylist |
| Colours | `eslint.config.js` | Tailwind default colour names such as `bg-slate-800` in `src/` |
| Words | `tests/frontend/places.test.tsx` | language-specific technical terms, German text in English, and `snake_case` keys in the rendered markup of the four places |
| One primary button | `tests/frontend/places.test.tsx` | a second dark (`bg-ink`) button on one screen in either language |
| Coordinates | shared fixture, tests in Python and TypeScript | divergence between `parsers/pdf.py` and `src/viewer/coords.ts` |
| Rust | CI job `shell` | `cargo fmt` differences and any Clippy warning (`-D warnings`) |

## Forbidden by name

| Package | Reason |
|---|---|
| PyMuPDF | AGPL-3.0 |
| OpenCV wheels from PyPI | bundle FFmpeg under LGPL-2.1 |
| python-Levenshtein, fuzzywuzzy | GPL-2.0, also transitively |
| PyTorch | architecture rule: 1.5 to 4 GB for the framework alone, no GPU on the target |
| Mistral OCR | proprietary, paid, no open weights |
| RapidOCR | pulls in opencv-python, and measured worse than Tesseract |
| Gemma models, LFM2, CC-BY-NC checkpoints | no OSI licence |

`licenses/policy.toml` is authoritative and lists further packages, aliases
and approved exceptions.

## CI jobs

| Job | Runs |
|---|---|
| `sidecar` | Ruff, corpus generation, pytest, non-strict benchmark |
| `frontend` | `npm ci`, TypeScript, ESLint, Vitest |
| `shell` | Tauri system packages, rustfmt, Clippy without warnings, Rust tests |
| `licenses` | Python and npm licence check, `cargo deny`, SBOM |
| `egress` | grep gate |
| `evaluation-corpus` | checks that the LFS files of the evaluation corpus are present and intact |

A full air-gap test of the installed application is planned for stage 4,
together with the installer.

## Adding a gate

A new gate comes with a negative test: the deliberately forbidden state must
make it fail. The egress gate was checked with a planted `fetch`, the colour
gate with a default colour name. Otherwise it is only shown that today's tree
is clean.

Timing measurements are not a gate. Shared CI runners vary too much; a broken
budget only fails locally with `npm run bench -- --strict`.

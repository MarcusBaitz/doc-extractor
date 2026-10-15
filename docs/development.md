# Development

## Commands

| Command | What it does |
|---|---|
| `npm start` | set up, fetch models and start (see [Getting started](getting-started.md)) |
| `npm run app` | start the app in development mode |
| `npm run app:wsl` | the same under WSL2 |
| `npm run check` | typecheck, lint, frontend and sidecar tests, licence and egress gates |
| `npm run test` | frontend tests (Vitest) |
| `npm run test:sidecar` | sidecar tests (pytest) |
| `npm run lint` | ESLint, including the colour and egress rules |
| `npm run typecheck` | TypeScript contract |
| `npm run licenses` | licence gate for Python and npm |
| `npm run egress` | grep-based egress gate |
| `npm run corpus` | generate the synthetic test corpus into `corpus/out/` |
| `npm run bench` | measure performance budgets |

Rust checks run in `src-tauri/`:

```bash
export PATH="$HOME/.cargo/bin:$PATH"   # cargo is not on every shell's PATH
cd src-tauri
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
```

## Project layout

```text
src/                    React frontend
  App.tsx               entry point, switches between the four places
  places/               the four places and the template assistant
  viewer/               document viewer, overlays, coords.ts
  api/                  Tauri client and hand-written types
  i18n/                 German and English texts, context and language storage
  design/tokens.css     the only place with colour values
  state/session.ts      session state
  results/save.ts       saving results
  shell/Sidebar.tsx     navigation between places
  ui/components.tsx     shared interface components
src-tauri/src/          Rust shell: lib, sidecar, bridge, egress, policy
sidecar/substrakt/      Python sidecar
  app.py                FastAPI endpoints
  parsers/              PDF, images, spreadsheets, OCR
  extraction/           fields, extractors, normalisation, grounding
  document_kinds/       YAML document kinds, schema and custom parsers
  db/                   SQLite migrations and persisted types
  store.py              loaded documents, in memory only
tests/frontend/         Vitest
tests/sidecar/          pytest and the shared coordinate fixture
corpus/                 synthetic test corpus generators; evaluation corpus v1
bench/                  benchmarks, not shipped
licenses/policy.toml    licence rules, single source of truth
scripts/                setup, model download and gate scripts
docs/                   documentation, decisions, measurements
```

## Adding an endpoint

A new endpoint passes through five places, none of them generated:

1. Pydantic model in `sidecar/substrakt/model.py` or `db/models.py`.
2. FastAPI route in `sidecar/substrakt/app.py` with a `response_model`.
3. The matching TypeScript type in `src/api/types.ts`, by hand.
4. A Tauri command in `src-tauri/src/bridge.rs`, registered in `lib.rs`.
5. A wrapper in `src/api/client.ts`.

A new domain error needs a stable key in `sidecar/substrakt/errors.py` and
matching texts in `src/i18n/de.ts` and `src/i18n/en.ts`.

## Tests

- **Frontend** (`tests/frontend/`): coordinates, image rotation, and the four
  places. Interface tests mock `pdfjs-dist`, because PDF.js needs `DOMMatrix`,
  which Node does not provide.
- **Sidecar** (`tests/sidecar/`): parsers, API, migrations, extractors,
  normalisation, grounding, OCR, manual values. `conftest.py` sets the
  environment at module level, before `app.py` reads its configuration.
  Property-style tests use `random.Random(seed)` so failures are reproducible.
- **Rust**: unit tests next to the modules in `src-tauri/src/`.

A test should run the production path and the relevant failure cases. The
stage 1 report (`docs/status.md`) records why: a green path-check test set its
own read roots while the real process received none.

## Evaluation corpus

`corpus/evaluation/v1` holds 84 synthetic PDFs with ground truth, stored in
Git LFS. It is frozen: no document or expected value is changed after a model
result. See [`corpus/evaluation/README.md`](../corpus/evaluation/README.md).

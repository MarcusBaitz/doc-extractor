# Substrakt

Substrakt is a Tauri v2 desktop application for local document extraction,
built for clerks: React → Rust shell → Python sidecar on `127.0.0.1`. Nothing
leaves the infrastructure; code and model weights are permissively licensed.
The target device is a standard laptop with 16 GB RAM and no GPU.

Stage 2, design language v2 and document kinds as YAML files are done. Stage 3
with LLM integration, template recognition and folder watching is open; the
repository is being switched to English. German remains the default interface
language, with English available in Settings. Details are in
`docs/harness/00-product.md`.

## Commands

```bash
./scripts/setup-dev.sh
npm run app                 # under WSL2: npm run app:wsl
npm run check
npm run test                # TypeScript
npm run test:sidecar        # Python; conftest.py sets SUBSTRAKT_DEV
npm run lint && npm run typecheck
npm run licenses && npm run egress
npm run corpus && npm run bench
export PATH="$HOME/.cargo/bin:$PATH"
cd src-tauri && cargo test  # Rust
cargo fmt --check && cargo clippy --all-targets -- -D warnings
```

## Before you change anything

The egress gate forbids direct network paths in frontend and sidecar. The
colour and word gates protect tokens and the language of the four places. The
licence gate checks shipped dependencies against the allowlist. The shared
coordinate fixture and the Rust CI job protect conversions, formatting and
warning-free shell code. The details are in the required reading.

## Required reading

- `docs/harness/00-product.md`: product, promises and status
- `docs/harness/01-architecture.md`: processes, egress, persistence, map
- `docs/harness/02-sidecar.md`: errors, endpoints and migrations
- `docs/harness/03-frontend.md`: places, words, colours and coordinates
- `docs/harness/04-shell.md`: shell, sidecar life cycle and Rust gates
- `docs/harness/05-dependencies.md`: licences and models
- `docs/harness/06-tests-and-gates.md`: tests, CI and negative checks
- `docs/harness/07-definition-of-done.md`: completion checklist
- `docs/harness/08-writing.md`: language, reasons and comments

## Sandbox

An `EPERM` when opening a port, a read-only `.git`, or a missing `uv` or
`cargo` is a finding for the report, not a reason to restructure code. Checks
outside the sandbox are not claimed green as long as they were not run there.

## Sources

Also authoritative are `README.md`, `docs/decisions.md`,
`docs/design/design-language.md`, `docs/status.md` and the hand-over plans under
`docs/plans/`. If documentation and code disagree, the code wins; then update
the documentation.

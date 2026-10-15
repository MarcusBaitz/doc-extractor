# Substrakt

Substrakt is a cross-platform Tauri v2 desktop application for document
extraction, built for clerks. React calls the Rust shell through Tauri, and the
shell talks to a local Python sidecar on `127.0.0.1`. No document content, no
model call and no telemetry leaves the infrastructure; code and model weights
are fully permissively licensed. The target is a standard laptop with 16 GB
RAM and no GPU.

Stage 2, design language v2 and document kinds as YAML files are done. Stage 3
with LLM integration, template recognition and folder watching is open. The
repository is being prepared for public release and switched to English; the
interface defaults to German and can be switched to English in Settings. The
exact status and deliberately open points are in `docs/harness/00-product.md`.

## Commands

```bash
npm start                   # set up, fetch models and start
./scripts/setup-dev.sh      # set up the development environment
npm run app                 # start the application
npm run app:wsl             # start under WSL2 with four environment switches
npm run check               # all local gates and tests
npm run test                # TypeScript tests (Vitest)
npm run test:sidecar        # Python tests; conftest.py sets SUBSTRAKT_DEV
npm run lint                # ESLint including colour and egress gate
npm run typecheck           # check the TypeScript contract
npm run licenses            # licence gate
npm run egress              # egress gate
npm run corpus              # generate the synthetic test corpus
npm run bench               # measure performance budgets
export PATH="$HOME/.cargo/bin:$PATH"
cd src-tauri
cargo test                  # Rust tests
cargo fmt --check
cargo clippy --all-targets -- -D warnings
```

## Before you change anything

The egress gate rejects direct network paths in frontend and sidecar; rules
and exceptions are in `docs/harness/01-architecture.md`.

The colour and word gates reject unnamed colours and engine-room terms on the
four places; the interface rules are in `docs/harness/03-frontend.md`.

The licence gate rejects unapproved runtime dependencies and packages
forbidden by name; the procedure is in `docs/harness/05-dependencies.md`.

The coordinate fixture and the Rust CI reject diverging conversions,
formatting errors and Clippy warnings; all checks are in
`docs/harness/06-tests-and-gates.md`.

## Rules

The rules live under `docs/harness/` and are loaded here:

@docs/harness/00-product.md
@docs/harness/01-architecture.md
@docs/harness/02-sidecar.md
@docs/harness/03-frontend.md
@docs/harness/04-shell.md
@docs/harness/05-dependencies.md
@docs/harness/06-tests-and-gates.md
@docs/harness/07-definition-of-done.md
@docs/harness/08-writing.md

## Sources

Entry point and structure are in `README.md` and `docs/README.md`, binding
decisions in `docs/decisions.md`, the interface in
`docs/design/design-language.md` and the lessons from stage 1 in
`docs/status.md`. Hand-over plans for Codex are under `docs/plans/`.

If documentation and code disagree, the code wins; then update the
documentation.

# Plan: English shell, scripts, licence policy and CI

> Hand-over from the architect (Claude) to the implementation (Codex). The chat in which this plan was written does not exist for Codex: what is not written here does not exist.

**Stand:** 2026-10-15 · **Branch:** `codex/english-shell` · **Basis:** `designsprache-v2` · **Modell:** `gpt-5.6-sol` · **Aufwand:** high · **Prüfen:** `npm run check && export PATH="$HOME/.cargo/bin:$PATH" && cd src-tauri && cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test` · **Regeln:** `npm run lint && npm run egress` · **Vorbereiten:** `cd sidecar && uv sync --all-groups && cd .. && npm run korpus && mkdir -p models && cp -r /home/marcus/dev/doc-extractor/models/tessdata models/` · **Freigabe:** erteilt am 2026-10-15 · **Umgesetzt:** 2026-10-15

This is plan 2 of 3. It starts after plan 1 (`english-sidecar.md`) is merged; plan 3 (`english-frontend.md`) follows it. The glossary in `english-sidecar.md`, section „Glossary“, applies here unchanged; read it first.

## Ziel

Rename the Rust shell, the scripts, the licence policy, the npm scripts and the CI workflows to English, as if the project had been written in English from the start.

## Kontext

**Why.** `docs/harness/08-writing.md` requires English for identifiers, file names, keys, comments, log messages, script output and CI step names. Plan 1 already renamed the sidecar, the database, the HTTP routes and the Tauri command names (`bridge.rs` command functions and their registration in `lib.rs`). This plan does the rest of the shell and everything around the build.

**Rust shell** (`src-tauri/src/`, about 1,200 lines; `lib.rs`, `sidecar.rs`, `bridge.rs`, `egress.rs`, `policy.rs`, `main.rs`). German identifiers today include: `enum Modus` (`Airgap`, `Onprem`, `Cloud`, `as_str`, `strenge`), `Policy { modus, allowlist, inferenz_server }`, `fn laden`, `fn verengen`, `fn policy_pfade`, `Egress::neu`, `Egress::anfordern`, `Egress::modus`, `protokoll_abholen`, `protokollieren`, `pruefen`, `enum EgressFehler { NichtAufAllowlist, … }`, `struct AuditEintrag`, `SidecarFehler`, `BridgeFehler`, `fn starten`, `beenden`, `startbefehl`, `token_erzeugen`, `lesbare_wurzeln`, `dirs_home`, `warte_auf_health`, `verbindung`, `hole`, `hole_bytes`, `sende`, `auswerten`, `jetzt_iso`, `technisch`, and test names such as `airgap_verweigert_alles`, `onprem_erlaubt_nur_allowlist`, `nutzer_kann_verengen_aber_nicht_erweitern`, `wurzeln_enthalten_das_heimverzeichnis`. Use: `Mode`, `strictness`, `inference_server`, `load`, `narrow`, `policy_paths`, `Egress::new`, `Egress::request`, `Egress::mode`, `take_audit_log`, `log_attempt`, `check`, `EgressError { NotOnAllowlist, … }`, `AuditEntry`, `SidecarError`, `BridgeError`, `start`, `shutdown`, `start_command`, `generate_token`, `read_roots`, `home_dir`, `wait_for_health`, `connection`, `fetch`, `fetch_bytes`, `send`, `evaluate`, `now_iso`, `technical`, and test names that state the property in English (`airgap_refuses_everything`, …). The rule in `docs/harness/04-shell.md` stays: a `MutexGuard` on `state.sidecar` is never held across an HTTP call; keep `connection` copying URL and token and releasing the lock.

**Policy file** (read by `policy.rs`, documented in `docs/configuration.md`): JSON keys `modus→mode`, `inferenz_server→inference_server`; `allowlist` stays; values `airgap`, `onprem`, `cloud` stay. Behaviour stays: missing or broken file means Air-gap.

**Environment variables** passed by `sidecar.rs` and read by `sidecar/substrakt/config.py`: `SUBSTRAKT_MODUS→SUBSTRAKT_MODE`; the others (`SUBSTRAKT_TOKEN`, `SUBSTRAKT_BIND`, `SUBSTRAKT_DATA_DIR`, `SUBSTRAKT_ROOTS`, `SUBSTRAKT_PARENT_PID`, `SUBSTRAKT_MODEL_DIR`, `SUBSTRAKT_LOG_DIR`, `SUBSTRAKT_DEV`) are English already. Change both sides and `tests/sidecar/conftest.py` if it sets the variable.

**Scripts** (`scripts/`): `check_egress.sh`, `check_licenses.py`, `generate_icon.py`, `fetch-models.sh`, `setup-dev.sh`, `dev-wsl.sh`, `start.sh`. Make the names consistent in kebab case: `check-egress.sh`, `check-licenses.py`, `generate-icon.py`; the others keep their names. Translate comments, variable names (`WURZEL`, `ZIEL`, `MODELLE`, `FEHLER`, `GRUEN`, …) and all output. `start.sh`: the flag `--neu` becomes `--fresh`. `fetch-models.sh` keeps its pinned URLs and SHA-256 values byte for byte.

**npm scripts** (`package.json`): `korpus→corpus`; the others are English already. Update the targets of renamed script files.

**Licence policy** (`licenses/policy.toml`, read by `scripts/check-licenses.py`; `src-tauri/deny.toml`): tables `[[ausnahmen]]→[[exceptions]]`, `[[verboten]]→[[forbidden]]`, `[[verboten_modelle]]→[[forbidden_models]]`; keys `paket→package`, `alias→aliases`, `ersatz→replacement`, `freigabe→approval`, `gilt_fuer→applies_to`, `grund→reason`, `lizenz→license`, `muster→pattern`, `quelle→source`, `repo` stays, `spdx` stays; `[allow]`, `[deny]`, `[review]` stay. Translate all comments and reason texts. The checker must read the new keys only. Gate behaviour must not change: same packages allowed, same forbidden.

**CI** (`.github/workflows/ci.yml`, `evaluation-corpus.yml`): job id `lizenzen→licenses`, all `name:` values and comments in English, renamed script paths. Job ids `sidecar`, `frontend`, `shell`, `egress` stay.

**Configuration files with German comments or messages**: `eslint.config.js` (comments and the messages of the egress and colour rules), `vite.config.ts`, `vitest.config.ts`, `index.html` (comments only; the `lang` attribute stays `de`, because the default interface is German), `src-tauri/tauri.conf.json` (no German expected), `src-tauri/Cargo.toml` and `sidecar/pyproject.toml` comments, `.gitignore` and `.gitattributes` comments.

**Gate scripts must keep rejecting.** `docs/harness/06-tests-and-gates.md` requires that a gate fails on the forbidden state. After renaming `check-egress.sh` and `check-licenses.py`, show it once by hand: plant a `fetch(` in a scratch copy of a file under `src/`, and a forbidden package name in a scratch copy of the checker's input, run the gate, see it fail, remove the plant. Report the two runs; do not commit the plants.

## Schritte

1. **Rust.** Rename identifiers, enum variants, error types, functions and tests in `src-tauri/src/*.rs`; translate comments and log messages; policy JSON keys and `SUBSTRAKT_MODE` (also in `sidecar/substrakt/config.py`). Expected: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` and `cargo test` green, all 8 tests still present under English names.
2. **Licence policy and checker.** Rename tables and keys in `licenses/policy.toml`, translate it and `src-tauri/deny.toml` comments, rename `scripts/check_licenses.py` to `scripts/check-licenses.py` and translate it. Expected: `npm run licenses` green with the same package counts as before; negative run as described above.
3. **Other scripts and npm.** Rename `check_egress.sh` and `generate_icon.py`, translate all scripts and their output, `--neu→--fresh`, `npm run corpus`. Expected: `npm run egress` green plus its negative run; `bash -n` on every shell script; `npm start -- --help` is not required.
4. **CI and configuration files.** `ci.yml`, `evaluation-corpus.yml`, `eslint.config.js`, `vite.config.ts`, `vitest.config.ts`, `index.html`, manifest and ignore-file comments. Expected: `npm run lint` and `npm run typecheck` green; the YAML parses.
5. **Documentation.** Update every file that names a changed identifier, key, variable, script or job: `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `AGENTS.md`, `docs/getting-started.md`, `docs/configuration.md` (policy keys, `SUBSTRAKT_MODE`, `policy::narrow`), `docs/development.md`, `docs/gates.md`, `docs/architecture/README.md`, `docs/architecture/architecture.mmd` and `architecture.svg` (only the text `Egress::anfordern` becomes `Egress::request`; nothing else in the drawing changes), `docs/harness/*.md`, `.github/pull_request_template.md`, `SECURITY.md`, `NOTICE`. Expected: `grep -rn "anfordern\|verengen\|SUBSTRAKT_MODUS\|inferenz_server\|check_egress\|check_licenses\|npm run korpus\|--neu\|lizenzen" -- README.md CONTRIBUTING.md CLAUDE.md AGENTS.md SECURITY.md NOTICE docs/*.md docs/harness docs/architecture .github` finds nothing.

## Nicht anfassen

- Everything plan 1 already did: sidecar modules, database, routes, Tauri command names, error keys.
- `src/`: the frontend is plan 3. `eslint.config.js` is in scope only for comments and rule messages; its rules stay identical.
- `corpus/evaluation/**`, `docs/entscheidungen.md`, `docs/stand.md`, `docs/design/**`, `docs/messungen/**`, `docs/plans/**`, `docs/release-readiness.md`, `CHANGELOG.md`.
- URLs and SHA-256 values in `scripts/fetch-models.sh`; `LICENSE`.
- No new dependency. No change of behaviour or defaults: Air-gap stays the default, a broken policy still means Air-gap, the egress and licence gates allow and reject exactly what they did before.
- The writing rules in `docs/harness/08-writing.md`. No adaptation of code to the sandbox: an `EPERM`, a read-only `.git` or a missing `uv`/`cargo` is a finding, not a reason to change code.
- Renaming an identifier is not a search-and-replace of a word. In plan 1 a blind replacement turned German interface texts into „So sieht das ExtractionResult aus“. Never replace a word inside a string or comment because an identifier of that name was renamed; translate prose as prose.
- Do not write into „Befunde der Abnahme“.

## Fertig, wenn

The **Prüfen** command is green, both negative gate runs are reported, and `git grep -nIiE "\b(nicht|und|oder|wenn|fehler|starten|laden|pruefen|wurzel|einrichten|vorhanden|abhängigkeit)\b" -- src-tauri/src scripts licenses .github eslint.config.js vite.config.ts vitest.config.ts` finds nothing.

## Befunde der Abnahme

Reviewed by the architect on 2026-10-15.

1. **Codex reported the run as not fully green, correctly.** `test_api.py` hangs in Starlette's `TestClient` inside the Codex sandbox, so the Prüfen command could not finish there. That is a sandbox finding; outside the sandbox the suite runs. Decision: no code change.
2. **A leftover of plan 1 broke `tests/sidecar/test_parser.py`.** Plan 1 renamed the generator output to `empty_workbook.xlsx`, but the test still loaded `leere_mappe.xlsx`. The review of plan 1 missed it because its worktree still held the file from the old generator. Decision: the architect changed the test to the new name in this branch.
3. **Gates reject exactly what they rejected before.** `licenses/policy.toml` compared structurally with the base: `allow`, `deny` patterns, `review`, all 8 forbidden models and every package name, alias and `applies_to` in `forbidden` and `exceptions` are unchanged; only prose and the `applies_to` value `laufzeit → runtime` (read the same way by the checker) changed. Exceptions are matched by package name only, so the translated free-text licence of `reportlab` has no effect. Both checkers report 58 Python and 194 npm packages and the same seven development-only notes. `eslint.config.js` differs only in rule messages; the patterns of `check-egress.sh` are unchanged.
4. **Negative runs** reported by Codex: a planted `fetch(` and a planted forbidden runtime package each ended with exit 1; both plants were removed, which the architect confirmed.
5. **Defaults:** a missing `mode` still falls back to `Mode::AirGap`, `SUBSTRAKT_MODE` defaults to `airgap` in `config.py` and `conftest.py`. `scripts/fetch-models.sh` URLs and SHA-256 values are unchanged.
6. **`docs/release-readiness.md`** still names the CI job `lizenzen` twice; the file was out of scope. Decision: the architect updates it after the merge.

Runs by the architect in the worktree: `npm run check` green (71 TypeScript tests; 280 Python tests passed, 2 skipped because the fresh corpus has no transport form; licence and egress gates green), `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` and `cargo test` green (8 tests).

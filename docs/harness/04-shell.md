# Rust shell

Status: 2026-10-15

This file applies to changes under `src-tauri/`. The shell owns the
product's process and network boundaries; its rules therefore protect not
only Rust code but the locality promise of the whole application.

## Responsibility of the files

- `src-tauri/src/lib.rs` starts the application, holds the shared state, sets
  up plugins and registers the Tauri commands.
- `src-tauri/src/sidecar.rs` starts the sidecar, passes session token and
  read roots, checks the handshake and keeps the stdin watchdog open.
- `src-tauri/src/bridge.rs` provides the commands and forwards calls with the
  bearer token to the local sidecar.
- `src-tauri/src/egress.rs` is the only chokepoint for outbound traffic and
  logs allowed as well as refused attempts.
- `src-tauri/src/policy.rs` loads the machine-wide policy and falls back to
  Air-gap on errors.

`main.rs` stays the narrow binary entry point. Moving responsibility from the
five modules there would make the checked boundaries invisible.

## Network boundary

`Egress::request` in `egress.rs` is the only place that may release an
outbound target. A second HTTP client for external targets, a Tauri HTTP
plugin or a direct call from frontend or sidecar is a breach, because it would
bypass mode, allowlist and audit log.

The `reqwest::Client` in `lib.rs`, `bridge.rs` and `sidecar.rs` serves the
local connection to `127.0.0.1`; proxy detection is explicitly off, so that
not even this connection runs through a foreign machine. The grep gate in
`scripts/check-egress.sh` rejects `reqwest` in other Rust places and thereby
protects the intended topology.

## Sidecar life cycle and read roots

`sidecar.rs` sets `SUBSTRAKT_ROOTS`. Without this variable the sidecar checks
no path; an empty list would therefore be a sham protection layer. The roots
must not open system directories such as `/etc`, `/tmp` or `/`.

The existing Rust test requires a non-empty list, the home directory and the
exclusion of system directories. Changes to mount paths or platform logic
must extend this test, because the first green path check had only secured
an isolated function and not the started process.

Tokens are passed through the environment instead of process arguments. The
sidecar binds to `127.0.0.1:0`, reports the kernel-assigned port in the
handshake and exits through the open stdin watchdog when the shell dies.
These properties prevent readable tokens, port collisions and orphaned
processes.

## Concurrency

A `MutexGuard` on `state.sidecar` is never held across an HTTP call.
`bridge.rs::connection` copies base URL and token and releases the lock
immediately. Otherwise a render call with a long timeout would also block the
concurrent loading of words and text.

This rule comes from `docs/status.md`, section “What CI revealed”
(what CI revealed): the code compiled despite the unnecessary serialisation.
Clippy is no gate for runtime behaviour here; review and a suitable
concurrency test must secure the lifetime of the guard.

## Build, logging and resources

Before every commit, at least `cargo fmt --check`,
`cargo clippy --all-targets -- -D warnings` and `cargo test` run in
`src-tauri/`. The CI job `shell` rejects formatting differences and every
Clippy warning as an error.

Logging runs through `tauri-plugin-log`, locally and rotating. Document
contents do not belong in the log; hashes, field names and metrics suffice
for diagnosis and avoid a second data trail.

Every file referenced in `src-tauri/tauri.conf.json` must exist in the
repository or in the intended build step. `tauri::generate_context!()`
evaluates the configuration at compile time; a missing resource therefore
makes Clippy fail on the macro even if the Rust code is correct.

After setup, Cargo lives in `~/.cargo/bin` and is not on every shell's
`PATH`. Before diagnosing a missing tool, run
`export PATH="$HOME/.cargo/bin:$PATH"`.

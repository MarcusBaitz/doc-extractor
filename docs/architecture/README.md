# Architecture

![Substrakt architecture: frontend, Rust shell and Python sidecar on the user's machine, the egress chokepoint with its three operating modes, and the persistence boundary](architecture.svg)

Source: [`architecture.mmd`](architecture.mmd) (Mermaid). The SVG is drawn
from it by hand; change both together.

## Three processes, one direction

```text
React frontend  ──invoke──▶  Rust shell  ──HTTP 127.0.0.1──▶  Python sidecar
   (no fetch)               (chokepoint)    (bearer token)
```

**Frontend** (`src/`). React in the Tauri WebView. Every backend call goes
through `src/api/client.ts` and Tauri `invoke`. The frontend never learns the
sidecar's port or session token, and it has no way to open a network
connection: ESLint rejects `fetch`, `XMLHttpRequest`, `WebSocket`,
`EventSource`, `navigator.sendBeacon`, `axios` and the Tauri HTTP plugin.

**Rust shell** (`src-tauri/`). Owns every process and network boundary.

| Module | Responsibility |
|---|---|
| `lib.rs` | start-up, shared state, plugins, command registration |
| `sidecar.rs` | starts the sidecar, passes token and read roots, checks the handshake, keeps the stdin watchdog open |
| `bridge.rs` | Tauri commands; forwards calls with the bearer token to `127.0.0.1` |
| `egress.rs` | `Egress::request`, the only place that may release an outbound target; audit log |
| `policy.rs` | loads the machine-wide policy; falls back to Air-gap |

**Python sidecar** (`sidecar/substrakt/`). FastAPI bound to `127.0.0.1:0`.
The kernel picks a free port, which the sidecar reports in its handshake. It
parses PDFs, images and spreadsheets, runs Tesseract OCR, extracts and
normalises values and grounds each one at its position in the document. It
imports no HTTP client; Ruff and `scripts/check-egress.sh` reject `requests`,
`urllib.request` and `httpx` at runtime. Errors leave it as RFC 9457
`application/problem+json` with a stable key, never as a stack trace.

The session token travels through the environment, not process arguments.
If the shell dies, the sidecar's stdin closes and it exits, so there are no
orphaned processes.

## Egress and operating modes

All outbound traffic must pass `Egress::request` in
`src-tauri/src/egress.rs`. The local connection to the sidecar is not egress.

| Mode | Allowed outbound targets |
|---|---|
| **Air-gap** (default) | none |
| **On-premise** | hosts on an administrator's allowlist in the customer network, for example a vLLM server |
| **Cloud** | external providers, only after explicit unlock |

An inference server outside the customer network is not allowed in any mode.
Every allowed and every refused attempt is logged, so the promise can be
proven. The mode comes from a machine-wide policy (see
[Configuration](../configuration.md)); a missing or broken policy means
Air-gap.

`Egress::request` has no caller yet. The first will be the LLM path of
stage 3.

## Persistence boundary

Loaded documents and their contents live only in the sidecar's memory
(`sidecar/substrakt/store.py`). SQLite stores document types, field
definitions and extraction runs, never document contents. Migrations under
`sidecar/substrakt/db/migrations/` are applied in order through
`PRAGMA user_version`, each in one transaction.

Writing document contents to disk would create a second data trail and needs
an explicit architecture decision, not just a new table.

## Coordinates

Rectangles are always stored in document coordinates (PDF points), never in
screen pixels, so highlights stay on the same spot at any zoom, scaling or
rotation. The conversion exists in exactly two places,
`sidecar/substrakt/parsers/pdf.py` and `src/viewer/coords.ts`, and both are
tested against the shared fixture `tests/sidecar/fixtures/coordinates.json`.

## Hard rules

- **No model name in code.** Models are meant to be swappable; repository,
  revision, SHA-256 and licence belong in a model registry (planned for
  stage 3).
- **No quantisation method in code.** GGUF locally, AWQ or
  compressed-tensors on a server, are properties of a registry entry.
- **No PyTorch in the bundle.** The target has no GPU, and PyTorch alone
  adds 1.5 to 4 GB. Machine learning runs on ONNX Runtime or llama.cpp.
- **No network access at runtime.** `HF_HUB_OFFLINE=1` and
  `TRANSFORMERS_OFFLINE=1` are set by shell and CI.

The binding decisions behind these rules are in
[`docs/decisions.md`](../decisions.md).

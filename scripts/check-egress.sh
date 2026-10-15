#!/usr/bin/env bash
# Grep gate: network access only through the chokepoint.
#
# This complements ESLint and Ruff with a check that still applies if someone
# changes the linter configuration or disables a rule in a comment. Its
# deliberately coarse syntax-independent matching is harder to bypass with a
# spelling that a parser considers harmless.
#
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RED=$'\033[31m'; GREEN=$'\033[32m'; RESET=$'\033[0m'
ERRORS=0

report() {
  printf '%s✗%s %s\n' "$RED" "$RESET" "$1"
  ERRORS=$((ERRORS + 1))
}

# --- Frontend --------------------------------------------------------------
# Comments and strings may mention forbidden names; calls are rejected.
MATCHES=$(grep -rnE '(^|[^a-zA-Z0-9_."'"'"'`])(fetch|XMLHttpRequest|EventSource)[[:space:]]*\(' \
  --include='*.ts' --include='*.tsx' src/ 2>/dev/null | grep -v '^[^:]*:[0-9]*:[[:space:]]*//' || true)
if [ -n "$MATCHES" ]; then
  report "Network call found in the frontend:"
  echo "$MATCHES" | sed 's/^/      /'
fi

MATCHES=$(grep -rn "from ['\"]axios['\"]\|@tauri-apps/plugin-http" \
  --include='*.ts' --include='*.tsx' src/ 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
  report "HTTP library imported in the frontend:"
  echo "$MATCHES" | sed 's/^/      /'
fi

# --- Python sidecar --------------------------------------------------------
# The sidecar talks only to the local process. Outbound requests belong in
# src-tauri/src/egress.rs.
MATCHES=$(grep -rnE '^[[:space:]]*(import|from)[[:space:]]+(requests|urllib3|aiohttp|httpx)\b' \
  --include='*.py' sidecar/substrakt/ 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
  report "Network library imported in the sidecar:"
  echo "$MATCHES" | sed 's/^/      /'
fi

MATCHES=$(grep -rnE 'urllib\.request\.(urlopen|urlretrieve)' \
  --include='*.py' sidecar/substrakt/ 2>/dev/null || true)
if [ -n "$MATCHES" ]; then
  report "Direct network access found in the sidecar:"
  echo "$MATCHES" | sed 's/^/      /'
fi

# --- Measurement tools -----------------------------------------------------
# bench/ is deliberately outside substrakt/ and is not shipped. urllib is
# allowed there for local model servers, but non-local targets are not.
MATCHES=$(grep -rnoE 'https?://[a-zA-Z0-9.-]+' --include='*.py' bench/ 2>/dev/null \
  | grep -vE '://(127\.0\.0\.1|localhost|\[::1\])' || true)
if [ -n "$MATCHES" ]; then
  report "Non-local target found in a measurement script:"
  echo "$MATCHES" | sed 's/^/      /'
fi

# --- Rust ------------------------------------------------------------------
# reqwest may appear only in bridge.rs (local sidecar), sidecar.rs (handshake),
# egress.rs (the chokepoint) and lib.rs (client construction).
MATCHES=$(grep -rn 'reqwest::' --include='*.rs' src-tauri/src/ 2>/dev/null \
  | grep -vE 'src-tauri/src/(bridge|egress|sidecar|lib)\.rs' || true)
if [ -n "$MATCHES" ]; then
  report "HTTP client outside bridge.rs/egress.rs/sidecar.rs/lib.rs:"
  echo "$MATCHES" | sed 's/^/      /'
fi

# --- Tauri permissions -----------------------------------------------------
# The HTTP plugin would give the frontend a path around the chokepoint.
if grep -q '"http:' src-tauri/capabilities/*.json 2>/dev/null; then
  report "HTTP permission in Tauri capabilities bypasses the chokepoint."
fi

if [ "$ERRORS" -eq 0 ]; then
  printf '%s✓%s Egress gate: no network access outside the chokepoint.\n' "$GREEN" "$RESET"
  exit 0
fi

printf '\n%s%d egress rule violation(s).%s\n' "$RED" "$ERRORS" "$RESET"
echo "See docs/decisions.md: outbound traffic passes through exactly one"
echo "function in src-tauri/src/egress.rs."
exit 1

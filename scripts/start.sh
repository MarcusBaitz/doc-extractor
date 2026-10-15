#!/usr/bin/env bash
# Set up and start Substrakt with one command: `npm start`.
#
# This composes the existing steps instead of copying them: setup-dev.sh for
# tools and dependencies, fetch-models.sh for verified model files and then
# application start through dev-wsl.sh under WSL2. Downloads happen only here
# during setup; the running application downloads nothing.
#
# Full setup takes minutes because setup-dev.sh runs `npm ci` and `uv sync`.
# A stamp under node_modules/ records the configured revision. `npm start`
# starts immediately while lock files and setup scripts remain unchanged and
# required tools exist. `npm start -- --fresh` forces setup.
#
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

YELLOW=$'\033[33m'; RED=$'\033[31m'; BLUE=$'\033[34m'; RESET=$'\033[0m'

if [ "$(uname -s)" != "Linux" ]; then
  printf '%s✗%s Setup currently supports only Linux and WSL2.\n' "$RED" "$RESET"
  printf '    On macOS and Windows, follow the setup steps in README.md manually.\n'
  exit 1
fi

export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

# The stamp lives in node_modules/ so removing that directory triggers setup.
STAMP="$ROOT/node_modules/.substrakt-configured"
revision() {
  cat package.json package-lock.json sidecar/pyproject.toml sidecar/uv.lock \
    scripts/setup-dev.sh scripts/fetch-models.sh 2>/dev/null | sha256sum | cut -d' ' -f1
}

setup=0
[ "${1:-}" = "--fresh" ] && setup=1
[ -f "$STAMP" ] && [ "$(cat "$STAMP")" = "$(revision)" ] || setup=1
command -v cargo >/dev/null 2>&1 || setup=1
command -v uv >/dev/null 2>&1 || setup=1
[ -d sidecar/.venv ] || setup=1
[ -f models/tessdata/deu.traineddata ] || setup=1

if [ "$setup" -eq 1 ]; then
  bash scripts/setup-dev.sh
  # setup-dev.sh continues when apt packages remain pending without a terminal.
  # Without them the shell cannot build, and starting would fail only after a
  # lengthy Cargo build.
  if ! pkg-config --exists webkit2gtk-4.1 2>/dev/null; then
    printf '\n%s✗%s System packages are still missing; run the command above, then `npm start` again.\n' "$RED" "$RESET"
    exit 1
  fi
  printf '%s==>%s Model files\n' "$BLUE" "$RESET"
  bash scripts/fetch-models.sh
  revision > "$STAMP"
else
  printf '%s  ✓%s configured; starting directly (fresh setup: npm start -- --fresh)\n' "$BLUE" "$RESET"
fi

if grep -qi microsoft /proc/version 2>/dev/null; then
  exec bash scripts/dev-wsl.sh
fi
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  printf '%s  !%s No graphical session found; the window cannot appear.\n' "$YELLOW" "$RESET"
fi
exec npm run tauri dev

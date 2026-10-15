#!/usr/bin/env bash
# Set up the Substrakt development environment (Linux/WSL2, Ubuntu 24.04).
#
# The apt section needs sudo and asks for the password once. Everything else is
# installed in the home directory without elevated privileges.
#
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

BLUE=$'\033[34m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
step() { printf '%s==>%s %s\n' "$BLUE" "$RESET" "$1"; }
ok()   { printf '%s  ✓%s %s\n' "$GREEN" "$RESET" "$1"; }
note() { printf '%s  !%s %s\n' "$YELLOW" "$RESET" "$1"; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- 1. System packages (sudo) ---------------------------------------------
# Tauri v2 expects webkit2gtk 4.1; version 4.0 is insufficient.
APT_PACKAGES=(
  build-essential pkg-config curl wget file
  libwebkit2gtk-4.1-dev
  libgtk-3-dev
  libayatana-appindicator3-dev
  librsvg2-dev
  libssl-dev
  libxdo-dev
  # tauri-plugin-dialog needs libdbus-1-dev through libdbus-sys. Without it,
  # `cargo check` fails in pkg-config; this was measured rather than assumed.
  libdbus-1-dev
  tesseract-ocr
)

step "Checking system packages"
MISSING=()
for package in "${APT_PACKAGES[@]}"; do
  dpkg -s "$package" >/dev/null 2>&1 || MISSING+=("$package")
done

APT_PENDING=0

if [ ${#MISSING[@]} -eq 0 ]; then
  ok "all system packages are installed"
elif sudo -n true 2>/dev/null || [ -t 0 ]; then
  note "missing: ${MISSING[*]}"
  sudo apt-get update
  sudo apt-get install -y "${MISSING[@]}"
  ok "system packages installed"
else
  # Without a terminal sudo cannot request a password. Print the command and
  # continue with Rust, uv and project dependencies, which need no elevation.
  APT_PENDING=1
  note "missing: ${MISSING[*]}"
  note "No terminal is available for the password prompt; run this once:"
  echo
  echo "    sudo apt-get update && sudo apt-get install -y ${MISSING[*]}"
  echo
  note "The remaining setup continues without sudo."
fi

# The distribution's tesseract-ocr-deu is deliberately not installed: Ubuntu
# 24.04 supplies trained data 4.1.0 with engine 5.3.4. The licence audit
# requires the verified Apache-2.0 chain from tessdata_best, fetched with
# SHA-256 verification by scripts/fetch-models.sh.

# --- 2. Rust ---------------------------------------------------------------
step "Rust toolchain"
if command -v rustup >/dev/null 2>&1 || [ -x "$HOME/.cargo/bin/rustup" ]; then
  ok "rustup available: $("$HOME/.cargo/bin/cargo" --version 2>/dev/null || cargo --version)"
else
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --profile minimal --default-toolchain stable --no-modify-path
  ok "Rust installed"
fi
export PATH="$HOME/.cargo/bin:$PATH"

# --- 3. uv -----------------------------------------------------------------
step "uv (Python package management)"
if command -v uv >/dev/null 2>&1 || [ -x "$HOME/.local/bin/uv" ]; then
  ok "uv available: $("$HOME/.local/bin/uv" --version 2>/dev/null || uv --version)"
else
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ok "uv installed"
fi
export PATH="$HOME/.local/bin:$PATH"

# --- 4. Project dependencies -----------------------------------------------
step "Python sidecar"
# Use --all-groups, not --all-extras: dev and corpus are dependency groups.
(cd "$ROOT/sidecar" && uv sync --all-groups)
ok "sidecar environment ready"

step "Frontend"
(cd "$ROOT" && npm ci 2>/dev/null || npm install)
ok "frontend dependencies ready"

# --- 5. Completion ---------------------------------------------------------
echo
if [ "$APT_PENDING" -eq 1 ]; then
  printf '%sSystem packages are still missing.%s The application cannot be built\n' \
    "$YELLOW" "$RESET"
  printf 'without them, although Python tests, frontend and gates already run.\n\n'
  printf '    sudo apt-get update && sudo apt-get install -y %s\n\n' "${MISSING[*]}"
  printf 'Then run this script again.\n\n'
else
  cat <<'END'
Done. Next steps:

  npm run tauri dev           start the application
  npm run check               run all local gates, tests and type checks
  ./scripts/fetch-models.sh   fetch models with SHA-256 verification

END
fi

cat <<'END'
If cargo or uv cannot be found, add them to the shell path:

  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

END

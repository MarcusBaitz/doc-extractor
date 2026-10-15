#!/usr/bin/env bash
# Start the application under WSL2.
#
# WSLg does not pass a GPU through to WebKitGTK. Without the switches below,
# the application starts but reports:
#
#   libEGL warning: failed to get driver name for fd -1
#   MESA: error: ZINK: failed to choose pdev
#   libEGL warning: egl: failed to create dri2 screen
#
# The window also appears as a Wayland surface that does not render reliably.
# Measured on Ubuntu 24.04 under WSL2 with WSLg: these four variables remove
# the messages and produce a regular X11 window (1440×900).
#
# A native Linux desktop does not need this script; use `npm run app` there.
#
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  printf '\033[33m  !\033[0m This is not WSL; `npm run app` is sufficient here.\n'
  printf '    The switches are still set because they are harmless.\n\n'
fi

# X11 instead of Wayland produces a regular inspectable X window.
export GDK_BACKEND=x11
# Disable WebKitGTK GPU compositing to avoid empty content.
export WEBKIT_DISABLE_COMPOSITING_MODE=1
# The DMABUF renderer needs a passed-through GPU, which is unavailable here.
export WEBKIT_DISABLE_DMABUF_RENDERER=1
# Use software rasterization instead of the failing ZINK connection.
export LIBGL_ALWAYS_SOFTWARE=1

export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

exec npm run tauri dev

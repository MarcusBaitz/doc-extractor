#!/usr/bin/env python3
"""Generate the application icon.

A sheet with highlighted evidence represents what the application does: show
the position in a document where a value appears.

The icon is generated instead of committed as a binary so it remains
reproducible without another source file. The Tauri CLI generates derived
formats (icns, ico and every size):

    python scripts/generate-icon.py
    npx tauri icon /tmp/substrakt-icon.png
    rm -rf src-tauri/icons/android src-tauri/icons/ios

Mobile variants are removed because the target platforms are Windows, macOS
and Linux.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

S = 1024

# Interface colours (Tailwind sky/slate/amber) keep the icon and application
# visually consistent.
SKY = (2, 132, 199, 255)
SHEET = (255, 255, 255, 255)
FOLD = (186, 230, 253, 255)
LINE = (148, 163, 184, 255)
HIGHLIGHT_FILL = (254, 240, 138, 255)
HIGHLIGHT_BORDER = (234, 179, 8, 255)
HIGHLIGHT_TEXT = (120, 53, 15, 255)


def draw() -> Image.Image:
    image = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)

    d.rounded_rectangle([0, 0, S, S], radius=int(S * 0.22), fill=SKY)

    # Sheet with a folded top-right corner.
    lx, ly = int(S * 0.26), int(S * 0.20)
    rx, ry = int(S * 0.74), int(S * 0.80)
    fold = int(S * 0.14)
    d.polygon(
        [(lx, ly), (rx - fold, ly), (rx, ly + fold), (rx, ry), (lx, ry)],
        fill=SHEET,
    )
    d.polygon(
        [(rx - fold, ly), (rx, ly + fold), (rx - fold, ly + fold)],
        fill=FOLD,
    )

    # Suggested text lines, with a shorter third line to avoid a grid effect.
    height = int(S * 0.022)
    for i, y in enumerate(range(int(S * 0.30), int(S * 0.46), int(S * 0.055))):
        end = int(S * 0.58) if i == 2 else int(S * 0.67)
        d.rounded_rectangle(
            [int(S * 0.33), y, end, y + height], radius=height // 2, fill=LINE
        )

    # The highlight represents the core product interaction.
    d.rounded_rectangle(
        [int(S * 0.31), int(S * 0.53), int(S * 0.69), int(S * 0.68)],
        radius=int(S * 0.012),
        fill=HIGHLIGHT_FILL,
        outline=HIGHLIGHT_BORDER,
        width=int(S * 0.016),
    )
    d.rounded_rectangle(
        [int(S * 0.35), int(S * 0.585), int(S * 0.60), int(S * 0.615)],
        radius=int(S * 0.015),
        fill=HIGHLIGHT_TEXT,
    )

    return image


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/substrakt-icon.png")
    draw().save(target)
    print(f"{target} — {S}×{S}")
    print("Continue with: npx tauri icon", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())

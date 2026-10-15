#!/usr/bin/env bash
# Fetch model files with SHA-256 verification.
#
# The application downloads nothing at runtime. This script runs only while
# setting up development or packaging the installer.
#
# Every entry names its source, checksum and licence. A model without this
# information cannot enter the build (see licenses/policy.toml).
#
# Ubuntu 24.04 ships version 4.1.0 trained data through
# `apt install tesseract-ocr-deu` while the engine is 5.3.4. The licence audit
# requires the verified Apache-2.0 chain from tessdata_best.
#
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${SUBSTRAKT_MODEL_DIR:-$ROOT/models}"

GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'

# Format: target path|URL|SHA-256|licence
# Checksums come from their respective releases and are pinned here. If one is
# missing, the file is fetched and its checksum reported for a subsequent run.
MODELS=(
  "tessdata/deu.traineddata|https://github.com/tesseract-ocr/tessdata_best/raw/4.1.0/deu.traineddata|8407331d6aa0229dc927685c01a7938fc5a641d1a9524f74838cdac599f0d06e|Apache-2.0"
  "tessdata/eng.traineddata|https://github.com/tesseract-ocr/tessdata_best/raw/4.1.0/eng.traineddata|8280aed0782fe27257a68ea10fe7ef324ca0f8d85bd2fd145d1c2b560bcb66ba|Apache-2.0"
  # Document VLM for reading stage 3 (measurements 1 and 2 from stage 0).
  # Apache-2.0, 258M parameters, revision pinned as of 5 October 2025.
  # mmproj carries the vision encoder and accompanies the language model.
  "vlm/granite-docling-258M-Q8_0.gguf|https://huggingface.co/ggml-org/granite-docling-258M-GGUF/resolve/684c1800c5fbd614e29b4d1a82177e6c122af1f3/granite-docling-258M-Q8_0.gguf|b687245c212b59da938e411e2d4485596cbaeed1ae52706582ac38ed6a970f76|Apache-2.0"
  "vlm/mmproj-granite-docling-258M-Q8_0.gguf|https://huggingface.co/ggml-org/granite-docling-258M-GGUF/resolve/684c1800c5fbd614e29b4d1a82177e6c122af1f3/mmproj-granite-docling-258M-Q8_0.gguf|3d440e65a91e640dc0a53897ad7897700c39324802aaff2072232b6f21d0cadb|Apache-2.0"
)

mkdir -p "$TARGET"
ERRORS=0

for entry in "${MODELS[@]}"; do
  IFS='|' read -r path url expected license <<< "$entry"
  file="$TARGET/$path"
  mkdir -p "$(dirname "$file")"

  if [ -f "$file" ]; then
    actual="$(sha256sum "$file" | cut -d' ' -f1)"
    if [ "$expected" = "CHECKSUM_MISSING" ]; then
      printf '%s!%s %s exists — SHA-256: %s\n' "$YELLOW" "$RESET" "$path" "$actual"
      printf '    Add it to scripts/fetch-models.sh.\n'
      continue
    fi
    if [ "$actual" = "$expected" ]; then
      printf '%s✓%s %s (%s)\n' "$GREEN" "$RESET" "$path" "$license"
      continue
    fi
    printf '%s✗%s %s: checksum differs\n    expected %s\n    actual   %s\n' \
      "$RED" "$RESET" "$path" "$expected" "$actual"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  printf 'Downloading %s …\n' "$path"
  if ! curl -fsSL "$url" -o "$file.partial"; then
    printf '%s✗%s Download failed: %s\n' "$RED" "$RESET" "$url"
    rm -f "$file.partial"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  actual="$(sha256sum "$file.partial" | cut -d' ' -f1)"
  if [ "$expected" != "CHECKSUM_MISSING" ] && [ "$actual" != "$expected" ]; then
    printf '%s✗%s %s: checksum differs; file discarded\n' "$RED" "$RESET" "$path"
    rm -f "$file.partial"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  mv "$file.partial" "$file"
  if [ "$expected" = "CHECKSUM_MISSING" ]; then
    printf '%s!%s %s downloaded — SHA-256: %s\n' "$YELLOW" "$RESET" "$path" "$actual"
    printf '    Add it to scripts/fetch-models.sh.\n'
  else
    printf '%s✓%s %s (%s)\n' "$GREEN" "$RESET" "$path" "$license"
  fi
done

echo
if [ "$ERRORS" -gt 0 ]; then
  printf '%s%d invalid model(s).%s\n' "$RED" "$ERRORS" "$RESET"
  exit 1
fi

printf 'Models stored under %s\n' "$TARGET"
printf 'LLM and OCR models for stage 3 will follow when the inference\n'
printf 'interface is ready.\n'

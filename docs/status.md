# Status after stage 1

**28 July 2026** · Report as required by the build prompt: what works, what
is missing, which assumptions turned out to be wrong.

This is a historical record. Code names below are the current ones after the
switch to English; the findings and figures are those of stage 1.

## What works

**Loading documents.** PDF (pypdfium2 + pdfplumber), Excel/CSV (openpyxl,
python-calamine, own encoding detection) and images (Pillow + scikit-image)
lead into one shared document model. The word bounding-box index is filled
for PDF and spreadsheets; for images it stays empty until OCR arrives in
stage 3, and the document then honestly reports `text_source: "none"` instead
of passing off an empty extraction as success.

**Coordinates.** The conversion is implemented in exactly two places and
checked against the same fixture. All four page rotations lead back to the
same rectangle; zoom from 0.5 to 4.0 and retina ratios 1 and 2 shift nothing.
200 random rectangles per combination, fixed seed.

**Sidecar.** FastAPI on `127.0.0.1` with a kernel-assigned port, a 256-bit
session token through the environment, a JSON handshake over stdout, and a
stdin watchdog against orphaned processes. Errors leave the process as RFC
9457 `problem+json` with a stable key, never as a stack trace.

**Viewer.** An overlay abstraction across all three modes: PDF.js canvas with
navigation, zoom and rotation, image canvas, and a virtualised spreadsheet
grid with sheet tabs and cell range selection. Highlights can be drawn,
moved, resized and deleted, with mouse and keyboard.

**Persistence.** Complete schema according to the build prompt, migrations
through `PRAGMA user_version`, idempotent, in transactions.

**Gates.** Licence policy as a machine-readable single source of truth with
separate checks for runtime and development; egress gate through ESLint, Ruff
and a grep script. The egress gate is negatively tested: a built-in `fetch`
demonstrably makes it fail.

**Measurements.** PDF with text layer: 12–16 ms per page against a budget of
100 ms. Rendering at 2× scale: about 21 ms per page. Protocols under
[`measurements/`](measurements/).

**Rust shell.** Compiles, Clippy clean (`-D warnings`), eight unit tests
green.

**The application runs.** Window 1440×900 under WSLg, handshake on a
kernel-assigned port, mode `airgap`, both offline switches set. A complete
run against the live sidecar: PDF loaded (100 words, `text_layer`), word
index with correct locations, raw text with umlauts, Excel with three sheets,
page rendered as PNG, broken PDF rejected as `422 document-corrupt`. Without
token: `401`.

On exit no process is left behind; the stdin watchdog takes effect.

| Layer | Tests |
|---|---|
| Python | 79 (coordinates, parsers, migrations, API, error cases) |
| TypeScript | 65 (coordinates against the shared fixture, image rotation) |
| Rust | 8 (egress modes, policy, token, read roots) |

All five CI jobs green: sidecar, frontend, shell, licence gates, egress.

**The core test has passed.** Draw a highlight, zoom to 400%, rotate the page
by 90°: it stays on the same document point. Confirmed by Marcus on 28 July
2026 in the running viewer, after the rotation bug described below was fixed.

To read off instead of estimating, the toolbar shows the document coordinates
of the selected highlight. They do not change under zoom and rotation; only
the screen representation does.

## What is missing

Planned for later stages: field extraction and grounding (stage 2), OCR, LLM
integration and document type recognition (stage 3), export, batch, installer
and air-gap CI test (stage 4).

Not implemented although planned for stage 1: **generating** the TypeScript
types from `openapi.json`. The types are written by hand and match the
Pydantic model; a test checks that all endpoints of the contract exist, but
not field by field. This is a deliberately chosen shortcut and should be
caught up in stage 2.

## What CI revealed

Five bugs that stayed invisible locally. Four runs until green.

**The sidecar tests only ran by chance.** I had always called them with
`SUBSTRAKT_DEV=1` and overlooked that they do not start at all without this
variable: `config.load()` refuses to work without a session token, and this
already applies during collection, because `app.py` reads the configuration
at module level. Fixed in `tests/sidecar/conftest.py`, at module level; a
fixture would come too late.

**`cargo fmt --check` failed.** Avoidable: unlike the build, `cargo fmt`
needs no system libraries.

**The icons were missing.** `tauri::generate_context!()` requires the files
declared in `tauri.conf.json`; I had referenced them but never generated
them. Clippy failed on the macro evaluation, not on the code.

**The benchmark did not run without the shell**: `conftest.py` does not take
effect outside pytest. Two weaknesses of the measurement itself surfaced
along the way: the first pass also measured module loading (a CSV came to
122 ms instead of 2 ms), and the budget gate sat in the wrong place. Now:
a warm-up run, and a broken budget aborts only with `--strict`. On a shared
runner with two cores, timings are too unreliable for a build gate.

**Borrow checker error (E0597) in `lib.rs`.** The `MutexGuard` from
`state.sidecar.lock().await.take()` lived in the `if let` until the end of
the block and outlived `state`.

And one finding that **no** tool would have reported, only the review after
the borrow error: in `bridge.rs` the same guard was held across the entire
HTTP call in six places. That compiles, but it would have serialised all
requests, so that a render call with a 120-second timeout would also have
blocked loading the raw text. The viewer fetches words and text
concurrently.

**Lesson:** the Rust part was the only one I could not build locally, and
that is exactly where the worst bugs were. What cannot be checked locally is
not checked but hoped for.

## What the first start revealed

Two gaps that neither tests nor CI could show, because they only arise in the
running interplay.

**The path check had no effect.** `store.py` checks loaded files against
`SUBSTRAKT_ROOTS`, and `errors.py` has `PathNotAllowed` ready for this, but
`sidecar.rs` never set the variable. With an empty list the sidecar does not
check at all: it opened `/etc/passwd` without complaint. The matching test
passed all along, because it sets the variable itself; it checked a function
that was never active in operation.

No attack path from outside: the sidecar listens only on `127.0.0.1` and
requires a token that only the shell knows. But a promised protection layer
that does not take effect is worse than none: it pretends security.

Fixed: the shell now passes the home directory, `/media`, `/mnt` and `/srv`.
Demonstrated on the running process: `/tmp` and `/etc/passwd` are rejected,
home and project folder are read. A Rust test records that the list is not
empty and contains no system directories.

**No logger initialised.** All `log::info!` calls on the Rust side went
nowhere; “Sidecar connected on port …” appeared nowhere. Now through
`tauri-plugin-log` with rotation to
`~/.local/share/it.baitz.substrakt/logs/`.

**Image highlights did not rotate along**, found by Marcus in the running
viewer, not by a test. When a scan was rotated by 90°, the highlight stayed
in place while the image rotated beneath it; afterwards it lay over the
recipient address instead of over the highlighted information block.

Two causes: in `coords.ts` the `image_rect` branch left with `return` before
the rotation switch was reached, so rotation was never computed for images.
And `ImageCanvas.tsx` gave the `img` swapped dimensions *and* a `rotate()`,
which swaps the axes twice.

The test for it is remarkable: it checked exactly this branch, but only with
`rotation: 0`, that is, only the case the code handled. **The same class of
failure as with the path check: a green test that secures nothing.** Eight
new cases cover all four rotations including round trips over zoom levels
and pixel ratios; they fail with the old code.

**WSLg needs four switches.** Without `GDK_BACKEND=x11`,
`WEBKIT_DISABLE_COMPOSITING_MODE`, `WEBKIT_DISABLE_DMABUF_RENDERER` and
`LIBGL_ALWAYS_SOFTWARE`, MESA throws errors (`ZINK: failed to choose pdev`)
and the window does not display reliably. Recorded in `scripts/dev-wsl.sh`,
callable through `npm run app:wsl`.

## Wrong assumptions

Nine points where reality differed from expectation. All were measured, not
assumed.

**1. pdfplumber and rotated pages.** At `rotation=90`, pdfplumber reports the
**unrotated** page dimensions but delivers word coordinates in the
**rotated** space: `x0` becomes larger than `page.width`, negative at 270°.
The four transformation rules are in the header of `parsers/pdf.py`. Without
this measurement every highlight on rotated pages would have sat in the
wrong place.

**2. charset-normalizer does not reliably detect CP1252.** A CP1252 file with
„Währung“ and „Frässpindel“ was classified as `mac_iceland`: the same bytes,
different characters. Encoding detection now checks BOM, then strict UTF-8,
then a suggestion from the library **only if it is plausible in a German
business context**, otherwise CP1252.

**3. openpyxl pads columns.** With `max_col`, `read_only` mode returns every
row padded with `None` up to the requested column count. A sheet with four
columns therefore reported 1024, and promptly triggered a false truncation
warning.

**4. `ImageOps.exif_transpose` destroys multi-page images.** It returns a new
image without frame navigation. A multi-page TIFF, that is, a scanned stack
of documents and a common real case, was reduced to its first page. EXIF
rotation now happens per frame.

**5. TypeScript 7 is not yet compatible.** `typescript-eslint` 8.65 requires
`<6.1.0`. Type-aware linting outweighs the speed gain of the native port; the
project stays on 6.0 and reassesses at the next `typescript-eslint` major.

**6. `license-checker` is unmaintained** and drags along six security
warnings about outdated `glob` versions, in the licence tool of all things.
Replaced by `npm query`, which is built in and delivers the same data.
Afterwards: zero warnings.

**7. PDF.js 6: `PDFDocumentProxy` no longer has `destroy()`**, and
`isEvalSupported` does not exist. Clean-up happens through the loading task.

**8. `libdbus-1-dev` is needed additionally**, through `tauri-plugin-dialog`
and `libdbus-sys`. It was in no guide; the build aborted with a pkg-config
error.

**9. `tesseract-ocr-deu` from Ubuntu 24.04 ships 4.1.0 traineddata**, while
the engine is 5.3.4. For the verified Apache-2.0 chain required by the
licence audit, `deu.traineddata` must be pinned from `tessdata_best`; the
distribution package is deliberately not installed.

## Two deviations from the plan

**The source documents were not copied into the repository.** The plan
intended it. Copies drift apart as soon as someone works on the original.
Instead, [`docs/README.md`](README.md) points to the sources,
[`docs/decisions.md`](decisions.md) condenses what is binding, and what is
enforced by machine is in `licenses/policy.toml` rather than in prose.

**Property tests without Hypothesis.** Hypothesis is licensed under MPL-2.0
and would therefore be on the review list. For coordinate transformations
`random.Random(seed)` is enough: reproducible, without an additional licence
question.

## Next steps

These were the next steps at the end of stage 1; they have since been done.

1. Run `./scripts/setup-dev.sh`, then `npm run app`. Only then does the
   application run as a whole, and the Rust part can be checked locally in
   future instead of through a CI run.
2. Manual verification: draw a rectangle, zoom to 400%, rotate the page,
   resize the window. The highlight must stay on the same document point.
   Then exit and check that no sidecar is left orphaned.
3. Catch up on stage 0: the four open measurements from
   [`decisions.md`](decisions.md), now that `bench/run.py` exists.
4. Begin stage 2: field builder, path A, grounding with rapidfuzz.

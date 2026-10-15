# Measurement protocols

The JSON files next to the protocols are kept exactly as they were recorded,
including their German keys; they are evidence and are not edited.

## Stage 0 — completed 28 July 2026

The four measurements for which, according to the architecture decision,
there were “no reliable public figures”. All four have been carried out; two
results change the plan.

| # | Question | Result | Protocol |
|--:|---|---|---|
| 1 | Is a VLM viable on CPU? | yes, 13.6 s/page at 150 dpi, but 28× slower than OCR | [vlm](stage0-vlm-2026-07-28.md) |
| 2 | Constrained decoding with VLMs? | works, but **57% of the values are still wrong** | [vlm](stage0-vlm-2026-07-28.md) |
| 3 | OCR reference | **Tesseract 98.9%**, RapidOCR 90.5% | [ocr](stage0-ocr-2026-07-28.md) |
| 4 | Server throughput | 10.1 pages/min, the lower end of the estimate | [server](stage0-server-2026-07-28.md) |

## Added later

| # | Question | Result | Protocol |
|--:|---|---|---|
| 5 | Handwriting in form fields? | **Tesseract 0 of 5**, granite-docling 1 of 5 and without a warning signal | [handwriting](handwriting.md) |

This measurement closes the gap that protocol 3 had left open: “Where a VLM
could win (handwriting, forms without lines), this corpus does not cover.” It
leads to manual entry as an equal extraction path.

## The three decisions that follow

### 1. Tesseract as primary engine, not RapidOCR

This reverses the previous plan. Tesseract is more accurate (98.9% against
90.5%), more robust against poor scans (−0.1 points against −3.2) and faster
(0.48 against 0.80 s/page).

The decisive point, however, is a side aspect: **RapidOCR's confidence is
useless as a control value.** It reports 97–99% where 87–90% is correct. The
planned confidence-driven escalation of the reading stage would never have
triggered, although every tenth word is missing. Tesseract understates
(92–94% at 98.9%) and works as a trigger; a threshold around 85% is the
starting point.

As a side finding, RapidOCR pulls in `opencv-python`, whose wheels bundle
FFmpeg under LGPL-2.1 — the licence gate caught it.

### 2. The provenance layer is necessary, as measured

Constrained decoding works with multimodal models: 10 of 10 answers were
valid, schema-conforming JSON. **23 of 40 fields were correct.** As the total
amount the model returned the VAT, a VAT ID, a line item and a customer
number; as the VAT ID it once returned the field label itself.

An extractor that relies on schema validation would have shipped **43% wrong
values here — without any warning signal.** That makes “every value needs a
location” no longer a precaution but the basis for the result being worth
anything at all.

### 3. The reading stage stays two-level, the server serves path B

The planned third reading stage (document VLM) is viable locally but does not
pay off for printed documents: Tesseract on the CPU is more accurate and
**twelve times faster than a 7B VLM on a dedicated GPU** (125 against 10.1
pages/min).

This shifts the justification of the server variant. It remains right — but
not because “vision models become usable on the server”, but because **path
B becomes interactive** and mass processing becomes possible. For the reading
stage the CPU is enough.

For purchasing advice: with vision models, **VRAM limits, not compute**.
Throughput collapsed from four parallel requests on, because the KV cache
holds only about two simultaneous image requests. An L4 with 24 GB should
achieve more than the consumer card measured here, despite slower compute
units.

## What these measurements cannot do

**The corpus is synthetic.** Ten generated documents in four scan qualities,
with exact ground truth from the PDF text layer — but without folds, stains,
stamps, staples, carbon copies or handwritten notes. The absolute accuracy
figures are an **upper bound**. For comparing the methods with each other and
for all timing measurements this does not matter.

**Where a VLM could win was not measured:** handwriting, forms without lines,
nested tables. The reading stage therefore remains planned as a swappable
module — it just does not become the default escalation.

**As soon as real documents are available**, measurement 3 and the
confidence threshold must be repeated. That is the most important open point.

## Earlier protocols

- [`measurement-2026-10-15.md`](measurement-2026-10-15.md) — parse and render
  times after the switch to YAML document kinds and the English rename; the
  three OCR images and the two-page form are over budget on this WSL2 machine
- [`../../corpus/evaluation/README.md`](../../corpus/evaluation/README.md) —
  84-PDF field benchmark of the same day: core 315/336, all 730/756, 0 wrong
  without review flag (`corpus/evaluation/reports/2026-10-15/`)
- [`measurement-2026-07-27.md`](measurement-2026-07-27.md) — parse and render
  times from stage 1 (performance budgets)

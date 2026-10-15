# Measurement: handwriting in form fields

**Date:** 28 July 2026
**Occasion:** `corpus/out/transportschein-aok.pdf` — an AOK transport form
(specimen) whose billing data is entered by hand into box fields.
**Question:** Can these values be read automatically, locally?

The stage 0 measurement had named this gap explicitly: “Where a VLM could win
(handwriting, forms without lines), this corpus does not cover.” It is closed
here.

## Set-up

Five fields with known target values, each as a separate image crop at
300 dpi. Tested were Tesseract 5.5.0 (`deu`, `tessdata_best`) in four page
segmentation modes, each free and with the character set restricted to
`0123456789,-R`, and granite-docling-258M (Q8_0) via llama.cpp, CPU only,
6 threads.

## Tesseract result

| Field | Target | free (best mode) | with character set |
|---|---|---|---|
| IK des Transporteurs (carrier ID) | `601234567` | `ein 131716 Ice le` | `1317161` |
| Belegnummer (document number) | `2026071501` | `21 Hlablelo1/` | `21216114` |
| Gesamt-Brutto (gross total) | `185,40` | `hPa` | `11` |
| Rechnungsnummer (invoice number) | `R-2026-0001` | `FECHTEN 1,` | `RRR-1,` |
| Zuzahlung (co-payment) | `10,00` | `AL` | *(empty)* |

**0 of 5 correct.** No mode (6, 7, 11, 13) and no restriction of the
character set changed that. The restricted set produces shorter outputs, but
not more correct ones — it merely forces the model to express its wrong
guesses in digits.

On the whole page, Tesseract reads the **printed** parts of the form well:
268 words, field labels and headers correct. The line runs cleanly between
print and handwriting, not between easy and hard.

## granite-docling result

On the **whole billing block** (with the surrounding labels), 5.2 s:

```
IK des Transporteurs
6 0 1 2 3 4 5 6 7          ← correct
Rechnungsnummer
R-2 0 2 6 - 0 0 0 0 1      ← one zero too many
Belegnummer   Gesamt-Brutto
20 2 6 0 7 5 6 1 4 8 5 1 4 0 1 4 0 1 4 0 …   ← repetition loop
```

On **single field crops**, about 3 s each: nothing usable, for none of the
five fields.

The model needs the surrounding labels as context. Isolate the box, and it
loses its footing. And even in the block context the output breaks into a
repetition loop after two fields — the same behaviour that already appeared
at 300 dpi in the stage 0 measurement.

## Assessment

One value read correctly and a second read almost correctly are not an
extraction method. What matters is not the hit rate but that **no signal shows
which value is right**. The carrier ID was right, the invoice number off by
one digit — from the outside the two are indistinguishable. This is the same
finding as for constrained decoding in stage 0: 23 of 40 values correct,
without a warning for the other 17.

A wrong value with high confidence is worse than no value at all.

## Consequence for the product

Manual entry as an equal extraction path, not a stopgap: source `manual`,
confidence 1.0, the marked region as the location. Implemented in
`extraction/fields.py::_manual`.

This makes the division of labour explicit:

* **Person** — recognises the handwriting. They can do this reliably, and no
  one else can here.
* **Tool** — remembers the field position (saved template), normalises
  (`185,40` → `185.4`), checks the type, records the location and exports in
  machine-readable form.

For the second transport form from the same health insurer, the field
position is already stored: the user clicks the field, sees the crop and
types the value. No searching, no formatting, no transcription error.

The path for later would be a model trained on handwriting (TrOCR is
MIT-licensed, but brings PyTorch along and is not available as ONNX). That is
a separate decision with its own measurement — not something to build in here
in passing.

## Reproducing

```bash
cd sidecar
uv run pytest ../tests/sidecar/test_manual_values.py -q
```

`test_transport_form_is_complete` records the case: five fields, five
locations, fully supported. It is skipped when the transport form is not in
the local corpus; the form is not part of the repository.

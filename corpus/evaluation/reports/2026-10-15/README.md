# Benchmark: 84 PDFs, document kind “invoice”

Substrakt · corpus/evaluation/v1 · 2026-10-15

**Regression on a known synthetic corpus, not a blind test.** Local pipeline
only. Reference values were loaded after extraction, for scoring.

## Summary

| Scope | Correct | PDFs complete | Review flags | Wrong without review flag |
|---|---|---|---|---|
| Core fields (4) | 315/336 (93.75 %) | 74 | 42 | 0 |
| All fields (9) | 730/756 (96.56 %) | 73 | 133 | 0 |

Core fields: belegnummer, belegdatum, gesamtbetrag, ust_idnr. A review flag never counts as a
correct value.

## Per field

| Field | Correct | Review flags |
|---|---|---|
| belegnummer | 78/84 | 12 |
| belegdatum | 82/84 | 8 |
| gesamtbetrag | 79/84 | 8 |
| nettobetrag | 82/84 | 2 |
| steuerbetrag | 81/84 | 5 |
| waehrung | 84/84 | 0 |
| ust_idnr | 76/84 | 14 |
| dokumentart | 84/84 | 0 |
| absender | 84/84 | 84 |

## Per group

| Group | PDFs | All fields | Wrong without review flag |
|---|---|---|---|
| split:setup | 24 | 208/216 (96.30 %) | 0 |
| family:A | 14 | 124/126 (98.41 %) | 0 |
| variant:digital | 60 | 540/540 (100.00 %) | 0 |
| variant:scan | 12 | 108/108 (100.00 %) | 0 |
| variant:photo | 12 | 82/108 (75.93 %) | 0 |
| split:known_layout | 18 | 157/162 (96.91 %) | 0 |
| family:B | 14 | 121/126 (96.03 %) | 0 |
| family:C | 14 | 120/126 (95.24 %) | 0 |
| split:unseen_layout | 42 | 365/378 (96.56 %) | 0 |
| family:D | 14 | 123/126 (97.62 %) | 0 |
| family:E | 14 | 119/126 (94.44 %) | 0 |
| family:F | 14 | 123/126 (97.62 %) | 0 |

Variants of the same source document are not independent documents.

## Remaining deviations (26)

| PDF | Variant | Field | Expected | Predicted | Review flag | Note |
|---|---|---|---|---|---|---|
| A03_photo | photo | belegnummer | INV-A-26-0003 | ∅ | yes | No unambiguous assignment for the field label |
| A03_photo | photo | gesamtbetrag | 41198.28 | ∅ | yes | No unambiguous assignment for the field label |
| B03_photo | photo | gesamtbetrag | 58761.53 | ∅ | yes | No unambiguous assignment for the field label |
| B03_photo | photo | ust_idnr | DE970000102 | ∅ | yes | No unambiguous assignment for the field label |
| B08_photo | photo | belegnummer | INV-B-26-0008 | ∅ | yes | No unambiguous assignment for the field label |
| B08_photo | photo | gesamtbetrag | 12551.13 | ∅ | yes | No unambiguous assignment for the field label |
| B08_photo | photo | ust_idnr | DE970000107 | ∅ | yes | No unambiguous assignment for the field label |
| C03_photo | photo | belegnummer | INV-C-26-0003 | ∅ | yes | No unambiguous assignment for the field label |
| C03_photo | photo | belegdatum | 2026-03-12 | ∅ | yes | No unambiguous assignment for the field label |
| C03_photo | photo | steuerbetrag | 8342.08 | ∅ | yes | No unambiguous assignment for the field label |
| C03_photo | photo | ust_idnr | DE970000202 | ∅ | yes | No unambiguous assignment for the field label |
| C08_photo | photo | belegnummer | INV-C-26-0008 | ∅ | yes | No unambiguous assignment for the field label |
| C08_photo | photo | ust_idnr | DE970000207 | ∅ | yes | No unambiguous assignment for the field label |
| D03_photo | photo | belegnummer | INV-D-26-0003 | ∅ | yes | No unambiguous assignment for the field label |
| D03_photo | photo | ust_idnr | DE970000302 | ∅ | yes | No unambiguous assignment for the field label |
| D08_photo | photo | ust_idnr | DE970000307 | ∅ | yes | No unambiguous assignment for the field label |
| E03_photo | photo | belegnummer | GS-E-26-0003 | ∅ | yes | No unambiguous assignment for the field label |
| E03_photo | photo | gesamtbetrag | -30159.99 | ∅ | yes | No unambiguous assignment for the field label |
| E03_photo | photo | steuerbetrag | -4815.46 | 4815.46 | yes | Confidence too low — review required |
| E03_photo | photo | ust_idnr | DE970000402 | ∅ | yes | No unambiguous assignment for the field label |
| E08_photo | photo | gesamtbetrag | -29940.80 | ∅ | yes | No unambiguous assignment for the field label |
| E08_photo | photo | nettobetrag | -25160.34 | 25160.34 | yes | Confidence too low — review required |
| E08_photo | photo | steuerbetrag | -4780.46 | 4780.46 | yes | Uncertain text recognition (55%) — review or enter the value manually |
| F03_photo | photo | belegdatum | 2026-03-15 | ∅ | yes | No unambiguous assignment for the field label |
| F03_photo | photo | ust_idnr | DE970000502 | ∅ | yes | No unambiguous assignment for the field label |
| F08_photo | photo | nettobetrag | 26121.25 | ∅ | yes | No unambiguous assignment for the field label |

## Files

Every field value is in [fields.csv](fields.csv) and [summary.csv](summary.csv);
[report.html](report.html) is the same report with filters and works offline.

## Protocol

Commit c9174e59a89f4cd6df752f7c345a3377b28e6711 ·
fingerprint 861ccc758dc6 · protocol benchmark84-v3

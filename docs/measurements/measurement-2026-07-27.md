# Measurement protocol 2026-07-27

**Environment:** Linux 6.6.87.2-microsoft-standard-WSL2 · x86_64 · 16 cores · 15.2 GB RAM · Python 3.12.3

**Repetitions per measurement:** 3 (the median is given)

### Loading

| File | Kind | Pages | Words | Median | per page | Budget |
|---|---|--:|--:|--:|--:|:--:|
| `artikel_cp1252.csv` | sheet | 1 | 30 | 1.6 ms | 1.6 ms | ✓ |
| `artikel_utf8.csv` | sheet | 1 | 25 | 0.4 ms | 0.4 ms | ✓ |
| `positionen.xlsx` | sheet | 3 | 38 | 2.5 ms | 0.8 ms | ✓ |
| `rechnung_din5008.pdf` | pdf | 1 | 100 | 14.4 ms | 14.4 ms | ✓ |
| `rechnung_mehrseitig.pdf` | pdf | 3 | 243 | 36.5 ms | 12.2 ms | ✓ |
| `rechnung_mehrseitig.tiff` | image | 2 | 0 | 71.5 ms | 35.8 ms | ✓ |
| `rechnung_scan_150dpi.png` | image | 1 | 0 | 10.6 ms | 10.6 ms | ✓ |
| `rechnung_scan_300dpi.png` | image | 1 | 0 | 49.3 ms | 49.3 ms | ✓ |
| `rotationen.pdf` | pdf | 4 | 16 | 4.0 ms | 1.0 ms | ✓ |

### Rendering

| File | Kind | Pages | Words | Median | per page | Budget |
|---|---|--:|--:|--:|--:|:--:|
| `rechnung_din5008.pdf (Rendern, 2×)` | render | 1 | 100 | 20.4 ms | 20.4 ms | ✓ |
| `rechnung_mehrseitig.pdf (Rendern, 2×)` | render | 1 | 243 | 18.8 ms | 18.8 ms | ✓ |
| `rotationen.pdf (Rendern, 2×)` | render | 1 | 16 | 14.5 ms | 14.5 ms | ✓ |

The file names are those of the synthetic corpus from `corpus/generate.py`;
the labels in the rendering table are quoted as the benchmark printed them.

> Measured on the development machine. The target profile is a laptop with 16 GB RAM and no GPU — slower values are to be expected there.

# Measurement report 2026-10-15

**Environment:** Linux 6.6.87.2-microsoft-standard-WSL2 · x86_64 · 16 cores · 15.6 GB RAM · Python 3.12.3

**Repetitions per measurement:** 5 (median shown)

### Reading

| File | Kind | Pages | Words | Median | per page | Budget |
|---|---|--:|--:|--:|--:|:--:|
| `artikel_cp1252.csv` | sheet | 1 | 30 | 1.7 ms | 1.7 ms | ✓ |
| `artikel_utf8.csv` | sheet | 1 | 25 | 0.2 ms | 0.2 ms | ✓ |
| `empty_workbook.xlsx` | sheet | 1 | 0 | 1.5 ms | 1.5 ms | ✓ |
| `positionen.xlsx` | sheet | 3 | 38 | 2.7 ms | 0.9 ms | ✓ |
| `rechnung_din5008.pdf` | pdf | 1 | 100 | 14.1 ms | 14.1 ms | ✓ |
| `rechnung_mehrseitig.pdf` | pdf | 3 | 243 | 35.2 ms | 11.7 ms | ✓ |
| `rechnung_mehrseitig.tiff` | image | 2 | 200 | 2161.0 ms | 1080.5 ms | ❌ |
| `rechnung_scan_150dpi.png` | image | 1 | 100 | 522.1 ms | 522.1 ms | ❌ |
| `rechnung_scan_300dpi.png` | image | 1 | 100 | 884.9 ms | 884.9 ms | ❌ |
| `rotationen.pdf` | pdf | 4 | 16 | 4.1 ms | 1.0 ms | ✓ |
| `transportschein-aok.pdf` | pdf | 2 | 382 | 4755.1 ms | 2377.5 ms | ❌ |

### Rendering

| File | Kind | Pages | Words | Median | per page | Budget |
|---|---|--:|--:|--:|--:|:--:|
| `rechnung_din5008.pdf (Rendern, 2×)` | render | 1 | 100 | 22.5 ms | 22.5 ms | ✓ |
| `rechnung_mehrseitig.pdf (Rendern, 2×)` | render | 1 | 243 | 20.3 ms | 20.3 ms | ✓ |
| `rotationen.pdf (Rendern, 2×)` | render | 1 | 16 | 15.9 ms | 15.9 ms | ✓ |
| `transportschein-aok.pdf (Rendern, 2×)` | render | 1 | 382 | 87.6 ms | 87.6 ms | ✓ |

> Measured on the development machine. The target is a 16 GB laptop without a GPU and may be slower.

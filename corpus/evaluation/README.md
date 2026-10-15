# Document extraction: evaluation corpus

Version 1 contains 84 synthetic PDF files (98 pages), six layout families and
nine annotated fields per document. All data is generated; no real customer
documents are included. Method and limits are described in
[v1/README.txt](v1/README.txt) (German).

## Measured results

Results are produced with the local runner described in
[Benchmark against the current code](#benchmark-against-the-current-code) and
stored as one directory per run under `reports/<date>/`, each with its own
`report.html`, CSV tables and predictions. The newest directory is the current
state. Each run is a regression on known data, not a blind test: the label
patterns of the invoice kind were tuned on this corpus.

## Loading

PDFs and preview images are stored in **Git LFS**. After cloning:

```sh
git lfs install --local
git lfs pull --include="corpus/evaluation/v1/**"
```

A checkout without LFS contains only pointers for these files. CI checks this
explicitly and fails on missing binaries. GitHub's source ZIP is no reliable
replacement for `git lfs pull`.

## Layout

| Path | Purpose |
| --- | --- |
| `v1/inputs/` | model inputs, separated by data set part; PDFs in LFS |
| `v1/ground_truth/expected.jsonl` | expected values, printed form and locations |
| `v1/manifest.json` | file paths, SHA-256, layout family and grouping |
| `v1/field-schema.json` | shared extraction schema |
| `v1/evaluate.py` | offline scoring of stored predictions |
| `v1/test_*.py` | tests for scoring, data integrity and separation |
| `v1/tools/generate.py` | deterministic generator with a fixed seed |
| `v1/index.html` | local overview with preview images |
| `tools/run_benchmark.py` | runs the current pipeline over all 84 PDFs and scores it |

The three parts hold 24 files for setup, 18 new documents of known layouts
and 42 documents of unknown layout families. Originals and scan variants stay
within the same part. Only `setup` may be used to adjust rules, templates and
prompts. Report results by layout family, variant and `group_id`; variants are
not independent documents.

The field names in `v1` (`belegnummer`, `belegdatum`, …) are German and stay
so: `v1` is frozen.

## Scoring

Create one JSONL file per method with `id`, `fields` and optionally
`review_fields` (format in `v1/README.txt`). Missing documents or field keys
count as errors. `null` is correct only when the expected value is absent.

```sh
python corpus/evaluation/v1/evaluate.py predictions.jsonl \
  --split unseen_layout --output scores.json
python -m unittest discover -s corpus/evaluation/v1 -p 'test_*.py' -v
```

By default the four core fields are scored: document number, document date,
total amount and VAT ID. Further fields can be chosen with `--fields`. Every
method compared must receive the same field set. Never pass expected values
to a model.

### Benchmark against the current code

`tools/run_benchmark.py` runs all 84 PDFs through the current local pipeline,
using the fields of a document kind from `sidecar/substrakt/document_kinds/`
(default `invoice`). It writes `predictions.jsonl`, scores it with
`v1/evaluate.py` and renders a report. Reference values are loaded only after
extraction. The tool is local only and makes no network calls.

From the repository root, after `git lfs pull` and with the sidecar
environment and Tesseract (`models/tessdata`) installed:

```sh
sidecar/.venv/bin/python corpus/evaluation/tools/run_benchmark.py
sidecar/.venv/bin/python corpus/evaluation/tools/run_benchmark.py --output /path/to/new-dir
sidecar/.venv/bin/python corpus/evaluation/tools/run_benchmark.py --verify corpus/evaluation/reports/<date>
```

The default output is `corpus/evaluation/reports/<date>/` with
`predictions.jsonl`, `results.json`, `summary.csv`, `fields.csv`,
`README.md` (the summary as Markdown, shown by GitHub in the directory
view), `report.html` (the same with filters, works offline) and a per-PDF
`cache/`. An interrupted run resumes from the cache; a directory holding a
run of a different source state is refused, so a changed pipeline always gets
a new directory. `--verify` re-scores the stored predictions independently;
`--render DIR` re-creates the report files from a stored `results.json`. `--limit N` processes only the first N PDFs as a
smoke test. On Windows, Tesseract runs inside WSL.

## Comparing with other methods

The application itself never calls a cloud service, and CI runs no paid model
tests. Other methods, including cloud services, can be compared by importing
their answers as files in the JSONL format above. Such a comparison records
model version, prompt, source state, run times and usage, and stores answers
outside the frozen corpus. Real documents and credentials must never be
committed.

## Reproducing and versioning

```sh
python -m venv .venv-evaluation
# activate the virtual environment, then:
python -m pip install -r corpus/evaluation/v1/tools/requirements-generation.txt
python corpus/evaluation/v1/tools/generate.py --output /path/to/new-folder
```

`v1` is a frozen test set: no expected values or documents are adjusted
after a model result. Extensions or other seeds get a new version. Package
versions of the original Windows/Python 3.12 run are recorded; byte identity
across operating systems and native libraries is not promised. For an exact
repetition, use the LFS files and their hashes, not a newly rendered
replacement.

The corpus covers neither real handwriting nor real camera perspectives and
does not replace a field test with released real documents.

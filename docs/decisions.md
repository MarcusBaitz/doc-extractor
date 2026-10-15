# Binding decisions

A condensed version of the four foundation documents, reduced to what matters
when building. If this file and an original disagree, the original wins; the
originals are internal and not published (see [README](README.md)).

## The two promises

**1. Nothing leaves the infrastructure.** No document content, no model
call, no telemetry. In case of doubt this promise beats every other
requirement, including convenience and accuracy. If a requirement collides
with it, locality wins, and the conflict is named explicitly instead of being
quietly built around.

**2. Fully permissive licences.** This applies to code *and* model weights
alike. An Apache-2.0 library that loads a CC-BY-NC model is a violation.
Enforced through [`licenses/policy.toml`](../licenses/policy.toml).

## Target profile

A standard laptop, 16 GB RAM, **no GPU**, Windows/macOS/Linux. A design
decision that requires a GPU is wrong. The development machine has an
RTX 5070 Ti; it must not leak into any assumption.

## Stack

| Layer | Decision |
|---|---|
| Desktop shell | Tauri v2 (Rust) |
| Frontend | React + TypeScript + Vite, Tailwind |
| Viewer | PDF.js v6 with a self-built overlay |
| Backend | Python sidecar (FastAPI), 127.0.0.1, random port, bearer token |
| Inference | OpenAI-compatible HTTP only, with `response_format: json_schema` |
| Local LLM | llama.cpp (llama-server), GGUF |
| Server LLM | vLLM on a GPU **in the customer network**: the same client, a different address |
| PDF | pypdfium2 (rendering) + pdfplumber (word bounding boxes) |
| Excel | openpyxl, python-calamine for large files |
| Images | Pillow + scikit-image |
| OCR | **Tesseract 5** (primary, measured); RapidOCR not adopted |
| Fast extraction | GLiNER2 (`fastino/gliner2-base-v1`) + regex |
| LLM model | `ibm-granite/granite-4.0-micro` |
| Embeddings | `intfloat/multilingual-e5-small` |
| Grounding | rapidfuzz over the word bounding-box index |
| Persistence | SQLite |
| Bundling | PyInstaller |
| Icons / font | Lucide (ISC), Inter (OFL 1.1) |

## Architecture rules

**Egress chokepoint.** Outbound traffic runs through *one* central function
in the Rust layer. No `fetch` in the frontend, no scattered `requests` calls.
Whatever does not pass through this chokepoint does not exist. A CI test
starts the app in a sandbox without a network route; any request in Air-gap
mode makes the test fail. That is the real safeguard of the core promise.

**Three operating modes, strictly separated.** Air-gap (default, 127.0.0.1
only), On-premise (additionally an administratively maintained allowlist,
including a vLLM server in the customer network), Cloud (only after explicit
unlocking). Settable through a machine-wide policy file that the user cannot
override. An inference server outside the customer network is not allowed in
any mode.

**Coordinates are always document coordinates**, never screen pixels.
Conversion happens only when rendering. Zoom, window scaling and retina
displays must never move stored highlights.

**No model name hard-coded.** Models come from the registry and are
swappable. Every entry needs repository, revision, SHA-256, licence and
licence URL; an entry without these is rejected at start-up.

**Never hard-wire a quantisation method.** GGUF locally,
compressed-tensors/AWQ on the server: a property of the registry entry, not
a code path.

**No PyTorch in the bundle.** All ML runs on ONNX Runtime or llama.cpp.

**No network access at runtime in standard operation.** No model downloads,
no telemetry, no crash reports, no font CDN, no update checks without
explicit approval. Models are loaded with `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1`.

## Provenance is a core function, not an extra

Constrained decoding guarantees the *form* of the output, not its *truth*. A
model can deliver perfectly structured, schema-conformant and arithmetically
consistent JSON with invented values; the documented case is an invoice
amount that wanders from 42.50 to 45.20.

Therefore: **every extracted value needs a location in the document.** If
none is found above the threshold, the field is marked as “unsupported” and
put up for manual review, never silently output.

This also applies to VLM output: its bounding boxes are documented as
unreliable and must **never be taken over directly as provenance**. They count
as a hint and are checked back against the word index through fuzzy
grounding like any other value.

## Stage 0, measured on 28 July 2026

The four open questions are answered. In full in
[`measurements/README.md`](measurements/README.md); three decisions changed
as a result:

**Tesseract is the primary engine, not RapidOCR.** More accurate (98.9%
against 90.5%), more robust and faster. Decisive: RapidOCR's confidence
reports 97–99% where 87–90% is correct, which makes it useless as a trigger
for escalating the reading stage. Tesseract's word confidence is fit for
that, with a threshold around 85% as a starting point.

**The reading stage stays two-tier.** The third tier (document VLM) is viable
locally (13.6 s per page at 150 dpi) but does not pay off for printed
documents: Tesseract is more accurate and twelve times faster than a 7B VLM
on a dedicated GPU. It stays planned as a swappable module but does not
become the standard escalation. Not measured and therefore open: handwriting,
forms without lines, nested tables.

**150 dpi instead of 300.** For both reading paths. At 300 dpi Tesseract is
slower without being more accurate, and the VLM runs into repetition loops.

**The server variant serves path B, not the reading stage.** It remains
right, but not because vision models become usable there; rather because free
field extraction becomes interactive. For vision models VRAM is the limit,
not compute.

**Provenance is necessary, as measured.** Constrained decoding works with
multimodal models: 10 of 10 answers were schema-conformant, but only 57% of
the values were correct. An extractor that trusts schema validation ships
43% wrong values without a warning sign.

All other performance figures in the foundation documents without an
explicit measurement remain estimates and are treated as such.

## Labelled document fields, 14 October 2026

The sample document fields use the extractor `document_field`. It assigns
values through German and English labels and their spatial neighbourhood: to
the right of the label or in the cell below. Other labels limit the search.
Value types are checked before a value is taken over; differing candidates
stay open. That way a delivery date does not replace a missing document date,
and the next column heading does not become the document number. Locations
still come from the words actually read.

Net amount, tax and document type complement the earlier sample fields. The
sender can be read from the letterhead before the recipient; this heuristic
assignment stays subject to review. Explicit regions, manual values and
custom regex configurations keep their precedence. Custom field definitions
already saved are not overwritten automatically; the new rules are loaded
through the updated sample fields.

Weak, sparse or shaded OCR pages get at most a second Tesseract run: local
thresholding and page segmentation mode 11. The image dimensions stay
identical; the second run replaces the first only if its summed word
confidence is higher. No field value is repaired using expected values,
dictionaries or calculations. The confidence sum is a heuristic, not a
guarantee of correct characters or signs.

The repeated 84-PDF run is a regression on a corpus that had already been
examined. The original split names are kept for comparability but no longer
count as a blind test after this error analysis. A new quality statement
needs fresh, independent documents.

## Document kinds as YAML files, 15 October 2026

Domain knowledge about a document kind lives in exactly one YAML file, not in
code. `sidecar/substrakt/document_kinds/invoice.yml` holds the values,
display names, data types, normalisation, required values, label patterns,
boundaries, legal forms and the titles by which an invoice and a credit note
are recognised. The core of parser, word index, label search, normalisation
and grounding reads this description and knows no document kind itself; the
fixed tables `LABELS`, `TITLES` and `COMPANY` and the sample fields in
`fields.py` are gone. A new document kind is a new file.

Bundled files live in the package, custom ones under
`<data dir>/document_kinds/`. A custom file with the same name replaces the
bundled one completely; nothing is merged. Files are validated on load with
Pydantic against `DocumentKind`; unknown keys, invalid patterns and a `name`
that differs from the file name are rejected. An error leaves the sidecar as
`problem+json` with the key `document-kind-invalid`, file name and position,
without document text. The JSON schema `document_kind.schema.json` is
generated from the model and serves editors; a test keeps it in sync. YAML
is read exclusively with `yaml.safe_load`.

At most one custom parser per document kind, and only when the core is not
enough: `parser: <name>` refers to a bundled module under
`sidecar/substrakt/document_kinds/parser/` with the function
`read(doc, field, kind) -> Assignment | None`. `None` hands back to the core.
A file in the user directory can choose a parser but cannot bring code. The
invoice needs no parser of its own.

A document kind names neither a model nor a quantisation method; both belong
in the registry from stage 3 and are rejected as unknown keys.

**Relation to SQLite.** YAML is the source for document kinds, that is, for
general knowledge about a kind of document. The templates created with the
assistant stay in SQLite: they are a user's field set with marked regions on
a sample document, not general knowledge about a document kind. A value taken
from a document kind carries its label rule in the existing JSON part
`locator_json`; the schema does not change, so there is no migration. Older
sets without a rule that only carry `extractor="document_field"` still get the
rule from the document kind that knows a value of that name. As long as the
recognition from stage 3 is missing, that is the default document kind
`invoice`; the core runs a custom parser only when a document kind is passed
to it explicitly.

The 84-PDF run from `corpus/evaluation` produced byte-identical predictions
and review flags before and after the switch: 315 of 336 core fields, 730 of
756 fields, zero wrong values without a review flag. All nine old anchor
patterns, the legal-form pattern and the title assignment compile from the
YAML file to the same regular expressions.

PyYAML has since been a direct runtime dependency of the sidecar (MIT, as is
the bundled libyaml) and was already in the lock file transitively before.

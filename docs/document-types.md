# Document types

Everything Substrakt knows about a kind of document lives in one YAML file,
not in code: which values it has, how they are labelled, which titles mark it
as an invoice or a credit note, which legal forms reveal a company name. The
core (parser, word index, label search, normalisation, grounding) reads this
description and is the same for every type. **A new document type is a new
file.**

Substrakt ships one kind, `invoice` (invoices and credit notes, labelled in
German or English), in
[`sidecar/substrakt/document_kinds/invoice.yml`](../sidecar/substrakt/document_kinds/invoice.yml).

## Where files are loaded from

| Location | Purpose |
|---|---|
| `sidecar/substrakt/document_kinds/*.yml` | shipped with the application |
| `<data dir>/document_kinds/*.yml` | your own kinds, see [Configuration](configuration.md#directories) |

A file of your own with the same name **replaces** the shipped one
completely; nothing is merged, so every type has exactly one version.

Files are read with `yaml.safe_load` and validated with Pydantic when loaded.
Unknown keys, invalid regular expressions and a `name` that differs from the
file name are rejected. The sidecar then answers with the error key
`document-kind-invalid`, the file name and the location of the error, never with
document text.

## Structure

```yaml
# yaml-language-server: $schema=document_kind.schema.json
name: invoice                  # equals the file name, [a-z][a-z0-9_]*
title: Rechnung                # name shown in the interface
description: Eingangs- und Ausgangsrechnungen sowie Gutschriften.

recognition:
  titles:                      # canonical value → printed titles
    Rechnung: [Rechnung, Invoice]
    Gutschrift: [Gutschrift, Credit note]

legal_forms: ['GmbH(?:\s*&\s*Co\.?\s*KG)?', 'AG', 'Ltd\.?']
boundaries: ['Lieferdatum', 'Due\s+date']

fields:
  - name: document_date        # becomes the JSON key
    label: Belegdatum          # shown to the user
    question: Wann wurde das Dokument ausgestellt?
    json_type: date
    label_rule:
      patterns: ['Belegdatum', 'Rechnungsdatum', 'Invoice\s+date']
      value: date
```

`document_kind.schema.json` next to the shipped file is generated from the model
and gives editors completion and validation. After a change to the model,
regenerate it with `document_kinds.write_schema()`;
`tests/sidecar/test_document_kinds.py` rejects an outdated schema.

### Fields (`fields`)

| Key | Meaning |
|---|---|
| `name` | JSON key of the value; a valid identifier |
| `label` | name in the interface |
| `question` | the question the value answers |
| `json_type` | `string`, `number`, `integer`, `date` or `boolean` |
| `required` | value is required |
| `extractor` | a built-in extractor such as `iban`, `bic`, `vat_id`, `date` |
| `normalization` | a built-in normaliser; by default chosen from `json_type` |
| `label_rule` | how the value is found next to its printed label (below) |

### Label rules (`label_rule`)

| Key | Meaning |
|---|---|
| `patterns` | labels as regular expressions, case-insensitive; a trailing colon is always allowed |
| `value` | `identifier`, `date`, `amount`, `code`, `vat_id`, `company` or `title` |
| `values` | allowed codes for `value: code`, e.g. `[EUR, USD, CHF, GBP]` |
| `unlabelled` | the value may also be found without a label |
| `skip_tax_rate` | skip a percentage printed before the amount |
| `letterhead_until` | look for an unlabelled company name above these labels |

## Custom parsers

When the core is not enough, a type may name at most one parser:
`parser: <name>` refers to a module shipped under
`sidecar/substrakt/document_kinds/parser/` with a function
`read(doc, field, kind)` that returns an assignment or `None`; `None`
hands the field back to the core.

A file in the user directory can **choose** a shipped parser but cannot bring
its own code. That keeps every type file reviewable as data.

## What does not belong in a type file

A document type names neither a model nor a quantisation method. Both belong
in the model registry planned for stage 3, and the schema rejects them like
any other unknown key.

## Measuring a change

Label patterns came from the 84-document evaluation run of 14 October 2026.
After changing them, run the 84-document evaluation again as described in
[`corpus/evaluation/README.md`](../corpus/evaluation/README.md) and compare
with the previous result. The corpus is no blind test any more: the patterns
were tuned on it.

# Plan: English sidecar, database and API contract

> Hand-over from the architect (Claude) to the implementation (Codex). The chat in which this plan was written does not exist for Codex: what is not written here does not exist.

**Stand:** 2026-10-15 · **Branch:** `codex/english-sidecar` · **Basis:** `designsprache-v2` · **Modell:** `gpt-5.6-sol` · **Aufwand:** high · **Prüfen:** `npm run check && export PATH="$HOME/.cargo/bin:$PATH" && cd src-tauri && cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test` · **Regeln:** `npm run lint && npm run egress` · **Vorbereiten:** `cd sidecar && uv sync --all-groups && cd .. && npm run korpus && mkdir -p models && cp -r /home/marcus/dev/doc-extractor/models/tessdata models/` · **Freigabe:** erteilt am 2026-10-15 · **Umgesetzt:** 2026-10-15

This is plan 1 of 3. It starts only after the local evaluation runner under `corpus/evaluation/tools/` is committed. Plan 2 (`english-shell.md`, Rust internals, scripts, CI) and plan 3 (`english-frontend.md`, frontend and `en.ts`) start only after this one is merged. All three share the glossary below word for word.

## Ziel

Rename everything in the Python sidecar, its tests, the database schema and the HTTP/Tauri contract to English, as if the project had been written in English from the start.

## Kontext

**Why.** The repository goes public. `docs/harness/08-writing.md` now requires English for identifiers, file names, database tables and columns, API and YAML keys, error keys, comments, docstrings, log messages, script output and test descriptions. German stays only for interface texts in `src/i18n/de.ts`, German sample content inside synthetic documents (a generated German invoice still prints „Rechnung“), and the frozen corpus `corpus/evaluation/`.

**Owner decision on the database (15 October 2026).** Rename columns and stored enum values **without** a new migration: rewrite `sidecar/substrakt/db/migrations/001_grundschema.sql` and `002_ausgabeform.sql` in place, renamed to `001_initial_schema.sql` and `002_output_format.sql`, so that they read as if they had always been English. There is no released version; development databases are deleted. Tests in `tests/sidecar/test_db.py` must still prove fresh setup, order and repetition. `docs/harness/02-sidecar.md`, section „Migrations“, records this one-off exception.

**Scope in files.**

- `sidecar/substrakt/**` (about 5,200 lines), `sidecar/pyproject.toml` (description, comments), `tests/sidecar/**` (about 2,900 lines incl. `fixtures/koordinaten.json`, which becomes `fixtures/coordinates.json`)
- `bench/**`, `corpus/generate.py`, `corpus/messkorpus.py`; `.gitignore` entries `corpus/mess/` and comments
- `corpus/evaluation/tools/**` (the local 84-document runner, outside the frozen data) and the section of `corpus/evaluation/README.md` that documents its call. The runner reads the field list from the document kind's YAML file and maps field names to the frozen German keys of `corpus/evaluation/v1/ground_truth/expected.jsonl` through one table, `CORPUS_KEYS` in `run_benchmark.py` (a field missing from the table is looked up under its own name). When the value names are renamed, change only the **keys** of `CORPUS_KEYS` to the new English names and keep the **values** German, e.g. `"document_number": "belegnummer"`. The full set: `document_number→belegnummer`, `document_date→belegdatum`, `total_amount→gesamtbetrag`, `net_amount→nettobetrag`, `tax_amount→steuerbetrag`, `currency→waehrung`, `vat_id→ust_idnr`, `document_kind→dokumentart`, `sender→absender`.
- The contract on the other side, because it must stay consistent in one commit: `src/api/types.ts`, `src/api/client.ts`, the route URLs and command names in `src-tauri/src/bridge.rs`, their registration in `src-tauri/src/lib.rs`, the error keys in `src/i18n/de.ts` (keys only, German texts stay), and every frontend place that reads a renamed property or calls a renamed client function. In the frontend change **only** what the typecheck needs; plan 3 renames the frontend itself.
- `tests/frontend/coords.test.ts` only for the fixture path.
- Documentation that names changed paths or identifiers: `docs/harness/01-architecture.md`, `02-sidecar.md`, `06-tests-and-gates.md`, `07-definition-of-done.md`, `docs/architecture/README.md`, `docs/development.md` (also remove the glossary rows that no longer apply and the sentence that names are German), `docs/document-types.md` (keys, file names, the German-keys note goes), `docs/configuration.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `AGENTS.md`.

**Current layout (German names to replace).**

```text
sidecar/substrakt/
  app.py config.py errors.py model.py store.py logging.py ...
  extraktion/  __init__.py beschriftungen.py extraktoren.py felder.py grounding.py normalisierung.py
  belegarten/  __init__.py rechnung.yml belegart.schema.json parser/__init__.py
  db/          migrate.py typen.py migrations/001_grundschema.sql migrations/002_ausgabeform.sql
  parsers/ index/
tests/sidecar/ test_belegarten.py test_beschriftete_felder.py test_felder.py test_feldzuordnung.py
               test_koordinaten.py test_manuell.py test_normalisierung.py test_api.py test_db.py ...
```

**HTTP routes today** (`sidecar/substrakt/app.py`): `/health`, `POST /documents`, `/documents/{doc_id}`, `/documents/{doc_id}/pages/{seite}/words`, `/documents/{doc_id}/datei`, `/documents/{doc_id}/text`, `/documents/{doc_id}/pages/{seite}/render`, `/documents/{doc_id}/sheets`, `/documents/{doc_id}/sheets/{index}/raster`, `POST /documents/{doc_id}/extrahieren`, `/beispielfelder`, `POST /documents/{doc_id}/export`, `/dokumenttypen`, `/dokumenttypen/{typ_id}`, `POST /shutdown`.

**Tauri commands today** (`src-tauri/src/lib.rs`, `invoke_handler`): `sidecar_status dokument_laden dokument_info dokument_bytes dokument_text dokument_schliessen seiten_woerter seite_rendern sheets sheet_raster extrahieren exportieren beispielfelder dokumenttypen dokumenttyp dokumenttyp_speichern dokumenttyp_loeschen`.

**Error keys today** (`sidecar/substrakt/errors.py`, resolved in `src/i18n/de.ts`): `belegart-unbekannt belegart-ungueltig datei-nicht-gefunden datei-zu-gross dokument-beschaedigt dokument-leer dokument-passwortgeschuetzt egress-verweigert format-nicht-unterstuetzt interner-fehler nicht-autorisiert pfad-nicht-erlaubt seite-nicht-vorhanden unbekanntes-dokument`. The problem+json member `schluessel` carries the key.

**Tables are already English** (`document_type`, `field_block`, `field`, `fingerprint`, `extraction_run`, `correction`, `export_profile`, `audit_log`, `app_setting`); German are many columns and the stored values of `document_type.ausgabe` (`'tabelle'`, `'datei'`).

**Test pattern.** `tests/sidecar/conftest.py` sets the environment at module level before `app.py` is imported; keep that. `test_api.py` uses the FastAPI TestClient; `test_db.py` builds databases in `tmp_path`.

## Glossary (shared by all three plans)

Use these names. Where a German name is not listed, translate it the same way: plain English, the domain meaning, snake_case in Python, SQL, YAML and JSON, camelCase/PascalCase in TypeScript, Rust conventions in Rust.

| German | English |
|---|---|
| Beleg | document |
| Belegart (YAML kind) | `DocumentKind`; package `document_kinds/`; error keys `document-kind-unknown`, `document-kind-invalid` |
| DokumentTyp (template stored in SQLite, „Vorlage“ in the UI) | `DocumentType` (table `document_type` stays) |
| Vorlage | template (UI word only) |
| Feld (field definition) | `FieldSpec` (not `Field`, which collides with `pydantic.Field`); module `fields.py` |
| Angabe | value (UI word only) |
| Lauf | `ExtractionRun` |
| Ergebnis | `ExtractionResult` |
| Zuordnung | `Assignment` |
| Fundstelle | `Evidence` |
| Treffer | `Match` |
| Beschriftung, Beschriftungsregel | label, `LabelRule`; module `labels.py` |
| Anker | `Anchor` |
| Rahmen | `LabelContext` |
| Erkennung | `Recognition` |
| Wertart values `kennung datum betrag code ustid firma titel` | `ValueKind` values `identifier date amount code vat_id company title` |
| Methode values `auto region regex extraktor` | `Method` values `auto region regex extractor` |
| JsonTyp | `JsonType` |
| Extraktion, extrahieren | extraction, `extract`; package `extraction/` |
| Extraktoren | `extractors.py` |
| Normalisierung | `normalization.py` |
| Seite, Seitentext | page, `PageText` |
| Wort, WortListe | word, `WordList` |
| Lesewurzeln | read roots |
| Nadelöhr | chokepoint |
| Modus | mode |
| Ausgabe(form) values `tabelle datei` | output (format) values `table file` |
| Korpus, Messkorpus | corpus, measurement corpus (`corpus/measurement_corpus.py`, output `corpus/measurement/`) |
| Ort / Orte | place / places (plan 3) |
| Sitzung | session (plan 3) |
| Assistent, Schritt | assistant, step (plan 3) |

**YAML and model keys of document kinds** (model in `document_kinds/__init__.py`, `labels.py`, `fields.py`; file `invoice.yml`, formerly `rechnung.yml`, `name: invoice`): `titel→title`, `beschreibung→description`, `erkennung→recognition` (`titel→titles`), `rechtsformen→legal_forms`, `grenzen→boundaries`, `felder→fields`, `label` stays, `frage→question`, `json_typ→json_type`, `pflicht→required`, `methode→method`, `regex` stays, `extraktor→extractor`, `normalisierung→normalization`, `regionen→regions`, `beschriftung→label_rule`, `muster→patterns`, `wert→value`, `werte→values`, `steuersatz_davor→skip_tax_rate`, `ohne_beschriftung→unlabelled`, `briefkopf_bis→letterhead_until`, `parser` stays. Schema file `document_kind.schema.json`, regenerated with the renamed `write_schema()`; the custom parser function `lese(doc, feld, belegart)` becomes `read(doc, field, kind)`.

**Value names of the invoice kind** (the `name:` of each entry in `invoice.yml`, which become JSON keys of results): `absender→sender`, `belegnummer→document_number`, `belegdatum→document_date`, `gesamtbetrag→total_amount`, `nettobetrag→net_amount`, `steuerbetrag→tax_amount`, `dokumentart→document_kind`, `waehrung→currency`, `ust_idnr→vat_id`, `iban` stays. Their `label:` and `question:` texts stay German, because they are shown to German users. The extractor registry keys in `extractors.py` follow the same words (`ustid→vat_id`, `datum→date`, `betrag→amount`, `prozent→percent`, `steuernummer→tax_number`, `zahlungsziel→payment_terms`, `plz_ort→postcode_city`; `iban`, `bic` stay), including the German alias names in the lookup table (`rechnungsdatum` and similar stay as recognised aliases, because they are user input).

**Columns** (both migrations): `dateiname→file_name`, `beispiel_datei→sample_file`, `beschreibung→description`, `frage→question`, `json_typ→json_type`, `pflicht→required`, `sortierung→sort_order`, `erstellt_am→created_at`, `geaendert_am→updated_at`, `ergebnis→result`, `ergebnis_json→result_json`, `feld_name→field_name`, `wert_alt→old_value`, `wert_neu→new_value`, `zeitpunkt→occurred_at`, `aktion→action`, `ziel→target`, `ziel_json→target_json`, `modus→mode`, `quelle→source`, `modell→model`, `namensschema→naming_scheme`, `normalisierung→normalization`, `extraktor→extractor`, `dauer_ms→duration_ms`, `ist_array→is_array`, `ausgabe→output` with `CHECK (output IN ('table', 'file'))` and default `'table'`. Columns already English stay.

**Routes**: `{seite}→{page}`, `/datei→/file`, `/extrahieren→/extract`, `/beispielfelder→/sample-fields`, `/dokumenttypen→/document-types`, `{typ_id}→{type_id}`; the others stay.

**Tauri commands**: `sidecar_status`, `load_document`, `document_info`, `document_bytes`, `document_text`, `close_document`, `page_words`, `render_page`, `sheets`, `sheet_raster`, `extract`, `export`, `sample_fields`, `document_types`, `document_type`, `save_document_type`, `delete_document_type`.

**Error keys**: `document-kind-unknown`, `document-kind-invalid`, `file-not-found`, `file-too-large`, `document-corrupt`, `document-empty`, `document-password-protected`, `egress-denied`, `format-not-supported`, `internal-error`, `not-authorized`, `path-not-allowed`, `page-not-found`, `unknown-document`; problem+json member `schluessel→key`. Exception classes follow (`DateiNichtGefunden→FileNotFound`, `DokumentBeschaedigt→DocumentCorrupt`, …).

## Schritte

1. **Database.** Rename and rewrite both migration files with the English columns and values, header comments in English. Rename `db/typen.py` to `db/models.py` and translate its models, `migrate.py` functions (`migriere→migrate`, `oeffne→open_database`, `aktuelle_version→current_version`) and comments. Translate `tests/sidecar/test_db.py`. Expected: the db tests pass on a fresh database.
2. **Extraction core and document kinds.** `extraktion/` becomes `extraction/` with `labels.py`, `extractors.py`, `fields.py`, `grounding.py`, `normalization.py`; `belegarten/` becomes `document_kinds/` with `invoice.yml` and the YAML keys and value names above; regenerate `document_kind.schema.json` with `write_schema()`. Translate all identifiers, docstrings and comments. Rename and translate the matching tests (`test_document_kinds.py`, `test_labelled_values.py`, `test_fields.py`, `test_value_assignment.py`, `test_manual_values.py`, `test_normalization.py`). Expected: these tests pass, including the stale-schema check.
3. **App, errors, model, parsers, store, config.** Routes, response models, error classes and keys, log and error message texts, `model.py`, `store.py`, `parsers/`, `index/`, `config.py` (only names and comments; the environment variable names stay for plan 2). Translate `test_api.py`, `test_koordinaten.py` (→ `test_coordinates.py`, fixture → `fixtures/coordinates.json`, update `tests/frontend/coords.test.ts` path) and the remaining sidecar tests. Expected: `npm run test:sidecar` green, Ruff clean (`cd sidecar && uv run ruff check . ../tests/sidecar ../bench ../corpus/generate.py ../corpus/measurement_corpus.py`).
4. **Contract to the frontend.** Update `src/api/types.ts`, `src/api/client.ts` (function names follow the command names, e.g. `api.loadDocument`), route URLs and command names in `src-tauri/src/bridge.rs` and the `invoke_handler` list in `src-tauri/src/lib.rs`, error keys in `src/i18n/de.ts`, and the frontend call sites until `npm run typecheck`, `npm run lint` and `npm run test` pass. No other frontend renaming.
5. **Bench, corpus generators and evaluation runner.** Update `corpus/evaluation/tools/run_benchmark.py` to the renamed modules (today it imports `substrakt.belegarten.lade` and calls `substrakt.extraktion.felder.extrahiere(…, belegart=…)`; its `--kind` default `rechnung` becomes `invoice`, its help texts and docstring become English, and the docstring sentence pointing to a historical Mistral comparison in `corpus/evaluation/README.md` is deleted, because the README no longer describes it) and add the key mapping from the scope section; then run it on the full corpus outside the sandbox if possible: `sidecar/.venv/bin/python corpus/evaluation/tools/run_benchmark.py --output /tmp/english-sidecar-benchmark`. The result before the rename is 315/336 core fields, 730/756 fields, 0 wrong values without a review flag; the rename must reproduce exactly these numbers. If the full run cannot execute in the sandbox, run `--limit 5` and report that the full run is open.
   Then: Translate `bench/**`, `corpus/generate.py`, rename `corpus/messkorpus.py` to `corpus/measurement_corpus.py` with output `corpus/measurement/` (update `.gitignore`, `bench/ocr.py`, `sidecar/substrakt/parsers/ocr.py` references). Synthetic document content stays German where it imitates German documents; the generated file names may stay as they are if tests depend on them. Expected: `npm run korpus` still produces the corpus the tests use.
6. **Documentation.** Update the files listed under scope so that every path, identifier, route, command and key they name exists. Expected: `grep -rn "extraktion/\|belegarten\|typen.py\|rechnung.yml\|schluessel\|beispielfelder\|dokumenttypen" -- docs/*.md docs/harness docs/architecture README.md CONTRIBUTING.md CLAUDE.md AGENTS.md` finds nothing.

## Nicht anfassen

- `corpus/evaluation/**` except `tools/` and the runner section of its README: frozen data and reports, checked by checksums in CI. Its German field names stay.
- `docs/entscheidungen.md`, `docs/stand.md`, `docs/design/**`, `docs/messungen/**`, `docs/plans/**`, `docs/release-readiness.md`, `CHANGELOG.md`: the architect translates or maintains them.
- Rust identifiers, Rust log texts, `policy.rs`, `egress.rs`, `sidecar.rs`, environment variable names (`SUBSTRAKT_*`), `scripts/**`, `package.json` script names, `.github/workflows/**`: plan 2.
- Frontend file names, component names, local identifiers, `src/i18n/de.ts` texts: plan 3. Only what step 4 requires.
- German interface texts, and German `label:`/`question:` texts in `invoice.yml`.
- No new dependency. No new migration file beyond the two rewritten ones. No change of behaviour: same endpoints, same results, same defaults; Air-gap stays the default.
- The writing rules in `docs/harness/08-writing.md` (checked by **Regeln:**). No adaptation of code to the sandbox: an `EPERM`, a read-only `.git` or a missing `uv`/`cargo` is a finding, not a reason to change code.
- Do not write into „Befunde der Abnahme“.

## Fertig, wenn

The **Prüfen** command is green, and `git grep -nIiE "\b(beleg|belegart|dokument|feld|felder|lauf|ergebnis|fundstelle|beschriftung|zuordnung|extraktion|seite|wurzel|schluessel|speicher|lade|liefert|wenn|nicht|und|oder)\b" -- sidecar tests/sidecar bench corpus/generate.py corpus/measurement_corpus.py` shows only German sample document content, German `label:`/`question:` texts and German user-input aliases.

## Befunde der Abnahme

Reviewed by the architect on 2026-10-15.

1. **German interface texts held type names.** `src/i18n/de.ts` expected: German values unchanged. Actual: a blind replacement of `Ergebnis` and `Feld` had turned six values into „So sieht das ExtractionResult aus“, „ExtractionResult sichern“ and similar; the word gate did not catch it because neither type name is on its list. Decision: fixed by the architect; all six values are byte-identical to the base again. The same replacement had reached German comments in `src/` (`das ExtractionResult`, `ein FieldSpec`) and the label of the word-gate entry `Feld statt Angabe` in `tests/frontend/orte.test.tsx`; restored as well. Lesson for plans 2 and 3: say explicitly that identifier renames never apply inside German strings or comments.
2. **Skip message in `tests/sidecar/test_coordinates.py`** read „ExtractionRun wiederholen“. Decision: replaced by an English sentence.
3. **Frontend files outside the plan** (`src/App.tsx`, `src/orte/**`, `src/zustand/sitzung.ts`, `src/ergebnis/sichern.ts`, `tests/frontend/*`) changed only to follow the renamed API types and client methods. Decision: accepted; plan 3 renames the rest.
4. **Bridge error keys** are English (`sidecar-unreachable`, `response-unreadable`, …), and `bridge.rs` now reads the problem's `key` field with the `type` URI as fallback. All 14 sidecar error keys and the bridge keys have an entry in `de.ts`. Decision: accepted.
5. **Sidecar error titles** are English now. The interface shows them only for a key missing from `de.ts`; there is none. Decision: accepted.
6. **Remaining German** in the plan's grep: `invoice.yml` labels, questions and description, and the printed page texts in `corpus/generate.py`. Both are German sample content. `docs/entscheidungen.md` still names `belegarten/rechnung.yml`; it is translated after plan 3. Decision: accepted.
7. **Migrations:** only `001_initial_schema.sql` and `002_output_format.sql`; `output` holds `'table'`/`'file'`. Defaults unchanged. Decision: accepted.

Runs by the architect in the worktree: `npm run check` green (71 TypeScript tests; 280 Python tests passed, 2 skipped because the fresh corpus has no transport form), `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` and `cargo test` green (8 tests). Full benchmark over 84 PDFs: core 315/336 (93,75 %), all 730/756 (96,56 %), 0 wrong values without review flag, identical to the bar.

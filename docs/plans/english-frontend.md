# Plan: English frontend code, English interface and a language switch

> Hand-over from the architect (Claude) to the implementation (Codex). The chat in which this plan was written does not exist for Codex: what is not written here does not exist.

**Stand:** 2026-10-15 · **Branch:** `codex/english-frontend` · **Basis:** `designsprache-v2` · **Modell:** `gpt-5.6-sol` · **Aufwand:** high · **Prüfen:** `npm run check && export PATH="$HOME/.cargo/bin:$PATH" && cd src-tauri && cargo test` · **Regeln:** `npm run lint && npm run egress` · **Vorbereiten:** `cd sidecar && uv sync --all-groups && cd .. && npm run corpus && mkdir -p models && cp -r /home/marcus/dev/doc-extractor/models/tessdata models/` · **Freigabe:** erteilt am 2026-10-15 · **Umgesetzt:** 2026-10-15

This is plan 3 of 3. It starts after plans 1 (`english-sidecar.md`) and 2 (`english-shell.md`) are merged. The glossary in `english-sidecar.md`, section „Glossary“, applies here unchanged; read it first.

## Ziel

Rename the React frontend and its tests to English and add an English interface with a language switch, while German stays the default.

## Kontext

**Why.** `docs/harness/08-writing.md` requires English for identifiers, file names, comments and test descriptions. Users are German clerks, so the German interface stays the default; an English interface makes the public project usable for others. Plan 1 already renamed the API contract (`src/api/types.ts`, `src/api/client.ts`) and the error keys; plan 2 renamed scripts and tooling.

**Files to rename** (about 5,600 lines in `src/`, plus `tests/frontend/`):

| Today | Becomes |
|---|---|
| `src/orte/` | `src/places/` |
| `Uebersicht.tsx`, `Pruefen.tsx`, `Vorlagen.tsx`, `Vorlagenansicht.tsx`, `Einstellungen.tsx`, `Assistent.tsx` | `Overview.tsx`, `Review.tsx`, `Templates.tsx`, `TemplateView.tsx`, `Settings.tsx`, `Assistant.tsx` |
| `src/orte/assistent/SchrittMusterbeleg.tsx`, `SchrittAngaben.tsx`, `SchrittErgebnis.tsx`, `SchrittAbschluss.tsx`, `schluessel.ts` | `src/places/assistant/StepSampleDocument.tsx`, `StepValues.tsx`, `StepResult.tsx`, `StepFinish.tsx`, `keys.ts` |
| `src/zustand/sitzung.ts` (`useSitzung`, `Sitzung`) | `src/state/session.ts` (`useSession`, `Session`) |
| `src/ergebnis/sichern.ts` (`sichern`) | `src/results/save.ts` (`saveResult`) |
| `src/shell/Seitenleiste.tsx` | `src/shell/Sidebar.tsx` |
| `src/ui/bausteine.tsx` (`Knopf`, `Karte`, `Titel`, `Hinweis`, `Flaeche`, `Marke`, `Punkt`, `Taste`, `Textfeld`, `Textlink`, `Suchfeld`, `Leer`, `Kopf`, `Blockueberschrift`) | `src/ui/components.tsx` (`Button`, `Card`, `Title`, `Notice`, `Surface`, `Badge`, `Dot`, `Key`, `TextInput`, `TextLink`, `SearchInput`, `Empty`, `Header`, `SectionHeading`) |
| `src/ui/format.ts` (`datumLang`, `uhrzeit`, `zeitspanne`, `formatZahl`, …) | same file, English names (`longDate`, `timeOfDay`, `duration`, `formatNumber`, …) |
| `src/design/theme.ts` (`gespeichertesTheme`, `themeAnwenden`, key `SCHLUESSEL = 'substrakt.theme'`) | `storedTheme`, `applyTheme`, constant `STORAGE_KEY`; the stored key value `'substrakt.theme'` stays |
| `src/i18n/de.ts` (`texte`, `fehlerText`, `formatBytes`, `formatZahl`) | `src/i18n/de.ts` (`de`), `src/i18n/en.ts` (`en`), `src/i18n/index.ts` (see below) |
| `tests/frontend/orte.test.tsx` | `tests/frontend/places.test.tsx` |

Other German identifiers (`Ort`, `Ansicht`, `Belegakte`, `Belegzustand`, `Markierung`, `SeitenMasse`, `Schilder`, `Ton`, `begrenzeAufSeite`, `rechteckAusPunkten`, `seitenGroesseAufSchirm`, `klarname`, `offeneAngaben`, `freierSchluessel`, `schluesselAus`, `spaltenName`, `vereinige`, `alsTabelle`, `istBridgeFehler`, …) follow the glossary. `src/viewer/coords.ts` keeps its exported names `docToScreen`, `screenToDoc`; its formulas do not change.

**Text keys.** The keys of the dictionary become English (`texte.einstellungen.hellDazu` → `texts.settings.lightDetail`, `texte.orte` → `places`, `uebersicht` → `overview`, `pruefen` → `review`, `vorlagen` → `templates`, `assistent` → `assistant`, `einstellungen` → `settings`, `beleg` → `document`, `markierung` → `highlight`, `betriebsart` → `mode`, `fehler` → `errors`). The German **values** stay exactly as they are.

**Language switch, fixed design.**

```ts
// src/i18n/index.ts
export type Language = 'de' | 'en'
export type Texts = typeof de          // en.ts is typed `export const en: Texts`, so a missing key fails the typecheck
export const LANGUAGES: Language[] = ['de', 'en']
export function storedLanguage(): Language          // localStorage key 'substrakt.language'; anything else or an exception → 'de'
export function applyLanguage(language: Language): void  // sets document.documentElement.lang and stores it; storage errors are ignored
export function LanguageProvider(props: { children: ReactNode }): JSX.Element
export function useTexts(): Texts
export function useLanguage(): [Language, (language: Language) => void]
export function errorText(texts: Texts, key: string, fallback: string): string
```

Follow the pattern of `src/design/theme.ts` for storage. Components read texts through `useTexts()` instead of importing the dictionary. `App.tsx` wraps everything in `LanguageProvider`. Settings get a block „Sprache“ / “Language” with two options in exactly the style of the existing light/dark choice (the same component, not a dark button, because each screen keeps exactly one dark button). The `lang` attribute in `index.html` stays `de`.

**English interface vocabulary** (British spelling, header comment of `en.ts` holds this table like `de.ts` does):

| German screen word | English screen word |
|---|---|
| Übersicht, Prüfen, Vorlagen, Einstellungen | Overview, Review, Templates, Settings |
| Beleg | document |
| Vorlage | template |
| Angabe | detail |
| sicher erkannt | recognised |
| nicht eindeutig | unclear |
| wartet auf Prüfung | waiting for review |
| abgelegt | filed |
| Alle Belege bleiben auf diesem Gerät. | All documents stay on this device. |

Write the English texts as plain, short sentences for clerks, mirroring the German ones in meaning, not word by word.

**Word gate for both languages** (`tests/frontend/places.test.tsx`). Today `VERBOTEN` holds the German list and every place is rendered once. Afterwards every place is rendered once per language, and:

- `FORBIDDEN_DE`: the current list unchanged (Konfidenz, Locator, Provenance, Bounding-Box, OCR, Dokumenttyp, Template, Feld, Dokument, Extraktion, Regex, the model names GLiNER, Granite, Tesseract, Q4_K_M, rapidfuzz, snake_case keys).
- `FORBIDDEN_EN`: confidence, locator, provenance, bounding box, OCR, document type, extraction, regex, field, threshold, the same model names, snake_case keys.
- In English, the rendered text contains no `ä`, `ö`, `ü` or `ß`; that catches a forgotten German text.
- The one-dark-button check runs in both languages.

Negative proof, required by `docs/harness/06-tests-and-gates.md`: put „Konfidenz“ into one German text and “confidence” into one English text, run the test, see each fail, revert. Report both runs; do not commit them.

The test mocks `pdfjs-dist` at the top of the file because PDF.js needs `DOMMatrix`; keep that.

## Schritte

1. **i18n.** Create `src/i18n/index.ts` as specified, rename keys in `de.ts`, translate its comments, create `en.ts` with every key. Expected: `npm run typecheck` fails until step 2 replaces the imports, then passes.
2. **Components and files.** Rename the files and identifiers in the table, switch all components to `useTexts()`, wrap `App.tsx` in `LanguageProvider`, translate all comments. Expected: `npm run typecheck`, `npm run lint` green.
3. **Language choice in Settings.** Add the „Sprache“ / “Language” block using the existing choice component and `useLanguage()`. Expected: switching changes every place without reload, survives a restart, and an unknown stored value falls back to German.
4. **Tests.** Rename and translate `tests/frontend/places.test.tsx` and `coords.test.ts`, add both forbidden lists, the umlaut check, a test for `storedLanguage()` fallback, and run the negative proof. Expected: `npm run test` green with more tests than the 71 before.
5. **Documentation.** `docs/harness/03-frontend.md` (paths, both word lists, the switch exists now), `docs/harness/01-architecture.md` directory map, `docs/harness/06-tests-and-gates.md` and `07-definition-of-done.md` (test file name, every text in both dictionaries), `docs/development.md`, `docs/getting-started.md` (the interface can be switched to English in Settings), `README.md` (remove “The interface is in German”, say German by default with English available), `CONTRIBUTING.md`, `CLAUDE.md`, `AGENTS.md`. Expected: `grep -rn "orte/\|orte.test\|zustand/\|ergebnis/\|bausteine\|Seitenleiste" -- README.md CONTRIBUTING.md CLAUDE.md AGENTS.md docs/*.md docs/harness` finds nothing.

## Nicht anfassen

- Colour tokens and `src/design/tokens.css` values; no new colour, no Tailwind default colour name.
- `src/viewer/coords.ts` formulas and `tests/sidecar/fixtures/coordinates.json`.
- The German texts' wording, the API contract, `src/api/client.ts` (only its comments), `src-tauri/**`, `sidecar/**`, `scripts/**`.
- `corpus/evaluation/**`, `docs/entscheidungen.md`, `docs/stand.md`, `docs/design/**`, `docs/messungen/**`, `docs/plans/**`, `docs/release-readiness.md`, `CHANGELOG.md`.
- No new dependency: no i18n library, React context is enough. No network path (`fetch` and friends stay forbidden). German stays the default.
- The writing rules in `docs/harness/08-writing.md`. No adaptation of code to the sandbox: an `EPERM` or a read-only `.git` is a finding, not a reason to change code.
- Renaming an identifier is not a search-and-replace of a word. In plan 1 a blind replacement turned German interface texts into „So sieht das ExtractionResult aus“. Never replace a word inside a string or comment because an identifier of that name was renamed; translate prose as prose.
- Check before finishing: in `git diff src/i18n/de.ts`, every changed line of a value must be a key rename only; the German value text stays byte for byte.
- Do not write into „Befunde der Abnahme“.

## Fertig, wenn

The **Prüfen** command is green, both negative proofs are reported, and `git grep -nIE "\b(texte|ort|orte|beleg|vorlage|angabe|sitzung|zustand|schritt|knopf|karte|fehler|laden|speichern)\b" -- src tests/frontend ':!src/i18n/de.ts'` shows nothing outside German string literals.

## Befunde der Abnahme

Reviewed by the architect on 2026-10-15.

1. **German texts unchanged.** All string literals of `src/i18n/de.ts` before and after were compared with the TypeScript parser: no German wording changed. Removed are only the unit and separator literals of the number helpers, which moved to `src/ui/format.ts` (now `de-DE` or `en-GB` by language). Added are the language block and texts that used to sit in JSX (`Uhr gelesen`, `Speicherort`, relative times, `Texterkennung`). Decision: accepted; the moved texts close an old breach of the dictionary rule.
2. **Language switch** in `src/i18n/index.ts` matches the specified signatures; `storedLanguage()` falls back to German for unknown values and unavailable storage, both tested. `index.html` keeps `lang="de"`. No new dependency.
3. **Word gate** renders every place in both languages, with `FORBIDDEN_DE` unchanged, `FORBIDDEN_EN` as specified, the umlaut check for English and the one-dark-button check per language. Codex reported both negative runs: „Konfidenz“ in a German text and “confidence” in an English text each failed exactly the matching test with exit 1 and were reverted.
4. **`docs/gates.md`** was changed although not listed in step 5; it names the renamed test file. Decision: accepted.
5. **Sandbox:** Codex could not finish `npm run check` because the FastAPI `TestClient` hangs in its sandbox, as in plan 2. Not a code issue.

Runs by the architect in the worktree: `npm run check` green (80 TypeScript tests, up from 71; 280 Python tests passed, 2 skipped because the fresh corpus has no transport form; licence and egress gates green), `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` and `cargo test` green (8 tests). Plan grep and documentation grep from „Fertig, wenn“ and step 5 find nothing.

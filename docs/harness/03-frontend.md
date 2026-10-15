# Frontend

Status: 2026-10-15

This file applies to changes under `src/` and to Substrakt's visible
language. It derives its rules from `docs/design/design-language.md` and names
the colour, word, egress and coordinate gates that enforce them.

## Four places and one path

The interface has exactly four places:

| Place | The user's question |
|---|---|
| Übersicht (Overview) | Is everything running? Do I need to do anything? |
| Prüfen (Review) | These documents were not unambiguous. |
| Vorlagen (Templates) | Which kinds of documents does the program know? |
| Einstellungen (Settings) | Behaviour, privacy, technical details |

The setup assistant is not a fifth place. It is a path that starts from
„Vorlagen → Neue Vorlage“ and leads back into everyday use after sample
document, values, result and completion. `src/App.tsx` switches the places;
`src/places/` contains their pages and the assistant's steps.

Each screen has exactly one dark button. It shows the obvious next step;
further dark areas would compete with it for attention.
`tests/frontend/places.test.tsx` renders every place in both languages and
rejects a second `button` with `bg-ink`.

## Texts and word list

Interface texts live exclusively in `src/i18n/de.ts` and `src/i18n/en.ts`,
never directly in JSX. Components read the active dictionary through
`src/i18n/index.ts`; the English dictionary is typed against the German one,
so a missing key fails typecheck. German is the default interface language.
The language choice in Settings changes every place without a reload and is
stored under `substrakt.language`; an invalid or unreadable value falls back
to German.

| On screen | In the engine room |
|---|---|
| Vorlage | Dokumenttyp, Template |
| Angabe | Feld |
| Beleg | Dokument |
| sicher erkannt | confidence ≥ threshold |
| nicht eindeutig | confidence below threshold |
| wartet auf Prüfung | review queue |
| abgelegt | exported |
| Alle Belege bleiben auf diesem Gerät | Air-gap mode |

The word gate in `tests/frontend/places.test.tsx` checks the rendered markup
of all four places. `FORBIDDEN_DE` rejects:

- Konfidenz
- Locator
- Provenance
- Bounding-Box
- OCR
- Dokumenttyp
- Template
- Feld instead of Angabe
- Dokument instead of Beleg
- Extraktion
- Regex
- model names: GLiNER, Granite, Tesseract, Q4_K_M or rapidfuzz
- keys in snake_case

`FORBIDDEN_EN` rejects:

- confidence
- locator
- provenance
- bounding box
- OCR
- document type
- extraction
- regex
- field
- threshold
- model names: GLiNER, Granite, Tesseract, Q4_K_M or rapidfuzz
- keys in snake_case

The English render must also contain no `ä`, `ö`, `ü` or `ß`; this catches a
German text whose key exists but whose value was not translated.

The engine room nevertheless remains reachable: confidence as a number, model
names, technical keys, paths and reading stages belong exclusively under
„Einstellungen → Technische Details“. In daily work a clerk decides about a
value, not about the technology that produced it.

## Colours

Colour values live exclusively in `src/design/tokens.css`. Components use
semantic Tailwind names such as `bg-card`, `text-ink-2`, `border-line`,
`text-good` and `bg-warn-bg`; that way light and dark theme work from the
same meaning.

The surface and text tokens are `bg`, `panel`, `card`, `card-2`, `line`,
`ink`, `ink-2` and `ink-3`. Only `accent`, `good`, `warn` and `bad` carry
meaning, together with their background variants. A new colour therefore
first needs a justified token for both themes, not a value in a component.

The colour gate in `eslint.config.js` rejects Tailwind default colour names
such as `bg-slate-800`, `text-red-500` or `border-blue-300` in `src/`. It
prevents an unnamed additional surface that only fits one theme.

## Process and coordinate boundaries

The frontend calls the backend only through `src/api/client.ts` with Tauri
`invoke`. `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`,
`navigator.sendBeacon`, `axios` and `@tauri-apps/plugin-http` are rejected by
the ESLint egress gate; `scripts/check-egress.sh` additionally protects
against disabled lint rules.

Viewer rectangles stay in document coordinates. Conversion for zoom, rotation
and pixel ratio happens only in `src/viewer/coords.ts`, because the
coordinate gate checks this place against the same fixture as the PDF parser.

PDF.js accesses `DOMMatrix` already on import, which Node does not provide.
Interface tests therefore mock `pdfjs-dist` as at the top of
`tests/frontend/places.test.tsx`; they check language and structure, not the
drawing of a PDF page.

## TypeScript conventions

Types are introduced with `import type` or an inline type import. The ESLint
gate `consistent-type-imports` keeps runtime imports free of pure types and
makes the module boundary visible.

Unused variables and arguments are errors. A deliberately unused value has a
`_` prefix; exactly this exception is configured in `eslint.config.js`.
Disabling a lint rule in source needs a domain reason and must not bypass any
product gate.

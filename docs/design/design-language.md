# Design language: Substrakt

> **Use:** This chapter complements the build prompt and went to the coding environment together with it. Reference prototype: [`substrakt-design-v2.html`](substrakt-design-v2.html); all tokens are in its CSS header.
>
> *Version 2: replaces the first draft completely. Why is explained under “What changed compared with the first draft”.*

The interface is German by default; an English interface can be chosen under „Einstellungen → Sprache“ (Settings → Language). German interface words below are quoted as they appear on screen, with the English counterpart from `src/i18n/en.ts` in parentheses where it helps.

---

## Guiding idea

**It runs, and you can see it.**

Substrakt has two lives, and only one of them is everyday work:

*Set up once.* The user opens a typical document, draws frames with the mouse around the places of interest, and says each time what is there. This produces a template. Then the user decides what should come out at the end and which folder is watched. This happens exactly once per sender.

*Then it runs.* Documents land in the folder, the program recognises the template, reads out the details and files the result. Nobody opens the application for that. The user's everyday work is: **do nothing and see that it runs**, and occasionally click away three doubtful cases.

Three decisions follow from this and carry everything else:

1. **The pipeline is at the centre, not the workbench.** The first screen answers a single question: *Is it running, and do I need to do anything?* The workbench is not a place to live in, but the setup step and the place for corrections.
2. **The engine room stays closed.** The user is a clerk, not a developer. They see „Rechnungsnummer“ (invoice number), not `invoice_number: string`. They see „sicher erkannt“ (recognised), not `0.91`. They never see a model, a reading stage or an extraction path. All of it still exists, under „Einstellungen → Technische Details“ (Settings → Technical details), where only those who look for it find it.
3. **One screen, one obvious action.** Each screen has exactly one dark button. Everything else is light, calm and of equal rank. Whoever does not know what to do presses the dark one.

The style frame: light paper grey, white cards, hairlines, plenty of empty space, very little colour. Calm comes not from leaving out function but from leaving out emphasis.

---

## The four places

There are no more. The sidebar carries **words instead of symbols**: for a non-technical user „Vorlagen“ (Templates) is unambiguous, an icon never is.

| Place | Answers | How often visited |
|---|---|---|
| **Übersicht** (Overview) | Is everything running? Do I need to do anything? | daily, for seconds |
| **Prüfen** (Review) | These documents were not unambiguous. | daily, for minutes |
| **Vorlagen** (Templates) | Which kinds of documents does the program know? | weekly |
| **Einstellungen** (Settings) | Behaviour, privacy, technology | rarely |

The **setup assistant** is not a place of its own, but a path that starts from „Vorlagen → Neue Vorlage“ (Templates → New template) and ends back in the overview. The pages are in `src/places/`, the assistant's steps in `src/places/assistant/`.

### Overview

From top to bottom: status line („Alles läuft“ / “Everything is running”, green dot, when last read) → three numbers (documents this month · **waiting for your review** · errors in 30 days) → watched folders with the day's count → the most recently processed documents.

Only *one* of the three numbers is coloured: the one that calls for an action. It is the only tile with a sand tone and the dark button „Jetzt prüfen“ (Review now). When the review list is empty, the colouring disappears; then the whole screen is grey on grey, and that is the desired normal state.

### Review

A queue, one document after the other, **only ever one question visible**:

- On the left the document, the questionable place highlighted.
- On the right: what it is about („Zahlungsbedingungen“, payment terms), the value found **large and easy to read**, one sentence on why the question is asked („Im Beleg steht die Angabe diesmal in einem Satz statt in der gewohnten Zeile“: this time the detail is in a sentence rather than in the usual line) and two buttons: **„Stimmt so“** (Looks right, Enter) · „Ändern“ (Change).
- Below, deliberately quiet: „Alles Übrige wurde sicher erkannt“ (Everything else was recognised) with the other values and check marks. This removes the worry that more is lurking behind the one doubtful case.
- A third way as a text link, not as a button: „Diese Angabe fehlt im Beleg“ (This detail is missing from the document).

The counter in the sidebar counts down on confirmation and disappears at zero. This small movement is the only reward the application expresses: no success message, no confetti, no toast.

### Templates

With 50 or more templates, a list is the right picture, not tiles. Search field, below it „Zuletzt verwendet“ (Last used: five rows with folder, number of details, documents in the last 30 days, state), then „Alle Vorlagen · A–Z“ (all templates) in condensed form. The state is one word: **running** or **resting**.

### Setup assistant

Four steps, each a question in everyday language:

1. **Sample document**: „Ziehen Sie einen typischen Beleg hierher.“ (Drag a typical document here.)
2. **Mark details**: draw frames, name them. The core of the application.
3. **Result**: „Was soll aus jedem Beleg werden?“ (What should become of each document?) Excel table · one file per document · own format. With it the target folder and a **real preview of the table** as it will look later.
4. **Folder**: which folder is watched, plus a summary in full sentences. Finish: **save template and start.**

The step bar can be clicked backwards; completed steps carry a green check mark. Forwards only works through *Next*, so it stays clear that something is missing when it is missing.

**Step 2 in detail:** draw a frame → a small floating question appears *below* the highlight (never above it, or it covers what it asks about): „Was steht an dieser Stelle?“ (What is shown here?) with a text field and five suggestions as chips. On the right the list „Diese Angaben will ich haben“ (These are the details I need) grows, with name, recognised value and check mark. In the assistant **all name labels are permanently visible**; this is where the user learns the template. On the review screen they are hidden; there every label gets in the way.

---

## Word list

The interface uses only the left column. The right column lives in code, database and documentation, never on screen. The dictionaries are `src/i18n/de.ts` and `src/i18n/en.ts`; the header comment of `en.ts` holds the English counterparts.

| On screen | In the engine room |
|---|---|
| Vorlage (template) | document type, template |
| Angabe (detail) | field |
| Beleg (document) | document |
| sicher erkannt (recognised) | confidence ≥ threshold |
| nicht eindeutig (unclear) | confidence below threshold |
| wartet auf Prüfung (waiting for review) | review queue |
| überwachter Ordner (watched folder) | watch folder |
| abgelegt (filed) | exported |
| Alle Belege bleiben auf diesem Gerät (All documents stay on this device) | Air-gap mode |

Forbidden on every screen a user sees: path A/B, model names, Q4\_K\_M, GLiNER2, rapidfuzz, reading stage, confidence as a number, `snake_case`, JSON keys, locator, provenance, bounding box, OCR (except under „Technische Details“). The word gate in `tests/frontend/places.test.tsx` checks the four places in both languages.

---

## Colour tokens

Light is the **default**: a clerk's workplace is bright, and paper grey is calmer than any dark surface. Dark is maintained as an equal.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F3F3F1` | `#0D0E11` | window background (warm paper grey) |
| `--panel` | `#FAFAF9` | `#121316` | sidebar, right column |
| `--card` | `#FFFFFF` | `#17181C` | cards, rows, inputs |
| `--card-2` | `#F7F7F5` | `#1D1F24` | hover, muted surface |
| `--line` | `rgba(23,25,29,.09)` | `rgba(255,255,255,.08)` | hairline |
| `--ink` | `#17191D` | `#ECEDEF` | text **and primary button** |
| `--ink-2` | `#5B6069` | `#A2A7AF` | secondary text |
| `--ink-3` | `#8A9099` | `#71767E` | labels, times |

**Only four colours carry meaning, and all are desaturated:**

| Token | Light | Meaning | Where it appears |
|---|---|---|---|
| `--accent` `#4C5BD4` | selection and highlight | frames in the document, selected detail, notice boxes |
| `--good` `#2F7D5F` | running, recognised, filed | status dot, check marks, privacy notice |
| `--warn` `#A9701A` | waiting for review | review counter, the one tile, the active highlight |
| `--bad` `#B4453F` | error | rare; so far only in the log |

**The primary button is black, not colourful.** This is the central calm decision: when the only strong surface on the screen is neutral, colour stays free for meaning. A blue button would compete with the blue of the highlights, and the user would have to learn to distinguish what they need not distinguish.

**All highlights in the document carry the same colour.** The earlier draft gave each detail its own; with eight details a document turns into a paint box. Now: all highlights indigo and faint, the *active* one strong and amber. Details are told apart by their name label, not by hue.

The values live in `src/design/tokens.css`; the colour gate in `eslint.config.js` rejects Tailwind default colour names in components.

---

## Typography

Inter for the interface, JetBrains Mono only for paths and file names, **no longer for values**. A value that a person is meant to read and confirm belongs in the reading typeface. Both fonts are shipped; an `@font-face` pointing to a CDN breaks the locality promise.

Base size **14 px** (previously 13), line height 1.6. The application may be airy; the screen now rarely shows more than a dozen lines at once.

| Level | Size | Use |
|---|---|---|
| Title | 30 px / −0.035 em | one title per screen |
| Number | 32 px / −0.04 em | the three key figures |
| Review value | 21 px / −0.025 em | the value to be confirmed |
| Body text | 14 px | everything else |
| Secondary | 12.5–13 px | paths, times, explanations |
| Section heading | 13 px, `--ink-3` | „Überwachte Ordner“ (Watched folders) |

Section headings are in **sentence case**, not in capitals. Capitals look like a form; sentence case looks like a sentence.

Numbers are tabular and follow the interface language: in German `1.284` and `22.656,65 €`, in English `1,284` and `22,656.65 €`. Dates a person reads are written out: **25. Juli 2026** or **25 July 2026**, not `2026-07-25`. The ISO form belongs in the result, not on screen. `src/ui/format.ts` formats with `de-DE` or `en-GB` according to the chosen language.

---

## Dimensions and elevation

**Spacing:** multiples of 4. Cards 28 px inside, 40–44 px between sections. Text columns at most 920 px, lists 1180 px.

**Radii:** 8 (button) · 12 (row, field) · 16 (card) · 24 (large container) · pill (badge).

**Elevation: three levels, very flat:**

0. Surface with hairline. The normal case.
1. Card: 1 px line plus `0 1px 2px rgba(23,25,29,.05)`. Barely visible, but it lifts.
2. Floating (assistant question, menu): a soft, widely spread shadow.

No gradient on a surface. No frames around frames. No grain, no texture, no colour glow; the first draft had both, and both were emphasis without a statement.

---

## Motion

Three durations: 130 ms (hover) · 220 ms (state change) · 340 ms (fade in). Curve `cubic-bezier(.22,.7,.28,1)`.

Only what shows a relationship moves: the review counter counts down, a step is ticked off, a card lifts barely noticeably on hover. **Nothing pulses, nothing blinks, nothing runs permanently** except the progress indicator of an operation that is actually running. `prefers-reduced-motion` switches everything off.

---

## Operation and accessibility

- **Review is fully operable by keyboard:** `Enter` confirms and moves to the next document, `Tab` reaches „Ändern“ (Change), `Esc` leaves the queue. The shortcut is shown visibly on the button, not in a help page.
- Focus visible as a 2 px ring in `--accent`, 3 px offset.
- Contrast: body text ≥ 7:1, secondary text ≥ 4.5:1. The sand tone of the review tile is deliberately so light that the amber text on it holds up.
- **Colour never carries meaning alone.** The state has a dot *and* a word, the review tile has colour *and* number *and* button.
- Targets at least 32 px high. Rows in lists are clickable across their full area, not only their text.
- German interface: formal „Sie“, full sentences, no abbreviations except IBAN and USt-IdNr. The English interface uses plain, short sentences in British spelling.

---

## What does not appear

- technical terms, model names, percentages without context, field types
- more than one dark button per screen
- dialogs, except for destructive actions
- toasts for results that someone is meant to review
- progress bars for something that runs in the background and holds nobody up
- toolbars with more than four symbols
- emojis, illustrations, mascots, success messages
- a setting for something the application can decide by itself

---

## What changed compared with the first draft, and why

| Before | Now | Reason |
|---|---|---|
| Workbench as main screen | Overview of the running pipeline | Everyday work is automatic, not manual. The workbench put the exceptional case first. |
| Field list with type, method, confidence | Queue with one question per document | The user decides whether a value is right, not how it came about. |
| Eight highlight colours | One colour, the active one emphasised | Eight colours on a document are a paint box, not a tool. |
| Dark as default | Light as default | An office workplace is bright; paper grey is the calmer base. |
| Status bar with model, path, reading stage | One sentence in the sidebar: „Alle Belege bleiben auf diesem Gerät.“ (All documents stay on this device.) | The promise matters; the technology behind it does not, for this user. |
| `snake_case` field names visible | „Rechnungsnummer“ (invoice number) | The JSON key is derived in the background from the display name and can be changed in step 3 if IT requires it. |
| Confidence 0.74 | „nicht eindeutig“ (unclear) | A number nobody can interpret demands a decision nobody can make. |

The architecture from the build prompt stays unchanged. Only **what of it is visible** has moved.

---

## Implementation in stage 1

1. `tokens.css` with all custom properties of both themes; Tailwind refers exclusively to these variables. A default colour name (`bg-slate-800`) in component code is prevented by a lint rule.
2. Light theme by default, `data-theme` on `<html>`. The choice is stored per window in local storage under `substrakt.theme` (`src/design/theme.ts`); the language choice works the same way under `substrakt.language`.
3. Maintain two texts per detail: **display name** (shown) and **key** (output). The key is derived from the display name and is visible only in step 3 of the assistant.
4. One central dictionary per language for the word list above; no technical term may reach the interface through a second place.
5. The reference for dimensions, states and flows is `substrakt-design-v2.html`: Overview, Review, Templates and the four-step assistant, in light and dark.

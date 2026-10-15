# Writing

Status: 2026-10-15

This file applies to documentation, code comments, domain identifiers, tests
and commit messages. A uniform language makes architecture boundaries and
product terms findable; it is therefore more than editorial decoration.

## Language

**English** is used for everything in the repository except the German
interface:

- code comments and module header comments,
- identifiers, including domain identifiers, file and directory names,
  database tables and columns, API and YAML keys, error keys,
- documentation and measurement protocols,
- script output and log messages,
- test descriptions,
- commit subjects and commit bodies.

**German** remains for:

- interface texts in `src/i18n/de.ts`, which stay the default interface
  language; `src/i18n/en.ts` is its English counterpart,
- sample content of synthetic documents (an invoice generator prints
  „Rechnung“, not „Invoice“, where it imitates a German invoice),
- the frozen evaluation corpus `corpus/evaluation/v1` and its archived
  reports, including field names such as `belegnummer`; they are evidence and
  are not edited.

**Why the rule changed.** Until 15 October 2026 this file prescribed German.
That suited a German-speaking team building a product for German clerks. The
repository is now being prepared for public release, and contributors and
reviewers outside that team need to read code, rules and history. The users'
language stays German where users see it: the interface.

**From when.** The rule applies from the commit that introduced this file.
Existing German code, file names and records are translated by the plans
under `docs/plans/`; until a plan is merged, the German names it replaces
stay valid and are not renamed piecemeal. Commit messages are English from
this commit on.

Technical terms keep their established form: Sidecar, token, bounding box,
frontend, typecheck, commit and gate. Interface texts additionally follow the
language-specific word lists in `tests/frontend/places.test.tsx`; a term that
is correct internally may still be forbidden for the user there.

## A rule names its reason

Rules are written as context, not as a detached instruction. The pattern:

> **Colours** live exclusively in `src/design/tokens.css`. A `bg-slate-800`
> in component code is rejected by ESLint.

The first sentence states the boundary, the second the reason or the gate.
That way the next person knows which product property is affected and whether
an exception would only break style or a promise.

Where a gate exists, it is named with its file and the rejected state. Where
none exists, the domain reason is stated explicitly. Slogans such as „KISS“,
„DRY“ or „Clean Code“ do not replace a reason from this repository.

## Header comments

A header comment explains why a module exists and which boundary it holds. It
does not merely repeat file name or implementation.

- `sidecar/substrakt/store.py` explains why documents live only in memory and
  which data persists instead.
- `src/design/tokens.css` explains why colour values are in exactly one place
  and which ESLint gate enforces it.
- `eslint.config.js` explains why a direct frontend network path would bypass
  the locality promise and the audit chokepoint.

New modules with an architecture responsibility follow this pattern. A
comment like „helpers for X“ is not enough when the more important
information is the process, data or licence boundary.

## Typography and numbers

English prose uses English typography: “double quotes”, an em dash without
spaces or a spaced en dash consistently within one file, decimal point
(`0.74`, `98.9%`, `22,656.65 €`). Quoted German interface terms keep their
German quotation marks, for example „Vorlagen → Neue Vorlage“. Ruff `RUF001`
to `RUF003` stay disabled because German interface strings and synthetic
German sample content legitimately contain these characters.

Dates for humans are written out, for example “25 July 2026”.
Machine-readable timestamps and metadata use ISO 8601.

## Tests and commits

Python tests are named `test_*.py`, TypeScript tests `*.test.ts` or
`*.test.tsx`. A test description states in one sentence which property it
secures; „works“ or „test 1“ makes a green run uninterpretable.

A negative test names the rejected state. This matters especially for gates:
the test must show that a forbidden network call or a forbidden colour really
fails, not just that the clean tree is green.

The commit subject summarises the change as a sentence; the body explains
starting point, decision and why. Commits end with the `Co-Authored-By` line
prescribed by the environment.

## References instead of copies

The harness refers to `README.md`, `docs/decisions.md`,
`docs/design/design-language.md` and `docs/status.md` instead of duplicating
their full content. That prevents diverging versions; only the boundaries
needed to start work are condensed here.

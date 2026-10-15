# Plan: Harness — CLAUDE.md, AGENTS.md und die Regeln unter docs/harness/

> Übergabe vom Architekten (Claude) an die Umsetzung (Codex). Der Chat, in dem der Plan entstand, existiert für Codex nicht: was hier nicht steht, gibt es nicht.

**Stand:** 2026-09-15 · **Branch:** `codex/harness` · **Basis:** `designsprache-v2` · **Modell:** `gpt-5.6-sol` · **Aufwand:** high · **Prüfen:** `npm run lint && npm run test && bash -c 'for f in $(grep -o "^@.*" CLAUDE.md | sed "s/^@//"); do test -f "$f" || { echo "fehlt: $f"; exit 1; }; done'` · **Freigabe:** erteilt am 2026-09-15 · **Umgesetzt:** 2026-09-15

## Ziel

Harness anlegen: CLAUDE.md, AGENTS.md und neun Regeldateien unter docs/harness/, die aus dem bestehenden Code und der Doku abgeleitet sind.

Ein Agent, der das Repo neu öffnet, soll nach dem Lesen von `CLAUDE.md` wissen, was Substrakt ist, wo es steht, welche Zusagen unverhandelbar sind, welche Gates ihn abweisen und wie er eine Aufgabe zu Ende bringt. Alles davon existiert heute verstreut in README, `docs/entscheidungen.md`, `docs/design/designsprache.md`, Kopfkommentaren und Konfigurationsdateien. Der Harness verdichtet es an eine Stelle und verweist auf die Quellen, statt sie zu kopieren.

## Kontext

### Was das Projekt ist

Substrakt: Desktop-Anwendung (Tauri v2) zur Dokumentenextraktion, vollständig lokal. Drei Prozesse: React-Frontend → Rust-Shell → Python-Sidecar (FastAPI auf 127.0.0.1). Das Frontend hat keinen HTTP-Client, der Sidecar keine Netzwerkbibliothek, ausgehender Verkehr läuft allein durch `src-tauri/src/egress.rs`. Lies zuerst, in dieser Reihenfolge:

1. `README.md` (ganz) — Aufbau, die zwei Zusagen, die vier Orte, Koordinaten, Tests.
2. `docs/entscheidungen.md` (ganz) — bindende Festlegungen: Zusagen (Z. 6–16), Zielprofil (Z. 18), Stack-Tabelle (Z. 24–45), Architekturregeln (Z. 47–78), Provenance (Z. 80–94), Stufe-0-Ergebnisse (Z. 96–128).
3. `docs/design/designsprache.md` — Leitgedanke (Z. 9–25), die vier Orte (Z. 29–76), Wortliste (Z. 78–96), Farbtokens (Z. 98–126), „Was nicht vorkommt" (Z. 184–195).
4. `docs/stand.md` — Bericht nach Stufe 1. **Veraltet in einem Punkt:** Er beschreibt den Stand vom 28. Juli 2026 nach Stufe 1. Seitdem sind Stufe 2 (Commits `fcc871d` bis `3a192bd`: Normalisierer, Extraktoren, Grounding, Feldsätze in SQLite, OCR, manuelle Werte) und die Designsprache v2 (Commit `67995b4`) fertig. Die Abschnitte „Was die CI aufgedeckt hat", „Was der erste Start aufgedeckt hat" und „Falsche Annahmen" bleiben gültig und sind eine Quelle für die Lehren im Harness.
5. `git log --format='%h %ad %s%n%b' --date=short -12` — die Commit-Rümpfe sind ausführlich und beschreiben, was gebaut wurde und warum.

### Der aktuelle Stand (für `00-produkt.md`)

| Stufe | Inhalt | Stand |
|---|---|---|
| 0 | Messungen (OCR, VLM, Server-Durchsatz) | abgeschlossen 28. Juli 2026, `docs/messungen/` |
| 1 | Fundament: Parser, Koordinaten, Viewer, Sidecar, Gates | abgeschlossen 28. Juli 2026 |
| 2 | Feldextraktion: Normalisierung, Extraktoren, Grounding, Confidence, Feldsätze in SQLite, Tesseract-OCR, manuelle Werte | abgeschlossen 28. Juli 2026 |
| — | Designsprache v2: vier Orte statt Werkbank, Farb- und Wort-Gate | 30. Juli 2026 |
| 3 | LLM-Anbindung (llama.cpp), Vorlagen-Wiedererkennung, Ordnerüberwachung | offen |
| 4 | Export, Batch, Installer, Air-Gap-CI-Test | offen |

Bewusst offen aus Stufe 2: Die TypeScript-Typen in `src/api/types.ts` werden von Hand gepflegt, nicht aus `openapi.json` erzeugt. Das steht in `docs/stand.md` unter „Was fehlt" und gilt weiter.

### Die Gates, die ein Agent kennen muss

Sie sind der Kern des Harness. Jede Regeldatei nennt, welches Gate sie durchsetzt, damit die Regel nicht als Bitte gelesen wird.

| Gate | Wo | Was es abweist |
|---|---|---|
| Egress (ESLint) | `eslint.config.js` Z. 95–159 | `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `navigator.sendBeacon`, Import von `axios` und `@tauri-apps/plugin-http` in `src/` |
| Egress (Ruff) | `sidecar/pyproject.toml` `[tool.ruff.lint.flake8-tidy-imports.banned-api]` | `requests`, `urllib.request`, `httpx` im Sidecar |
| Egress (Grep) | `scripts/check_egress.sh` | alles, was die Linter per Kommentar abschalten könnten |
| Farben | `eslint.config.js` Z. 55–93 | Tailwind-Standardfarbnamen (`bg-slate-800`) in `src/`; erlaubt nur Tokens aus `src/design/tokens.css` |
| Wörter | `tests/frontend/orte.test.tsx` Z. 285–299 (`VERBOTEN`) | Konfidenz, Locator, Provenance, Bounding, OCR, Dokumenttyp, Template, Feld, Dokument, Extrakt, Regex, Modellnamen, `snake_case` im gerenderten Markup der vier Orte |
| Lizenzen | `scripts/check_licenses.py` gegen `licenses/policy.toml`; `cargo deny` in CI | Laufzeitabhängigkeiten außerhalb der Allowlist; Denylist auch für Entwicklung |
| Koordinaten | `tests/sidecar/fixtures/koordinaten.json`, geprüft von `tests/sidecar/test_koordinaten.py` und `tests/frontend/coords.test.ts` | Auseinanderlaufen der zwei Umrechnungsstellen `sidecar/substrakt/parsers/pdf.py` und `src/viewer/coords.ts` |
| Rust | CI-Job `shell` in `.github/workflows/ci.yml` | `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` |

### Kommandos (für `CLAUDE.md`)

Aus `package.json` (Z. „scripts"): `npm run app`, `npm run app:wsl` (WSL2, vier Umgebungsschalter aus `scripts/dev-wsl.sh`), `npm run check` (alle Gates), `npm run test`, `npm run test:sidecar`, `npm run lint`, `npm run typecheck`, `npm run licenses`, `npm run egress`, `npm run korpus`, `npm run bench`. Rust: `cd src-tauri && cargo test`, `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`. Cargo liegt unter `~/.cargo/bin`, das nicht immer im PATH ist; `export PATH="$HOME/.cargo/bin:$PATH"` davor. Einrichtung: `./scripts/setup-dev.sh`. Sidecar-Tests laufen ohne `SUBSTRAKT_DEV=1`, weil `tests/sidecar/conftest.py` die Variable auf Modulebene setzt.

Stand der Testzahlen am 2026-09-15: 71 TypeScript, 229 Python, 8 Rust; alle grün, Clippy und fmt sauber.

### Verzeichniskarte (für `01-architektur.md`)

```
src/                Frontend (React, TypeScript, Vite, Tailwind)
  App.tsx           Einstieg, schaltet zwischen den vier Orten
  orte/             Uebersicht, Pruefen, Vorlagen, Vorlagenansicht, Einstellungen, Assistent (+ assistent/Schritt*.tsx)
  shell/            Seitenleiste
  ui/               bausteine.tsx (Karten, Schaltflächen), format.ts
  viewer/           ViewerHost, PdfCanvas, ImageCanvas, SheetGrid, OverlayLayer, coords.ts
  api/              client.ts (Tauri-invoke, einziger Weg zum Sidecar), types.ts (handgepflegt)
  i18n/de.ts        alle Oberflächentexte und die Wortliste
  design/           tokens.css (einzige Stelle für Farbwerte), theme.ts
  zustand/          sitzung.ts
  ergebnis/         sichern.ts
src-tauri/src/      Rust-Shell
  lib.rs            Start, Zustand, Plugins
  sidecar.rs        Sidecar starten, Handshake, Lesewurzeln (SUBSTRAKT_ROOTS), stdin-Watchdog
  bridge.rs         Tauri-Commands, Weiterleitung an den Sidecar mit Token
  egress.rs         das Nadelöhr: einzige Funktion für ausgehenden Verkehr, drei Modi
  policy.rs         maschinenweite Policy-Datei
sidecar/substrakt/  Python-Backend
  app.py            FastAPI-Endpunkte (Z. 193–440)
  config.py         Sitzungstoken, Lesewurzeln, Grenzen
  errors.py         RFC-9457-problem+json mit stabilem `schluessel`
  model.py          Dokumentmodell (Document, Page, Word, text_source)
  store.py          geladene Dokumente, nur im Arbeitsspeicher
  parsers/          pdf.py (Koordinaten!), image.py, sheet.py, ocr.py
  index/words.py    Wort-BBox-Index
  extraktion/       felder.py, extraktoren.py, normalisierung.py, grounding.py
  db/               migrate.py (PRAGMA user_version), migrations/*.sql, typen.py
tests/frontend/     vitest: coords.test.ts, orte.test.tsx
tests/sidecar/      pytest: test_*.py, conftest.py, fixtures/koordinaten.json
corpus/             Generator für den synthetischen Testkorpus; corpus/echt/ nie einchecken
bench/run.py        Performance-Budgets
licenses/policy.toml  Allow- und Denylist, Single Source of Truth
docs/               entscheidungen.md, stand.md, design/, messungen/, plaene/, harness/
models/             Modellgewichte, nicht im Repo (scripts/fetch-models.sh)
```

### Muster für die Regeldateien

Die Dateien unter `docs/harness/` folgen dem Stil dieses Repos, nicht dem einer allgemeinen Checkliste: **Jede Regel nennt ihren Grund und, wo es eines gibt, das Gate, das sie durchsetzt.** Beispiel aus `README.md`, Abschnitt „Die Oberfläche":

> **Farben** stehen ausschließlich in `src/design/tokens.css`. Ein `bg-slate-800` im Komponentencode wird von ESLint abgewiesen.

So sieht eine Regel im Harness aus. Nicht: „Verwende keine Hardcoded-Farben."

Kopf jeder Datei: Titel als `# `, dann `Stand: 2026-09-15`, dann ein Absatz, der sagt, wofür die Datei gilt. Länge: 60 bis 150 Zeilen je Datei. Ein Agent liest sie bei jedem Start, also keine Wiederholung dessen, was `README.md` schon sagt; stattdessen der Verweis darauf.

Schreibweise: Deutsch, wie im ganzen Repo (Kommentare, Commit-Nachrichten, Doku, Bezeichner in der Fachdomäne wie `Feld`, `Lauf`, `DokumentTyp`). Technische Begriffe bleiben englisch (`Sidecar`, `Token`, `Bounding-Box`). Typografische Anführungszeichen „so", Gedankenstrich — als Halbgeviertstrich mit Leerzeichen, wie in `README.md`.

### Vorbild für CLAUDE.md mit @-Includes

Claude Code lädt Dateien, die in `CLAUDE.md` als eigene Zeile `@pfad/zur/datei.md` stehen, beim Start mit. Das ist der Mechanismus, mit dem `docs/harness/` verbindlich wird, ohne dass der Inhalt doppelt gepflegt wird. Form:

```markdown
## Regeln

Die Regeln liegen unter `docs/harness/` und werden hier geladen:

@docs/harness/00-produkt.md
@docs/harness/01-architektur.md
```

Jede `@`-Zeile steht allein, ohne Aufzählungszeichen, ohne Backticks.

## Schritte

1. **`docs/harness/00-produkt.md`** — Was Substrakt ist, für wen (Sachbearbeiter, kein Entwickler; Standard-Notebook, 16 GB, keine GPU), die zwei Zusagen im Wortlaut aus `docs/entscheidungen.md` Z. 8–16, die Stufentabelle aus dem Kontext oben mit dem Stand je Stufe, und was bewusst offen ist (Typgenerierung, Ordnerüberwachung, LLM-Pfad). Nenne die Grundlagendokumente über `docs/README.md`, ohne ihre Inhalte zu wiederholen. Ergebnis: ein Agent weiß nach dieser Datei, welche Stufe gerade dran ist und was er nicht als Fehler melden soll (etwa: „Ordner werden noch nicht überwacht" in der Übersicht ist Absicht).

2. **`docs/harness/01-architektur.md`** — Die drei Prozesse und die eine Richtung (README-Diagramm), das Egress-Nadelöhr mit den drei Betriebsmodi (`docs/entscheidungen.md` Z. 49–59), die Koordinatenregel mit den zwei Umrechnungsstellen und der gemeinsamen Fixture (README „Koordinaten"), Persistenz (SQLite nur für Typen, Felder, Läufe; Dokumente nur im Arbeitsspeicher, siehe `sidecar/substrakt/store.py` Z. 1–7), die Verzeichniskarte aus dem Kontext oben. Dazu die Regeln „Kein Modellname hart im Code", „Kein PyTorch im Bundle", „Kein Netzwerkzugriff zur Laufzeit" aus `docs/entscheidungen.md` Z. 65–78, je mit Grund.

3. **`docs/harness/02-sidecar.md`** — Regeln für `sidecar/`: Fehler verlassen den Prozess als `problem+json` mit stabilem `schluessel` (`errors.py`), nie als Stacktrace; das Frontend löst Texte über diesen Schlüssel auf, also ist ein neuer Fehler auch ein neuer Eintrag in `src/i18n/de.ts`. Keine Netzwerkbibliothek (Ruff-Gate). Neue Endpunkte: Pydantic-Modell in `model.py` oder `db/typen.py`, Endpunkt in `app.py`, Typ in `src/api/types.ts` von Hand nachziehen, Command in `src-tauri/src/bridge.rs`, Aufruf in `src/api/client.ts`. Migrationen: neue Datei `db/migrations/NNN_*.sql`, idempotent, `PRAGMA user_version`; Muster ist `002_ausgabeform.sql`. Ruff-Konfiguration: `select = ["E","F","I","UP","B","SIM","RUF"]`, RUF001–003 bewusst aus, weil deutsche Typografie. Tests: `tests/sidecar/`, Muster `test_api.py` (TestClient) und `test_felder.py`; Property-Tests mit `random.Random(seed)`, nicht Hypothesis (MPL-2.0). Neue Laufzeitabhängigkeit: Lizenz in `pyproject.toml` als Kommentar, `licenses/policy.toml`, `docs/entscheidungen.md`.

4. **`docs/harness/03-frontend.md`** — Regeln für `src/`: die vier Orte und der Assistent als Weg (Designsprache Z. 29–76); genau eine dunkle Schaltfläche je Bildschirm; Texte nur aus `src/i18n/de.ts`, nie im JSX; die Wortliste (Tabelle aus dem Kopf von `de.ts`) und die Verbotsliste aus `orte.test.tsx` Z. 285–299 wörtlich; Farben nur aus `tokens.css`, die Tokennamen (`bg-card`, `text-ink-2`, `border-line`, `text-good`, `bg-warn-bg`, siehe Designsprache Z. 98–126); kein `fetch`, alles über `src/api/client.ts`; Koordinaten nur über `src/viewer/coords.ts`, Rechtecke in Dokumentkoordinaten; PDF.js läuft nicht in Node, deshalb wird es in Tests gemockt (`orte.test.tsx` Z. 22–30). ESLint: `consistent-type-imports`, ungenutzte Variablen mit `_`-Präfix. Der Maschinenraum (Konfidenz als Zahl, Modellnamen, Schlüssel) gehört unter Einstellungen → Technische Details.

5. **`docs/harness/04-shell.md`** — Regeln für `src-tauri/`: Rolle jeder Datei (Verzeichniskarte); das Nadelöhr in `egress.rs` ist die einzige Stelle für ausgehenden Verkehr, ein zweiter HTTP-Client ist ein Verstoß; Lesewurzeln (`SUBSTRAKT_ROOTS`) werden von `sidecar.rs` gesetzt und dürfen keine Systemverzeichnisse enthalten (Test vorhanden); MutexGuard nie über einen HTTP-Aufruf halten (Lehre aus `docs/stand.md`, Abschnitt „Was die CI aufgedeckt hat", vorletzter Absatz); `cargo fmt` und Clippy mit `-D warnings` vor jedem Commit; Logging über `tauri-plugin-log`; `tauri.conf.json` referenzierte Dateien müssen existieren.

6. **`docs/harness/05-abhaengigkeiten.md`** — Vorgehen bei jeder neuen Abhängigkeit (Python, npm, Cargo, Modellgewicht): erst `licenses/policy.toml` lesen, Lizenz prüfen, Laufzeit oder Entwicklung entscheiden, Eintrag in `policy.toml` mit Grund, Kommentar mit Lizenz neben der Abhängigkeit (Muster `sidecar/pyproject.toml`), `docs/entscheidungen.md` nachziehen. Die Verbotstabelle aus `README.md` „Was nicht verwendet wird" übernehmen. Modelle: kein Name hart im Code, Registry-Eintrag braucht Repo, Revision, SHA-256, Lizenz, Lizenz-URL; `HF_HUB_OFFLINE=1`; `models/` ist nicht im Repo.

7. **`docs/harness/06-tests-und-gates.md`** — Die Gate-Tabelle aus dem Kontext oben. Wo welche Tests liegen und wie sie laufen. Die CI-Jobs aus `.github/workflows/ci.yml` (sidecar, frontend, shell, lizenzen, egress) in je einem Satz. Drei Lehren aus `docs/stand.md`, je mit Verweis: der grüne Test, der nichts absichert (Pfadprüfung, Bildrotation); Zeitmessungen sind kein Build-Gate (`--strikt` nur lokal); was lokal nicht gebaut wird, wird gehofft (Rust vor dem Setup). Regel: Ein neues Gate wird negativ getestet, wie das Egress-Gate und das Farb-Gate. Messungen kommen als Protokoll nach `docs/messungen/`, Annahmen ohne Messwert bleiben Schätzungen.

8. **`docs/harness/07-definition-of-done.md`** — Checkliste, kurz, in Abschnitten Allgemein / Sidecar / Frontend / Shell / Doku. Allgemein: Ziel in einem Satz; nur Dateien aus dem Auftrag; `npm run check` und `cargo test` grün; kein neues Gate umgangen; keine neue Abhängigkeit ohne Schritt 6; Voreinstellungen unverändert. Doku: `docs/stand.md` oder `docs/entscheidungen.md` nachgezogen, wenn sich eine Festlegung geändert hat; Commit-Nachricht deutsch, Betreff ein Satz, Rumpf mit Warum (Muster: `git log -5`); `Co-Authored-By`-Zeile bleibt, wie die Umgebung sie vorgibt. Frontend zusätzlich: neuer Text in `de.ts`, kein neuer Begriff aus der Verbotsliste, `orte.test.tsx` grün. Sidecar zusätzlich: neuer Fehler hat Schlüssel und Text; neuer Endpunkt hat Typ, Command und Client-Aufruf.

9. **`docs/harness/08-schreibweise.md`** — Deutsch in Code-Kommentaren, Bezeichnern der Fachdomäne, Commits und Doku; englische Fachbegriffe bleiben; Begründung statt Anweisung (Muster oben); Kopfkommentare erklären das Warum eines Moduls (Beispiele: `store.py` Z. 1–7, `tokens.css` Z. 1–16, `eslint.config.js` Z. 6–14); Zahlen mit deutschem Dezimalkomma in Prosa; Dateinamen in `src/orte/` und `src/i18n/` deutsch; Tests heißen `test_*.py` und `*.test.ts(x)` und beschreiben in einem Satz, was sie absichern.

10. **`CLAUDE.md`** in der Repo-Wurzel, höchstens 80 Zeilen: ein Absatz, was Substrakt ist; ein Absatz zum Stand (Stufe 2 fertig, Stufe 3 offen, Details in `00-produkt.md`); Block „Kommandos" aus dem Kontext oben; Block „Bevor du etwas änderst": die vier Gates in je einem Satz mit Verweis; Block „Regeln" mit den neun `@`-Zeilen für `docs/harness/00` bis `08`; Block „Quellen": `README.md`, `docs/entscheidungen.md`, `docs/design/designsprache.md`, `docs/stand.md`, `docs/plaene/` (Pläne für Codex). Satz: „Widersprechen Doku und Code, gilt der Code; danach die Doku nachziehen."

11. **`AGENTS.md`** in der Repo-Wurzel, höchstens 60 Zeilen, für Codex und andere Agenten ohne `@`-Mechanismus: derselbe Inhalt wie `CLAUDE.md`, aber die Regeldateien als Pflichtlektüre mit Pfad aufgelistet statt eingebunden. Zusätzlich ein Abschnitt „Sandbox": Was in der Sandbox scheitert (EPERM beim Port, schreibgeschütztes `.git`, fehlendes `uv` oder `cargo`), ist ein Befund im Bericht, kein Grund für einen Umbau des Codes.

12. **`docs/README.md`** — im Abschnitt „Weitere Dokumente" zwei Einträge ergänzen: `harness/` (Regeln für Agenten, werden von `CLAUDE.md` geladen) und `plaene/` (Übergabepläne an Codex).

13. **`README.md`** — die Hinweisbox in Z. 10–13 („Stand: Stufe 1") ersetzen durch: Stufe 2 abgeschlossen, Designsprache v2 umgesetzt, Stufe 3 (LLM-Anbindung, Vorlagen-Wiedererkennung, Ordnerüberwachung) offen; Verweis auf `docs/harness/00-produkt.md` für den Stand und weiterhin auf `docs/stand.md` für den Bericht. Sonst nichts an `README.md`.

## Nicht anfassen

- Kein Code. Dieser Plan ändert ausschließlich Markdown-Dateien: die 13 Dateien aus den Schritten und keine weitere.
- `docs/stand.md` bleibt, wie es ist. Der Bericht nach Stufe 2 ist ein eigener Plan.
- `docs/entscheidungen.md` und `docs/design/designsprache.md` bleiben unverändert; der Harness verweist darauf.
- Keine neue Abhängigkeit, kein Skript, keine Änderung an `package.json`, `eslint.config.js`, `pyproject.toml` oder der CI.
- Keine Anpassung an die Sandbox. Scheitert `npm run test:sidecar` oder `cargo test` in der Sandbox, steht das im Bericht; der Prüfbefehl des Plans braucht beides nicht.
- Keine englischen Regeln aus anderen Projekten übernehmen („KISS", „DRY", „Clean Code" als Schlagworte). Jede Regel hier hat einen Grund aus diesem Repo.
- Nichts erfinden, was der Code nicht hergibt: keine Regel zu Modulen, die es nicht gibt (Registry, Watcher, LLM-Client). Wo etwas geplant, aber nicht gebaut ist, steht „geplant für Stufe 3" dabei.
- Den Abschnitt „Befunde der Abnahme" schreibt der Architekt.

## Fertig, wenn

- Der Prüfbefehl aus der Kopfzeile grün ist: Lint, Frontend-Tests und alle `@`-Pfade in `CLAUDE.md` existieren.
- `git status --short` genau die 13 Dateien aus den Schritten zeigt (11 neue, `README.md` und `docs/README.md` geändert).
- Man `CLAUDE.md` liest und ohne weitere Datei weiß: was das Projekt ist, wie man es startet und prüft, und welche neun Dateien die Regeln tragen.
- Jede Regeldatei zu jeder Regel einen Grund und, wo vorhanden, das Gate nennt.

## Befunde der Abnahme

Geprüft am 2026-09-15 im Worktree. `git status --short` zeigt genau die 13 Dateien aus den Schritten; Prüfbefehl grün (ESLint, 71 Vitest-Tests, alle neun `@`-Pfade vorhanden). Sidecar- und Rust-Tests wurden nicht erneut ausgeführt, weil kein Code geändert wurde.

Codex hat über den Plan hinaus aus dem Code abgeleitet und alles davon stimmt: `Egress::anfordern` (`egress.rs` Z. 76), `verbindung` in `bridge.rs` Z. 88, Rückfall auf Air-Gap in `policy.rs`, `no_proxy()` in `lib.rs` Z. 36, `reqwest`-Beschränkung in `check_egress.sh` Z. 71, `torch` samt Aliassen in `policy.toml` Z. 177, Zählung der dunklen Schaltflächen in `orte.test.tsx` Z. 274, `src-tauri/deny.toml`.

- `CLAUDE.md` Z. 6: Erwartung „kein Modellaufruf", Ist „Modellaufruf" ohne Verneinung, Satz grammatisch schief. Vom Architekten berichtigt.
- `CLAUDE.md` und `AGENTS.md`, Block Kommandos: Erwartung keine Testzahlen ohne Datum, Ist „71", „229", „8" als Kommentar. Sie veralten mit dem nächsten Test. Vom Architekten entfernt; die datierte Angabe in `06-tests-und-gates.md` bleibt.
- Kein weiterer Befund. Die Regeldateien halten das Muster „Grenze, dann Grund oder Gate" durch; keine übernommenen Schlagworte.

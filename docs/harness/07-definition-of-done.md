# Definition of done

Status: 2026-10-15

This checklist applies before handing over any change. It is kept short so
that it is actually checked completely; the reasons and gates behind the
points are in the other harness files.

## General

- [ ] The goal of the change can be stated in one sentence.
- [ ] Only files belonging to the task are changed; existing foreign changes
  stay untouched.
- [ ] `npm run check` is green.
- [ ] `cd src-tauri && cargo test` is green.
- [ ] A reproducible sandbox or tool obstacle is named in the report and not
  presented as a green run.
- [ ] No existing gate was disabled, exempted or bypassed through an
  alternative path.
- [ ] A new gate has a negative test that demonstrably fails with the
  forbidden state.
- [ ] New dependencies fully follow the procedure in
  `docs/harness/05-dependencies.md`.
- [ ] Defaults stay unchanged unless the task explicitly requires changing
  them; above all, Air-gap stays the default.
- [ ] New assumptions are named as estimates or backed by a protocol under
  `docs/measurements/`.

## Sidecar

- [ ] A new error has a stable key in `sidecar/substrakt/errors.py` and a
  German text in `src/i18n/de.ts` and an English text in `src/i18n/en.ts`.
- [ ] Domain errors leave the process as `problem+json`, not as a stack trace
  or unstructured string.
- [ ] A new endpoint has Pydantic model, FastAPI route, hand-written
  TypeScript type, registered Tauri command and a call in
  `src/api/client.ts`.
- [ ] A schema change has a numbered, transactionally checked migration and a
  test for existing databases.
- [ ] `tests/sidecar/` covers the success case and relevant rejections.
- [ ] No network library has entered the shipped sidecar.

## Frontend

- [ ] Every new visible text has matching entries in `src/i18n/de.ts` and
  `src/i18n/en.ts`, not in JSX.
- [ ] No new term from the forbidden list appears on any of the four user
  screens; engine-room terms stay under „Technische Details“.
- [ ] A screen has exactly one dark button.
- [ ] Colours use existing semantic tokens; a new token is justified in light
  and dark theme.
- [ ] Viewer rectangles stay in document coordinates and are converted only
  through `src/viewer/coords.ts`.
- [ ] `tests/frontend/places.test.tsx` passes in German and English, and the
  other frontend tests are green.

## Shell

- [ ] Outbound traffic runs exclusively through `src-tauri/src/egress.rs`;
  local sidecar calls stay in the bridge.
- [ ] No `MutexGuard` lives across an HTTP call.
- [ ] Changes to read roots keep the list non-empty and still exclude system
  directories.
- [ ] Every resource referenced in `tauri.conf.json` exists.
- [ ] `cargo fmt --check` and `cargo clippy --all-targets -- -D warnings` are
  green before the commit.
- [ ] Logs contain no document contents.

## Documentation and hand-over

- [ ] `docs/status.md` or `docs/decisions.md` is updated when status,
  stack or a binding decision has changed; `CHANGELOG.md` names user-visible
  changes.
- [ ] Contradictions between documentation and code are resolved in favour of
  the code and then corrected in the documentation.
- [ ] The commit message follows `docs/harness/08-writing.md`: English, the
  subject is a sentence, the body explains why.
- [ ] The `Co-Authored-By` line prescribed by the environment is kept.
- [ ] The hand-over report names the checks run, their results and open
  findings without presenting a failed run as a success.

## Goal

<!-- One sentence. -->

## Why

<!-- Starting point and reason for the decision. -->

## Checks

- [ ] `npm run check` is green
- [ ] `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings` and `cargo test` in `src-tauri/` are green
- [ ] Checks that could not run are named below, not reported as green
- [ ] No gate disabled, exempted or bypassed
- [ ] New dependencies or models follow `docs/harness/05-dependencies.md`
- [ ] No real documents, document content in logs, or changed defaults (Air-gap stays the default)
- [ ] New interface texts are in `src/i18n/de.ts`

## Not done or not checked

<!-- Open findings, skipped checks, follow-ups. -->

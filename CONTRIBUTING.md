# Contributing to Substrakt

Thank you for helping. Substrakt makes two promises that every change has to
keep, and most of the project's rules exist to protect them:

1. **Nothing leaves the infrastructure.** No document content, model call or
   telemetry goes over the network.
2. **Fully permissive licences** for code *and* model weights.

Both are enforced by gates in CI. A pull request that weakens a gate is not
merged, even if it is otherwise correct.

## Setting up

Setup is currently scripted for Linux and WSL2.

```bash
git lfs install --local   # the evaluation corpus is stored in Git LFS
npm start                 # set up, fetch models, start the app
```

The first run executes `scripts/setup-dev.sh` (asks once for sudo to install
Rust, `uv`, the Tauri system packages and Tesseract) and
`scripts/fetch-models.sh` (downloads model weights with SHA-256 checks).
Under WSL2 use `npm run app:wsl`. See the [README](README.md) for details.

## Before you open a pull request

Run the same checks as CI:

```bash
npm run check                       # typecheck, lint, both test suites, licences, egress
export PATH="$HOME/.cargo/bin:$PATH"
cd src-tauri
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
```

If a check cannot run on your machine, say so in the pull request. A check
that did not run is not a green check.

## Rules that are easy to break

**No network access outside the shell.** The frontend talks to the backend
only through `src/api/client.ts` and Tauri `invoke`. The sidecar imports no
HTTP client. Outbound traffic goes through `Egress::request` in
`src-tauri/src/egress.rs` and nowhere else. ESLint, Ruff and
`scripts/check-egress.sh` reject other paths.

**Every new dependency is a licence decision.** Read `licenses/policy.toml`
first, check the licence including transitive packages, add the package and
the reason to the policy, and put the licence as a comment next to the
dependency. Model weights need repository, immutable revision, SHA-256,
licence and licence URL. PyTorch, PyMuPDF, OpenCV wheels and GPL packages are
rejected by name.

**Coordinates are stored in document space.** The conversion lives only in
`sidecar/substrakt/parsers/pdf.py` and `src/viewer/coords.ts`; both are
tested against `tests/sidecar/fixtures/coordinates.json`.

**Interface texts live in both `src/i18n/de.ts` and `src/i18n/en.ts`.** Users
see „Vorlage“, „Angabe“ and „Beleg“, or their English counterparts, not
technical terms; the word gate in `tests/frontend/places.test.tsx` rejects
the language-specific forbidden lists. Colours come from
`src/design/tokens.css`; Tailwind default colour names are rejected.

**No document content in logs or error messages.** File name, hash and
technical details are enough to diagnose a problem.

**Never commit real documents.** Use synthetic data (`npm run corpus`).
`corpus/echt/` is ignored for local real documents and must stay out of Git.

The full rule set, with the reason behind each rule, is in
[`docs/harness/`](docs/harness/). The [definition of done](docs/harness/07-definition-of-done.md)
is the checklist reviewers use.

## Pull requests and commits

- One goal per pull request, stated in one sentence.
- Tests show the production path and the relevant failure cases, not only a
  helper in the success case. A new gate comes with a test that proves it
  fails on the forbidden state.
- Commit subjects are full sentences; the body explains why the change was
  needed. See `git log` for the pattern.
- Do not change defaults, Air-gap above all, unless that is the point of the
  pull request.

## Reporting bugs and security issues

Use the issue templates for bugs and ideas. Report vulnerabilities, especially
anything that lets data leave the machine, privately as described in
[SECURITY.md](SECURITY.md).

By contributing you agree that your contribution is licensed under the
[Apache License 2.0](LICENSE).

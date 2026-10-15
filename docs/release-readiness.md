# Release readiness: can the repository go public?

Status: 15 October 2026. The audit covered the working tree and the complete
Git history of the private repository as it was before publication (all
branches, local and remote).

This document records whether `MarcusBaitz/doc-extractor` can be switched
from private to public, what was checked, and what is still open. The decision
to publish is the owner's; this report only supplies the evidence.

## Verdict

**Yes.** No secrets, no real customer documents and no personal data of
third parties were found in the tree or anywhere in the private history. The
only hard blocker was the missing `LICENSE` file, which is now added. The
three owner decisions are taken (see
[Decisions for the owner](#decisions-for-the-owner)): the repository is
published fresh, with a single initial commit, so the private history is not
published at all.

| Area | Result |
|---|---|
| Own code licence | Apache-2.0 declared in `package.json`, `Cargo.toml`, `pyproject.toml`; **`LICENSE` was missing — added** (canonical text, MD5 `3b83ef96…bd57`) |
| Python and npm dependencies | `npm run licenses`: 58 Python and 194 npm packages, no violations |
| Rust dependencies | **not verified locally** — `cargo-deny` is not installed; the CI job `licenses` runs it |
| Model weights | Apache-2.0 (tessdata_best 4.1.0, granite-docling-258M); fetched, never committed; **granite-docling revision was unpinned — pinned** |
| Evaluation corpus | synthetic, generated with ReportLab; no real documents |
| `samples/` | fictitious data on a scanned official form; **deleted** |
| Secrets in history | none found |
| Personal data in history | only the owner's name and e-mail as commit author; moot, the history is not published |
| Measurement logs | no host names, user paths or IPs beyond `127.0.0.1`/`0.0.0.0` and a kernel version |
| Links to private documents | four Google Drive links in `docs/README.md`; owner-only, nothing exposed, but dead for readers |

## What was checked and how

### Secrets across the full history

`git log --all -p` (13 MB of patches, all commits of all local and remote
branches) was searched for added lines matching GitHub, Hugging Face, OpenAI,
Anthropic, AWS, Slack and Google key formats, PEM private keys, and
`api_key|secret|password|token = "…"` assignments. **No hits.** `gitleaks` and
`trufflehog` are not installed, so this is a pattern search, not a scanner run.

No file named `.env`, `*.pem`, `*.key`, `*.db`, `*.log` or below
`corpus/echt/` was ever added; `.gitignore` excludes all of them.

The Mistral comparison scripts read `MISTRAL_API_KEY` exclusively from the
process environment. The key appears only as that variable name, never as a
value — checked in the patches, the six LFS JSON files and the unpacked
`vergleich-reproduktion.zip`.

Git LFS content is not part of `git log -p`; it was checked separately:
all LFS JSON files and the ZIP contain no `/home/`, `C:\`, `Users`, owner
name, `sk-` or `api_key` strings.

### Personal data

- **E-mail addresses** in added lines: only `kontakt@example.invalid`
  (synthetic documents) and decorators such as `@app.get`.
- **User paths**: no `/home/<user>`, `/Users/<user>` or `C:\Users\…` in any
  added line, LFS file or measurement log.
- **IBANs**: all follow test patterns (`…0001 2345 67`, `…1234 5678 90`) and
  come from the generators `corpus/generate.py` and `corpus/measurement_corpus.py`.
  They use real bank codes with valid check digits; see the recommendations.
- **Names**: the owner's first name appears twice in `docs/status.md` as the
  person who found a bug. No other real person is named.
- **Commit metadata**: almost all commits carried the owner's personal
  e-mail address. Moot after the reset to a single initial commit; that
  commit's author address is the owner's choice.

### Evaluation corpus (`corpus/evaluation/`, Git LFS, about 40 MB)

The 84 PDFs are **synthetic**. Evidence:

- all 84 have `Author=anonymous`, `Creator=anonymous`,
  `Producer=ReportLab PDF Library` — none is a scan or a camera image;
  the `_scan` and `_photo` variants are rendered degradations;
- senders are `Fiktivwerk Alpha … Zeta GmbH`, VAT IDs
  `DE970000000`–`DE970000509`, addresses `Testweg 12, 00000 Musterstadt`;
- `v1/tools/generate.py` reproduces them with a fixed seed and only
  Helvetica (a PDF base font, nothing embedded);
- `v1/README.txt` states the same.

The reports include cached responses of the Mistral OCR cloud API for these
synthetic PDFs (`reports/2026-10-14/benchmark84/cache/mistral-*.json`). They
contain model output, page dimensions and usage counts, no account or request
identifiers. Publishing model output is generally permitted to the API user,
but Mistral's terms were not reviewed for this report.

### `samples/transportschein-aok.pdf`

A two-page phone scan (Genius Scan, 5 July 2026) of the official German
patient-transport form *Muster 4*. Every entry is fictitious and the form is
stamped „MUSTER“: insured person „Erika Musterfrau“, insurer „AOK
Testkasse“, „Radiologie Teststadt“, carrier IK `601234567`. **No personal
data.** The file is not used by any script; tests expect a copy under
`corpus/out/` and skip without it.

Two caveats: the form layout itself is a printed official form, not our
work, so it is not covered by Apache-2.0; and the handwriting and initials
belong to whoever filled it in.

### Licences of dependencies and weights

- **Python and npm**: `npm run licenses` passes. Development-only packages
  outside the runtime allowlist are flagged as such: `opencv-python`
  (pulled by `rapidocr-onnxruntime` in the dependency group `ocr`, used only
  for the stage-0 comparison), `tqdm` (MPL-2.0 AND MIT), `caniuse-lite`
  (CC-BY-4.0), `lightningcss` (MPL-2.0). None is shipped; none restricts
  publishing the source.
- **Rust**: `cargo deny check licenses bans sources` could not be run
  locally (`no such command: deny`). The CI job `licenses` covers it; the
  last green run on the branch is the evidence, not this report.
- **Model weights** (`scripts/fetch-models.sh`, downloaded at setup, never
  committed, `models/` is ignored):
  - `tessdata_best` `deu`/`eng`, tag `4.1.0`, Apache-2.0, SHA-256 pinned.
  - `granite-docling-258M` Q8_0 GGUF and mmproj from `ggml-org`,
    Apache-2.0 (IBM's original licence, kept by the conversion), SHA-256
    pinned. The URL used `resolve/main`, not an immutable revision, which
    violates `docs/harness/05-dependencies.md` (every model entry needs
    an immutable revision). **Fixed:** both URLs now point to commit
    `684c1800c5fbd614e29b4d1a82177e6c122af1f3` (5 October 2025). The
    Hugging Face API lists the same LFS SHA-256 values as the script, and the
    model card states `apache-2.0`.

### External links

All URLs in added lines of the history were listed by domain. Besides
package registries, upstream projects and documentation, two kinds stand out:

- `dateiablage.kunde.intern` and `10.0.4.12` are fixtures in the unit tests
  of `src-tauri/src/egress.rs`, not real hosts.
- `docs/README.md` (and earlier versions of `README.md`) link four Google
  Drive documents in the owner's folder „Ka&Pe“: the technical analysis, the
  licence audit, the Mistral/vLLM decision and the build prompt. Their Drive
  permissions were read on 15 October 2026: **owner only, no link sharing.**
  Publishing the repository exposes their IDs and the folder name, not their
  content. For public readers the links are dead; `docs/decisions.md`
  already condenses what is binding.

### Measurement logs and reports

`docs/measurements/`, `docs/status.md`, `docs/plans/`, `bench/` and the report
READMEs were searched for host names, private IP ranges, user paths and
cloud providers. Hits: `127.0.0.1`, `0.0.0.0` (local benchmark servers) and
the WSL kernel version `6.6.87.2`. Nothing identifies a machine or network.

## Decisions for the owner

Taken on 15 October 2026:

1. **Commit e-mail and private history.** The history is reset to a single
   initial commit, and the GitHub repository is deleted and created anew. The
   old commits, their author addresses and the Drive links in old README
   versions are therefore never published. No `filter-repo` rewrite is needed.
2. **`samples/transportschein-aok.pdf`** is deleted. Tests that use the form
   expect a local copy under `corpus/out/` and skip without it.
3. **Mistral comparison.** The README states that the comparison scripts
   measured a cloud competitor on synthetic data and are not part of the
   application. The archived reports are deleted and the 84-document
   comparison is run again before publication.

## Recommendations (not blocking)

- Done: `NOTICE` with the copyright line and the model weights; installers
  must additionally carry the notices of bundled libraries (PDFium via
  pypdfium2 and others), which is a stage-4 installer task.
- Done: `bundle.copyright` in `src-tauri/tauri.conf.json` said `"Apache-2.0"`,
  a licence rather than a copyright; it now names the holder.
- Enable GitHub's private vulnerability reporting when switching to public;
  `SECURITY.md` and the issue template link to it.
- Replace real bank codes in the corpus generators with codes that cannot
  belong to an existing account, or state that the accounts are fictitious.
  Changing `corpus/evaluation/v1` itself is off limits (frozen test set).
- Done: the Drive table in `docs/README.md` is replaced by a sentence that
  the original analyses are internal. Keep the Drive files private; switching
  them to link sharing would publish them through the old commits.
- Run `gitleaks detect --log-opts="--all"` once with the real tool before the
  switch; this report used pattern searches.
- Install `cargo-deny` locally so the Rust licence check is not CI-only.
- Public repositories on GitHub's free plan have 1 GB LFS bandwidth per month;
  at about 40 MB per full LFS pull that is roughly 25 clones with
  `git lfs pull`.
- The product name „Substrakt“ was not checked for trademark conflicts.

## Not covered

- Mistral's API terms for redistributing outputs.
- Trademark search for „Substrakt“.
- The Rust dependency tree (see above).
- A scanner-based secret search (`gitleaks`, `trufflehog`).

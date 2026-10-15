# Security policy

Substrakt processes invoices, forms and other business documents on the
user's own machine. Its central promise is that **no document content, model
call or telemetry leaves the infrastructure**. A weakness that breaks this
promise is a security issue, even if nothing else is affected.

## Reporting a vulnerability

Please report vulnerabilities privately through
[GitHub's private vulnerability reporting](../../security/advisories/new)
for this repository. Do not open a public issue, and do not attach real
documents: describe the problem with synthetic data such as the files
produced by `npm run corpus`.

You can expect an acknowledgement within seven days. Fixes are released as
soon as they are verified; the advisory credits the reporter unless asked
otherwise.

## In scope

- Any path by which document content, extracted values, file names or usage
  data can leave the machine, especially one that bypasses
  `Egress::request` in `src-tauri/src/egress.rs` or its audit log.
- Ways to widen the operating mode beyond the machine-wide policy, for example
  from Air-gap to On-premise without an administrator.
- Leaks of the sidecar's session token or port into the WebView, logs or
  process arguments.
- Reading files outside the configured read roots (`SUBSTRAKT_ROOTS`).
- Document content written to disk, logs or error messages, outside the
  in-memory store.
- Code execution through crafted PDFs, images or spreadsheets.
- Dependencies or model weights whose licence contradicts
  `licenses/policy.toml`.

## Out of scope

- Attacks that already require administrator rights on the machine.
- Denial of service through very large local files the user opens themselves.
- Evaluation scripts under `corpus/evaluation/`, which may call a cloud OCR
  service on synthetic data and are not part of the application.

## Supported versions

Substrakt has no released version yet. Security fixes go to `main`.

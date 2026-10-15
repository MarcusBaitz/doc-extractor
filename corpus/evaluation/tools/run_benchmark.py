"""Run the 84-PDF benchmark against the current Substrakt pipeline.

Every PDF of the frozen corpus in ``corpus/evaluation/v1`` is parsed and
extracted locally with the fields of a document kind from its YAML file
(``invoice`` by default). Reference values are loaded only after all
extractions have finished, and only for scoring through ``v1/evaluate.py``.

Local only: this tool makes no network calls and has no cloud comparison.

Output (default ``corpus/evaluation/reports/<date>/``):

- ``predictions.jsonl``  one line per PDF with ``fields`` and ``review_fields``
- ``results.json``       protocol, raw records and scores
- ``summary.csv``        scores per scope and group
- ``fields.csv``         every expected/predicted field value
- ``report.html``        self-contained report, works offline
- ``README.md``          the same summary as Markdown, rendered by GitHub
- ``cache/``             one file per PDF; an interrupted run resumes

Usage from the repository root, with the sidecar environment and Tesseract::

    sidecar/.venv/bin/python corpus/evaluation/tools/run_benchmark.py
    sidecar/.venv/bin/python corpus/evaluation/tools/run_benchmark.py --verify corpus/evaluation/reports/<date>

SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import os
import subprocess
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CORPUS = REPO / "corpus" / "evaluation" / "v1"
REPORTS = REPO / "corpus" / "evaluation" / "reports"
sys.path.insert(0, str(REPO / "sidecar"))
sys.path.insert(0, str(CORPUS))

from evaluate import DEFAULT_FIELDS, evaluate  # noqa: E402

PROTOCOL_VERSION = "benchmark84-v3"

# The only link between the document kind and the frozen corpus: field name in
# the document kind's YAML file → key in v1/ground_truth/expected.jsonl. The
# corpus keys stay German forever (v1 is frozen); the field names may change.
# A field missing here is looked up under its own name.
CORPUS_KEYS = {
    "document_number": "belegnummer",
    "document_date": "belegdatum",
    "total_amount": "gesamtbetrag",
    "net_amount": "nettobetrag",
    "tax_amount": "steuerbetrag",
    "currency": "waehrung",
    "vat_id": "ust_idnr",
    "document_kind": "dokumentart",
    "sender": "absender",
}


def corpus_key(field_name: str) -> str:
    return CORPUS_KEYS.get(field_name, field_name)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def truth() -> list[dict]:
    return read_jsonl(CORPUS / "ground_truth" / "expected.jsonl")


def evaluated_fields() -> list[str]:
    """All annotated fields, in the order of the shared field schema."""
    return list(read_json(CORPUS / "field-schema.json")["properties"])


# --- Windows: Tesseract through WSL -------------------------------------------


def configure_ocr_for_windows() -> None:
    """On Windows, run the Linux Tesseract inside WSL with the repository's tessdata."""
    if os.name != "nt":
        return
    from substrakt.parsers import ocr

    def wslpath(path) -> str:
        p = str(Path(path).resolve()).replace("\\", "/")
        return "/mnt/" + p[0].lower() + p[2:]

    def tsv(path, language, threads, psm=3):
        result = subprocess.run(
            ["wsl", "--", "env", "TESSDATA_PREFIX=" + wslpath(REPO / "models" / "tessdata"),
             "OMP_THREAD_LIMIT=" + str(threads), "tesseract", wslpath(path), "stdout",
             "-l", language, "--psm", str(psm), "tsv"],
            capture_output=True, encoding="utf-8", timeout=300,
        )
        if result.returncode:
            raise RuntimeError("Tesseract through WSL failed")
        return list(csv.DictReader(io.StringIO(result.stdout), delimiter="\t", quoting=csv.QUOTE_NONE))

    ocr._tsv = tsv
    ocr.available = lambda: True


# --- Running --------------------------------------------------------------------


def protocol(kind_name: str, fields: list[str], local_fields: list) -> dict:
    sources = sorted(
        p for p in (REPO / "sidecar" / "substrakt").rglob("*")
        if p.suffix in (".py", ".yml") and "__pycache__" not in p.parts
    )
    try:
        commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain", "--", "sidecar"], text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = "unknown", True
    tessdata = REPO / "models" / "tessdata" / "deu.traineddata"
    result = {
        "version": PROTOCOL_VERSION,
        "document_kind": kind_name,
        "core_fields": DEFAULT_FIELDS,
        "all_fields": fields,
        "local_fields": [f.model_dump(mode="json") for f in local_fields],
        "corpus_keys": {f.name: corpus_key(f.name) for f in local_fields},
        "unconfigured_fields": [k for k in fields if k not in {corpus_key(f.name) for f in local_fields}],
        "manifest_sha256": digest(CORPUS / "manifest.json"),
        "commit": commit,
        "sidecar_dirty": dirty,
        "source_hashes": {str(p.relative_to(REPO)): digest(p) for p in sources},
        "tessdata_sha256": digest(tessdata) if tessdata.exists() else None,
        "notes": [
            "Regression on an already inspected synthetic corpus, not a blind benchmark.",
            "The four core fields are the primary comparison; all annotated fields are scored as well.",
            "Reference values are loaded only after extraction, for scoring.",
            "Local pipeline only; no network calls.",
        ],
    }
    result["fingerprint"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def extract(path: Path, sha: str, fields: list, kind) -> dict:
    from substrakt.extraction.fields import extract
    from substrakt.parsers import pdf

    start = time.perf_counter()
    doc = pdf.parse(path, sha, sha, path.stat().st_size)
    if any("could not be recognized" in w for w in doc.meta.warnings):
        raise RuntimeError("OCR failed; check Tesseract and models/tessdata before resuming")
    run = extract(doc, fields, kind=kind)
    values = {}
    for e in run.results:
        v = e.normalized if e.normalized is not None else e.value
        values[corpus_key(e.field)] = None if v is None else str(v)
    return {
        "fields": values,
        "review_fields": [corpus_key(e.field) for e in run.results if not e.grounded or e.note],
        "seconds": time.perf_counter() - start,
        "details": [e.model_dump(mode="json") for e in run.results],
        "warnings": doc.meta.warnings,
        "text_source": doc.meta.text_source,
        "pages": len(doc.pages),
    }


def run(output: Path, kind_name: str, limit: int | None) -> dict:
    from substrakt import document_kinds

    configure_ocr_for_windows()
    kind = document_kinds.load(kind_name)
    fields = evaluated_fields()
    local_fields = [f for f in kind.fields if corpus_key(f.name) in fields]
    proto = protocol(kind_name, fields, local_fields)

    output.mkdir(parents=True, exist_ok=True)
    (output / "cache").mkdir(exist_ok=True)
    if (output / "protocol.json").exists():
        if read_json(output / "protocol.json") != proto:
            raise SystemExit(f"{output} holds a run of a different source state; choose a new --output")
    else:
        write_json(output / "protocol.json", proto)

    manifest = read_json(CORPUS / "manifest.json")[:limit]
    records = []
    for n, item in enumerate(manifest, 1):
        path = (CORPUS / item["path"]).resolve()
        if not path.is_relative_to((CORPUS / "inputs").resolve()) or path.suffix != ".pdf":
            raise SystemExit("Invalid corpus input: " + item["path"])
        if path.read_bytes()[:5] != b"%PDF-":
            raise SystemExit(f"{item['path']} is a Git LFS pointer; run: git lfs pull --include=\"corpus/evaluation/v1/**\"")
        if digest(path) != item["sha256"]:
            raise SystemExit("Corpus file changed: " + item["path"])
        cache = output / "cache" / f"{item['id']}-{proto['fingerprint'][:12]}.json"
        if cache.exists():
            record = read_json(cache)
        else:
            record = extract(path, item["sha256"], local_fields, kind)
            record["utc"] = datetime.now(UTC).isoformat()
            write_json(cache, record)
        if record["pages"] != item["pages"]:
            raise SystemExit("Page count mismatch for " + item["id"])
        records.append({**item, **record})
        print(f"{n:02d}/{len(manifest)} {item['id']}: {record['seconds']:.2f}s", flush=True)

    # Reference values enter only here, after extraction has finished.
    predictions = [{k: r[k] for k in ("id", "fields", "review_fields")} for r in records]
    (output / "predictions.jsonl").write_text(
        "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in predictions), encoding="utf-8")
    selected = {r["id"] for r in records}
    expected = [t for t in truth() if t["id"] in selected]
    scores = {scope: evaluate(expected, predictions, f) for scope, f in (("core", DEFAULT_FIELDS), ("all", fields))}
    results = {"utc": datetime.now(UTC).isoformat(), "protocol": proto, "records": records, "scores": scores}
    write_json(output / "results.json", results)
    render(output, results)
    return results


# --- Report ----------------------------------------------------------------------


def ratio(s: dict) -> str:
    return f"{s['correct']}/{s['fields']} ({100 * s['correct'] / s['fields']:.2f} %)" if s["fields"] else "–"


def render(output: Path, results: dict) -> None:
    scores = results["scores"]
    records = {r["id"]: r for r in results["records"]}
    notes = {(r["id"], corpus_key(d["field"])): d.get("note", "") for r in results["records"] for d in r["details"]}

    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scope", "group", "documents", "fields", "correct", "complete_documents",
                    "review_flagged", "incorrect_without_review"])
        for scope, s in scores.items():
            for group, g in s["summary"].items():
                w.writerow([scope, group, g["documents"], g["fields"], g["correct"], g["complete_documents"],
                            g["review_flagged"], g["incorrect_without_review"]])

    detail = []
    for d in scores["all"]["details"]:
        r = records[d["id"]]
        detail.append({
            "id": d["id"], "variant": r["variant"], "family": r["family"], "split": r["split"],
            "path": r["path"], "field": d["field"], "expected": d["expected"],
            "predicted": d["predicted"] if d["supplied"] else "not configured",
            "correct": d["correct"], "review": d["review_flagged"], "note": notes.get((d["id"], d["field"]), ""),
        })
    with (output / "fields.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(detail[0]) if detail else ["id"])
        w.writeheader()
        w.writerows(detail)

    esc = lambda v: html.escape("∅" if v is None else str(v))  # noqa: E731

    def table(head, rows):
        return ("<div class=scroll><table><thead><tr>" + "".join(f"<th scope=col>{esc(h)}</th>" for h in head)
                + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>" for row in rows)
                + "</tbody></table></div>")

    def md_table(head, rows):
        cell = lambda v: ("∅" if v is None else str(v)).replace("|", "\\|").replace("\n", " ")  # noqa: E731
        lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
        return "\n".join(lines)

    core, every = scores["core"]["summary"]["all"], scores["all"]["summary"]["all"]
    n_fields = len(scores["all"]["fields_evaluated"])
    summary_head = ["Scope", "Correct", "PDFs complete", "Review flags", "Wrong without review flag"]
    summary_rows = [
        ["Core fields (4)", ratio(core), core["complete_documents"], core["review_flagged"], core["incorrect_without_review"]],
        [f"All fields ({n_fields})", ratio(every), every["complete_documents"], every["review_flagged"], every["incorrect_without_review"]],
    ]
    per_field_head = ["Field", "Correct", "Review flags"]
    per_field_rows = [
        [f, f"{sum(d['correct'] for d in scores['all']['details'] if d['field'] == f)}/{core['documents']}",
         sum(d["review_flagged"] for d in scores["all"]["details"] if d["field"] == f)]
        for f in scores["all"]["fields_evaluated"]]
    groups_head = ["Group", "PDFs", "All fields", "Wrong without review flag"]
    groups_rows = [[g, s["documents"], ratio(s), s["incorrect_without_review"]]
                   for g, s in scores["all"]["summary"].items() if g != "all"]
    errors = [r for r in detail if not r["correct"]]
    remaining_head = ["PDF", "Variant", "Field", "Expected", "Predicted", "Review flag", "Note"]
    remaining_rows = [[r["id"], r["variant"], r["field"], r["expected"], r["predicted"],
                       "yes" if r["review"] else "NO", r["note"]] for r in errors]
    proto = results["protocol"]

    # GitHub renders README.md in the directory view, so the Markdown report is
    # readable in the repository without downloading report.html.
    markdown = f"""# Benchmark: {core['documents']} PDFs, document kind “{proto['document_kind']}”

Substrakt · corpus/evaluation/v1 · {results['utc'][:10]}

**Regression on a known synthetic corpus, not a blind test.** Local pipeline
only. Reference values were loaded after extraction, for scoring.

## Summary

{md_table(summary_head, summary_rows)}

Core fields: {', '.join(proto['core_fields'])}. A review flag never counts as a
correct value.

## Per field

{md_table(per_field_head, per_field_rows)}

## Per group

{md_table(groups_head, groups_rows)}

Variants of the same source document are not independent documents.

## Remaining deviations ({len(errors)})

{md_table(remaining_head, remaining_rows)}

## Files

Every field value is in [fields.csv](fields.csv) and [summary.csv](summary.csv);
[report.html](report.html) is the same report with filters and works offline.

## Protocol

Commit {proto['commit']}{' with uncommitted sidecar changes' if proto['sidecar_dirty'] else ''} ·
fingerprint {proto['fingerprint'][:12]} · protocol {proto['version']}
"""
    (output / "README.md").write_text(markdown, encoding="utf-8")

    summary = table(summary_head, summary_rows)
    per_field = table(per_field_head, per_field_rows)
    groups = table(groups_head, groups_rows)
    remaining = table(remaining_head, remaining_rows)
    data = json.dumps(detail, ensure_ascii=False).replace("<", "\\u003c")
    page = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Benchmark 84 PDFs</title>
<style>
:root{{--bg:#f5f7f4;--card:#fff;--ink:#132c34;--muted:#51666c;--line:#d5dfdf;--head:#edf3f2;--good:#086343;--bad:#9a3d21;--accent:#006c78}}
@media (prefers-color-scheme:dark){{:root{{--bg:#11181a;--card:#1a2427;--ink:#e3ecec;--muted:#9fb1b4;--line:#2d3b3e;--head:#22302f;--good:#6cc79d;--bad:#f0937a;--accent:#6fc7cf}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1280px;margin:auto;padding:32px 16px 64px}}h1{{font-size:clamp(28px,4vw,44px);line-height:1.15}}a{{color:var(--accent)}}
section{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:20px;margin:20px 0}}
.muted{{color:var(--muted);font-size:14px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{padding:8px 10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}}th{{background:var(--head)}}
.good{{color:var(--good)}}.bad{{color:var(--bad)}}.filters{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:10px}}
select,input{{font:inherit;padding:8px;border:1px solid var(--line);border-radius:4px;background:var(--card);color:var(--ink)}}
</style><main>
<p class=muted>Substrakt · corpus/evaluation/v1 · {esc(results['utc'][:10])}</p>
<h1>Benchmark: {core['documents']} PDFs, document kind “{esc(proto['document_kind'])}”</h1>
<p><strong>Regression on a known synthetic corpus, not a blind test.</strong> Local pipeline only. Reference values were loaded after extraction, for scoring.</p>
<section><h2>Summary</h2>{summary}<p class=muted>Core fields: {esc(', '.join(proto['core_fields']))}. A review flag never counts as a correct value.</p></section>
<section><h2>Per field</h2>{per_field}</section>
<section><h2>Per group</h2>{groups}<p class=muted>Variants of the same source document are not independent documents.</p></section>
<section><h2>Remaining deviations ({len(errors)})</h2>{remaining}</section>
<section><h2>All field values</h2><div class=filters><select id=status><option value="">All</option><option value=error>Deviations</option><option value=correct>Correct</option></select><input id=search placeholder="PDF or field, e.g. F08 or document_date"></div>
<p id=count class=muted aria-live=polite></p><div class=scroll><table><thead><tr><th>PDF</th><th>Field</th><th>Expected</th><th>Predicted</th><th>Result</th><th>Review flag</th><th>Note</th></tr></thead><tbody id=rows></tbody></table></div>
<p class=muted>Also in <a href="fields.csv">fields.csv</a> and <a href="summary.csv">summary.csv</a>.</p></section>
<section><h2>Protocol</h2><p class=muted>Commit {esc(proto['commit'])}{' with uncommitted sidecar changes' if proto['sidecar_dirty'] else ''} · fingerprint {esc(proto['fingerprint'][:12])} · protocol {esc(proto['version'])}</p></section>
</main><script>
const data={data};const esc=v=>String(v??'∅').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
function show(){{const s=document.getElementById('status').value,q=document.getElementById('search').value.toLowerCase();
const rows=data.filter(r=>(!s||(s==='error'?!r.correct:r.correct))&&(!q||(r.id+' '+r.field).toLowerCase().includes(q)));
document.getElementById('count').textContent=rows.length+' field comparisons';
document.getElementById('rows').innerHTML=rows.map(r=>'<tr><td>'+esc(r.id)+'</td><td>'+esc(r.field)+'</td><td>'+esc(r.expected)+'</td><td>'+esc(r.predicted)+'</td><td class="'+(r.correct?'good':'bad')+'">'+(r.correct?'correct':'deviation')+'</td><td>'+(r.review?'yes':'no')+'</td><td>'+esc(r.note)+'</td></tr>').join('')}}
for(const id of ['status','search'])document.getElementById(id).addEventListener('input',show);show();
</script></html>
"""
    (output / "report.html").write_text(page, encoding="utf-8")


# --- Verification ----------------------------------------------------------------


def verify(output: Path) -> str:
    """Re-score the stored predictions independently and check the report files."""
    results = read_json(output / "results.json")
    predictions = read_jsonl(output / "predictions.jsonl")
    assert predictions == [{k: r[k] for k in ("id", "fields", "review_fields")} for r in results["records"]]
    manifest = {m["id"]: m for m in read_json(CORPUS / "manifest.json")}
    assert results["protocol"]["manifest_sha256"] == digest(CORPUS / "manifest.json")
    assert all(manifest[r["id"]]["sha256"] == r["sha256"] for r in results["records"])
    selected = {p["id"] for p in predictions}
    expected = [t for t in truth() if t["id"] in selected]
    proto = results["protocol"]
    for scope, fields in (("core", proto["core_fields"]), ("all", proto["all_fields"])):
        assert evaluate(expected, predictions, fields) == results["scores"][scope], scope
    with (output / "fields.csv").open(encoding="utf-8", newline="") as f:
        assert len(list(csv.DictReader(f))) == len(expected) * len(proto["all_fields"])
    core = results["scores"]["core"]["summary"]["all"]
    every = results["scores"]["all"]["summary"]["all"]
    return (f"OK: {len(predictions)} PDFs re-scored. Core {ratio(core)}, all {ratio(every)}, "
            f"wrong without review flag: {every['incorrect_without_review']}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", type=Path, help="report directory (default: corpus/evaluation/reports/<date>)")
    parser.add_argument("--kind", default="invoice", help="document kind from sidecar/substrakt/document_kinds/")
    parser.add_argument("--limit", type=int, help="only the first N PDFs of the manifest (smoke test)")
    parser.add_argument("--verify", type=Path, metavar="DIR", help="only verify an existing report directory")
    parser.add_argument("--render", type=Path, metavar="DIR", help="re-create the report files from a stored results.json")
    args = parser.parse_args()
    if args.render:
        output = args.render.resolve()
        render(output, read_json(output / "results.json"))
        print(verify(output))
        return
    if args.verify:
        print(verify(args.verify.resolve()))
        return
    output = (args.output or REPORTS / date.today().isoformat()).resolve()
    run(output, args.kind, args.limit)
    print(verify(output))
    print(f"Report: {output / 'README.md'} and report.html")


if __name__ == "__main__":
    main()

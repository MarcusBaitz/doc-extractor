#!/usr/bin/env python3
"""Benchmark for vlm."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from pathlib import Path

os.environ.setdefault("SUBSTRAKT_DEV", "1")

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "measurement"
PROTOCOLS = ROOT / "docs" / "measurements"

SERVER = os.environ.get("SUBSTRAKT_VLM", "http://127.0.0.1:18080")




SCHEMA = {
    "type": "object",
    "properties": {
        "document_number": {"type": "string"},
        "document_date": {"type": "string"},
        "total_amount": {"type": "string"},
        "vat_id": {"type": "string"},
    },
    "required": ["document_number", "document_date", "total_amount", "vat_id"],
}


@dataclass
class ReadingResult:
    document: int
    quality: str
    seconds: float
    tokens: int
    tokens_per_second: float
    match: float
    truncated: bool


@dataclass
class SchemaResult:
    document: int
    quality: str
    seconds: float
    valid_json: bool
    schema_conforms: bool
    fields_correct: int
    fields_total: int
    values: dict[str, str] = dataclass_field(default_factory=dict)
    expected: dict[str, str] = dataclass_field(default_factory=dict)


def question(body: dict, timeout: int = 900) -> tuple[dict, float]:
    req = urllib.request.Request(
        f"{SERVER}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    start_time = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response), time.perf_counter() - start_time


def image_content(path: Path, text: str) -> list[dict]:
    b64 = base64.b64encode(path.read_bytes()).decode()
    return [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": text},
    ]


def expected_values(reference: str) -> dict[str, str]:
    single_line = re.sub(r"\s+", " ", reference)
    match = {}
    for name, patterns in [
        ("document_number", r"Belegnummer:\s*(\S+)"),
        ("document_date", r"Belegdatum:\s*(\d{2}\.\d{2}\.\d{4})"),
        ("total_amount", r"Gesamtbetrag\s+([\d.]+,\d{2})"),
        ("vat_id", r"USt-IdNr\.:\s*(DE\d+)"),
    ]:
        m = re.search(patterns, single_line)
        match[name] = m.group(1) if m else ""
    return match


def matches(expected: str, actual: object) -> bool:
    if not expected:
        return False
    a = re.sub(r"[\s€]|EUR", "", str(expected)).strip().lower()
    b = re.sub(r"[\s€]|EUR", "", str(actual)).strip().lower()
    return a == b


# --- Measurement 1 -------------------------------------------------------------


def read_stage(documents: list[dict], qualities: list[str]) -> list[ReadingResult]:
    
    
    sys.path.insert(0, str(Path(__file__).parent))
    from ocr import match_rate

    results: list[ReadingResult] = []

    for quality in qualities:
        for entry in documents:
            scan = CORPUS / entry["scans"][quality]["file"]
            reference = (CORPUS / entry["reference"]).read_text(encoding="utf-8")

            try:
                response, duration = question({
                    "messages": [{"role": "user",
                                  "content": image_content(scan, "Convert this page to docling.")}],
                    "max_tokens": 4096,
                    "temperature": 0.0,
                })
            except Exception as exc:
                print(f"  document_{entry['index']:02d}/{quality}: {exc}")
                continue

            choice = response["choices"][0]
            raw = choice["message"]["content"]
            
            plain_text = re.sub(r"<[^>]+>", " ", raw)
            tokens = response.get("usage", {}).get("completion_tokens", 0)

            results.append(ReadingResult(
                document=entry["index"],
                quality=quality,
                seconds=round(duration, 2),
                tokens=tokens,
                tokens_per_second=round(tokens / max(duration, 0.01), 1),
                match=round(match_rate(reference, plain_text), 4),
                truncated=choice.get("finish_reason") == "length",
            ))

        part = [e for e in results if e.quality == quality]
        if part:
            print(f"  {quality:<9} Match {statistics.median(e.match for e in part):6.1%}  "
                  f"{statistics.median(e.seconds for e in part):5.1f} s/page  "
                  f"{statistics.median(e.tokens_per_second for e in part):5.1f} tok/s")

    return results


# --- Measurement 2 -------------------------------------------------------------


def constrained(documents: list[dict], quality: str) -> list[SchemaResult]:
    results: list[SchemaResult] = []

    for entry in documents:
        scan = CORPUS / entry["scans"][quality]["file"]
        reference = (CORPUS / entry["reference"]).read_text(encoding="utf-8")
        expected = expected_values(reference)

        try:
            response, duration = question({
                "messages": [{"role": "user", "content": image_content(
                    scan,
                    "Extract document_number, document_date, total_amount and vat_id "
                    "from this document as JSON.")}],
                "max_tokens": 256,
                "temperature": 0.0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "document", "schema": SCHEMA, "strict": True},
                },
            })
        except Exception as exc:
            print(f"  document_{entry['index']:02d}: request rejected — {exc}")
            results.append(SchemaResult(
                document=entry["index"], quality=quality, seconds=0.0,
                valid_json=False, schema_conforms=False,
                fields_correct=0, fields_total=len(SCHEMA["required"]), expected=expected,
            ))
            continue

        raw = response["choices"][0]["message"]["content"]
        try:
            actual = json.loads(raw)
            valid = True
        except json.JSONDecodeError:
            actual, valid = {}, False

        conforms = valid and all(k in actual for k in SCHEMA["required"])
        correct = sum(1 for k, v in expected.items() if matches(v, actual.get(k, ""))) if valid else 0

        results.append(SchemaResult(
            document=entry["index"], quality=quality, seconds=round(duration, 2),
            valid_json=valid, schema_conforms=conforms,
            fields_correct=correct, fields_total=len(expected),
            values={k: str(actual.get(k, ""))[:60] for k in expected},
            expected=expected,
        ))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qualities", default="clean,medium,poor")
    parser.add_argument("--documents", type=int, default=None)
    parser.add_argument("--schema-quality", default="medium")
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    try:
        with urllib.request.urlopen(f"{SERVER}/health", timeout=5):
            pass
    except Exception:
        print(f"No VLM server at {SERVER}. Start it with:\n"
              "  docker run -d --name substrakt-vlm --cpus=4 --memory=8g \\\n"
              "    -v $PWD/models/vlm:/models:ro -p 18080:8080 \\\n"
              "    ghcr.io/ggml-org/llama.cpp:server \\\n"
              "    -m /models/granite-docling-258M-Q8_0.gguf \\\n"
              "    --mmproj /models/mmproj-granite-docling-258M-Q8_0.gguf \\\n"
              "    --host 0.0.0.0 --port 8080 --threads 4 --ctx-size 8192")
        return 1

    directory = json.loads((CORPUS / "directory.json").read_text(encoding="utf-8"))
    documents = directory["documents"][: args.documents] if args.documents else directory["documents"]
    qualities = [q.strip() for q in args.qualities.split(",") if q.strip()]

    print("Measurement 1 — document VLM on CPU (granite-docling-258M, 4 threads)\n")
    reading = read_stage(documents, qualities)

    print("\nMeasurement 2 — constrained decoding with a multimodal model\n")
    schema = constrained(documents, args.schema_quality)

    valid = sum(1 for s in schema if s.valid_json)
    conforms = sum(1 for s in schema if s.schema_conforms)
    correct = sum(s.fields_correct for s in schema)
    total = sum(s.fields_total for s in schema)

    print(f"  valid JSON:        {valid}/{len(schema)}")
    print(f"  schema conforms:   {conforms}/{len(schema)}")
    print(f"  fields correct:    {correct}/{total}  ({correct / max(total, 1):.0%})")
    print(f"  time:              {statistics.median(s.seconds for s in schema):.1f} s")

    print("\n  Examples of schema-conforming but incorrect values:")
    shown = 0
    for s in schema:
        for field, expected in s.expected.items():
            actual = s.values.get(field, "")
            if expected and not matches(expected, actual) and shown < 6:
                print(f"    document_{s.document:02d}.{field}: expected {expected!r}, actual {actual!r}")
                shown += 1

    if args.write:
        PROTOCOLS.mkdir(parents=True, exist_ok=True)
        tag = args.timestamp or "current"
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in tag)
        (PROTOCOLS / f"stage0-vlm-{safe}.json").write_text(
            json.dumps({
                "measurement": "Stage 0 / 1 and 2 — document VLM on CPU",
                "model": "granite-docling-258M-Q8_0",
                "runtime": "llama.cpp in a container, CPU, 4 threads",
                "read_stage": [asdict(e) for e in reading],
                "constrained": [asdict(s) for s in schema],
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nReport: {PROTOCOLS / f'stage0-vlm-{safe}.json'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Benchmark for ocr."""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

os.environ.setdefault("SUBSTRAKT_DEV", "1")

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "measurement"
TESSDATA = ROOT / "models" / "tessdata"
PROTOCOLS = ROOT / "docs" / "measurements"


@dataclass
class ExtractionResult:
    engine: str
    quality: str
    dpi: int
    document: int
    match: float
    cer_seq: float
    wer_seq: float
    seconds: float
    reference_characters: int
    recognized_characters: int
    confidence: float | None = None


@dataclass
class Summary:
    engine: str
    quality: str
    dpi: int
    documents: int
    match_median: float
    match_min: float
    cer_seq_median: float
    wer_seq_median: float
    s_median: float
    s_min: float
    s_max: float
    confidence: float | None = None
    error: list[str] = field(default_factory=list)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def match_rate(reference: str, recognized: str) -> float:
    ref_kette = normalize(reference).replace(" ", "")
    ocr_kette = normalize(recognized).replace(" ", "")

    words = normalize(reference).split()
    if not words:
        return 1.0

    
    
    rest = ocr_kette
    match = 0
    for word in words:
        kern = word.replace(" ", "")
        pos = rest.find(kern)
        if pos >= 0:
            match += 1
            rest = rest[:pos] + rest[pos + len(kern) :]

    del ref_kette  
    return match / len(words)


def error_rates(reference: str, recognized: str) -> tuple[float, float, float]:
    from rapidfuzz.distance import Levenshtein

    r = normalize(reference)
    e = normalize(recognized)
    rw, ew = r.split(), e.split()

    cer_seq = Levenshtein.distance(r, e) / max(len(r), 1)
    wer_seq = Levenshtein.distance(rw, ew) / max(len(rw), 1)

    return (match_rate(reference, recognized), min(cer_seq, 1.0), min(wer_seq, 1.0))


# --- Engines ---------------------------------------------------------------


def tesseract(image: Path, threads: int) -> tuple[str, float | None]:
    environment = {
        **os.environ,
        "TESSDATA_PREFIX": str(TESSDATA),
        "OMP_THREAD_LIMIT": str(threads),
    }

    run = subprocess.run(
        ["tesseract", str(image), "stdout", "-l", "deu", "--psm", "3"],
        capture_output=True, text=True, env=environment, timeout=300,
    )
    if run.returncode != 0:
        raise RuntimeError(f"Tesseract: {run.stderr.strip()[:200]}")

    return run.stdout, None


def tesseract_with_confidence(image: Path, threads: int) -> float | None:
    environment = {
        **os.environ,
        "TESSDATA_PREFIX": str(TESSDATA),
        "OMP_THREAD_LIMIT": str(threads),
    }
    run = subprocess.run(
        ["tesseract", str(image), "stdout", "-l", "deu", "--psm", "3", "tsv"],
        capture_output=True, text=True, env=environment, timeout=300,
    )
    if run.returncode != 0:
        return None

    values = []
    for row in run.stdout.splitlines()[1:]:
        fields = row.split("\t")
        if len(fields) >= 12 and fields[11].strip():
            try:
                confidence_value = float(fields[10])
                if confidence_value >= 0:
                    values.append(confidence_value)
            except ValueError:
                pass
    return statistics.mean(values) / 100 if values else None


_rapid = None


def rapidocr(image: Path, threads: int) -> tuple[str, float | None]:
    global _rapid
    if _rapid is None:
        from rapidocr_onnxruntime import RapidOCR

        _rapid = RapidOCR(
            intra_op_num_threads=threads,
            inter_op_num_threads=threads,
        )

    result, _ = _rapid(str(image))
    if not result:
        return "", None

    # ExtractionResult: [[box, text, confidence], …] in reading order.
    rows = [entry[1] for entry in result]
    confidences = [float(entry[2]) for entry in result if len(entry) > 2]

    return "\n".join(rows), (statistics.mean(confidences) if confidences else None)


ENGINES = {"tesseract": tesseract, "rapidocr": rapidocr}


# --- Measurement run -------------------------------------------------------


def measure(
    engines: list[str], qualities: list[str], threads: int, documents: int | None
) -> list[ExtractionResult]:
    directory = json.loads((CORPUS / "directory.json").read_text(encoding="utf-8"))
    entries = directory["documents"][:documents] if documents else directory["documents"]

    results: list[ExtractionResult] = []

    for name in engines:
        function = ENGINES[name]

        
        first = entries[0]["scans"][qualities[0]]["file"]
        try:
            function(CORPUS / first, threads)
        except Exception as exc:
            print(f"  {name}: unavailable ({exc})")
            continue

        for quality in qualities:
            for entry in entries:
                scan = CORPUS / entry["scans"][quality]["file"]
                reference = (CORPUS / entry["reference"]).read_text(encoding="utf-8")

                try:
                    start_time = time.perf_counter()
                    text, confidence = function(scan, threads)
                    duration = time.perf_counter() - start_time
                except Exception as exc:
                    print(f"  {name}/{quality}/document_{entry['index']:02d}: {exc}")
                    continue

                if name == "tesseract" and confidence is None:
                    confidence = tesseract_with_confidence(scan, threads)

                match, cer_seq, wer_seq = error_rates(reference, text)
                results.append(
                    ExtractionResult(
                        engine=name,
                        quality=quality,
                        dpi=entry["scans"][quality]["dpi"],
                        document=entry["index"],
                        match=round(match, 4),
                        cer_seq=round(cer_seq, 4),
                        wer_seq=round(wer_seq, 4),
                        seconds=round(duration, 3),
                        reference_characters=len(normalize(reference)),
                        recognized_characters=len(normalize(text)),
                        confidence=round(confidence, 3) if confidence else None,
                    )
                )

            completed = [e for e in results if e.engine == name and e.quality == quality]
            if completed:
                print(
                    f"  {name:<10} {quality:<9} "
                    f"Match {statistics.median(e.match for e in completed):6.1%}  "
                    f"(CER_seq {statistics.median(e.cer_seq for e in completed):5.1%})  "
                    f"{statistics.median(e.seconds for e in completed):5.2f} s/page"
                )

    return results


def summarize(results: list[ExtractionResult]) -> list[Summary]:
    summaries: list[Summary] = []
    key = sorted({(e.engine, e.quality, e.dpi) for e in results})

    for engine, quality, dpi in key:
        part = [e for e in results if e.engine == engine and e.quality == quality]
        confidences = [e.confidence for e in part if e.confidence is not None]
        summaries.append(
            Summary(
                engine=engine,
                quality=quality,
                dpi=dpi,
                documents=len(part),
                match_median=round(statistics.median(e.match for e in part), 4),
                match_min=round(min(e.match for e in part), 4),
                cer_seq_median=round(statistics.median(e.cer_seq for e in part), 4),
                wer_seq_median=round(statistics.median(e.wer_seq for e in part), 4),
                s_median=round(statistics.median(e.seconds for e in part), 3),
                s_min=round(min(e.seconds for e in part), 3),
                s_max=round(max(e.seconds for e in part), 3),
                confidence=round(statistics.mean(confidences), 3) if confidences else None,
            )
        )
    return summaries


def table(summaries: list[Summary]) -> str:
    rows = [
        "| Engine | Quality | dpi | Match | worst | CER_seq | WER_seq | s/page | Confidence |",
        "|---|---|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for summary in summaries:
        rows.append(
            f"| {summary.engine} | {summary.quality} | {summary.dpi} | **{summary.match_median:.1%}** | "
            f"{summary.match_min:.1%} | {summary.cer_seq_median:.1%} | {summary.wer_seq_median:.1%} | "
            f"{summary.s_median:.2f} ({summary.s_min:.2f}–{summary.s_max:.2f}) | "
            f"{f'{summary.confidence:.0%}' if summary.confidence else '—'} |"
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engines", default="tesseract,rapidocr")
    parser.add_argument("--qualities", default="clean,good,medium,poor")
    parser.add_argument(
        "--threads", type=int, default=4,
        help="Thread count. Default 4 models a laptop under load.",
    )
    parser.add_argument("--documents", type=int, default=None)
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if not (CORPUS / "directory.json").exists():
        print("Measurement corpus is missing. First run: uv run python ../corpus/measurement_corpus.py")
        return 1

    engines = [e.strip() for e in args.engines.split(",") if e.strip() in ENGINES]
    qualities = [q.strip() for q in args.qualities.split(",") if q.strip()]

    import platform

    print("Measurement 3 — classical OCR reference")
    print(f"Machine: {platform.machine()}, {os.cpu_count()} cores available, "
          f"{args.threads} threads used\n")

    results = measure(engines, qualities, args.threads, args.documents)
    if not results:
        print("No results.")
        return 1

    summaries = summarize(results)
    print("\n" + table(summaries))

    if args.write:
        PROTOCOLS.mkdir(parents=True, exist_ok=True)
        tag = args.timestamp or "current"
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in tag)

        (PROTOCOLS / f"stage0-ocr-{safe}.json").write_text(
            json.dumps(
                {
                    "measurement": "Stage 0 / 3 — classical OCR reference",
                    "threads": args.threads,
                    "available_cores": os.cpu_count(),
                    "corpus": "synthetic, 10 documents, 4 quality levels",
                    "summary": [asdict(summary) for summary in summaries],
                    "individual_values": [asdict(e) for e in results],
                },
                indent=2, ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nReport: {PROTOCOLS / f'stage0-ocr-{safe}.json'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

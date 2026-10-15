#!/usr/bin/env python3
"""Benchmark for server."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import os
import statistics
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

os.environ.setdefault("SUBSTRAKT_DEV", "1")

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "measurement"
PROTOCOLS = ROOT / "docs" / "measurements"
SERVER = os.environ.get("SUBSTRAKT_SERVER", "http://127.0.0.1:18000")


@dataclass
class ExtractionRun:
    parallel: int
    pages: int
    wall_time_seconds: float
    pages_per_minute: float
    seconds_per_page_median: float
    seconds_per_page_max: float
    total_tokens: int
    tokens_per_second: float
    error: int


def model_name() -> str:
    with urllib.request.urlopen(f"{SERVER}/v1/models", timeout=30) as r:
        return json.load(r)["data"][0]["id"]


def one_page(model: str, image: Path, max_tokens: int) -> tuple[float, int]:
    b64 = base64.b64encode(image.read_bytes()).decode()
    body = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": "Extract all text from this document."},
        ]}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        f"{SERVER}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    start_time = time.perf_counter()
    with urllib.request.urlopen(req, timeout=1800) as response:
        d = json.load(response)
    return time.perf_counter() - start_time, d.get("usage", {}).get("completion_tokens", 0)


def measure(model: str, images: list[Path], parallel: int, max_tokens: int) -> ExtractionRun:
    times: list[float] = []
    tokens = 0
    error = 0

    start_time = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as pool:
        jobs = [pool.submit(one_page, model, b, max_tokens) for b in images]
        for job in concurrent.futures.as_completed(jobs):
            try:
                duration, tok = job.result()
                times.append(duration)
                tokens += tok
            except Exception as exc:
                error += 1
                print(f"    Error: {str(exc)[:120]}")
    wall_time = time.perf_counter() - start_time

    return ExtractionRun(
        parallel=parallel,
        pages=len(times),
        wall_time_seconds=round(wall_time, 2),
        pages_per_minute=round(len(times) / max(wall_time, 0.01) * 60, 1),
        seconds_per_page_median=round(statistics.median(times), 2) if times else 0.0,
        seconds_per_page_max=round(max(times), 2) if times else 0.0,
        total_tokens=tokens,
        tokens_per_second=round(tokens / max(wall_time, 0.01), 1),
        error=error,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality", default="medium",
                        help="150 dpi was the useful value in measurement 1")
    parser.add_argument("--parallel", default="1,2,4,8")
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--timestamp", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    try:
        model = model_name()
    except Exception as exc:
        print(f"No vLLM server at {SERVER} ({exc}). Start it with:\n"
              "  docker run -d --name substrakt-vllm --gpus all \\\n"
              "    -v ~/.cache/huggingface:/root/.cache/huggingface -p 18000:8000 \\\n"
              "    vllm/vllm-openai:latest --model Qwen/Qwen2.5-VL-7B-Instruct-AWQ \\\n"
              "    --max-model-len 8192 --gpu-memory-utilization 0.92")
        return 1

    directory = json.loads((CORPUS / "directory.json").read_text(encoding="utf-8"))
    images = [CORPUS / e["scans"][args.quality]["file"] for e in directory["documents"]]

    print("Measurement 4 — server throughput")
    print(f"Model:   {model}")
    print(f"Corpus:  {len(images)} pages, quality {args.quality}")
    print("GPU:     RTX 5070 Ti (16 GB, Blackwell), not the planned L4\n")

    
    print("  warming up …")
    try:
        one_page(model, images[0], 64)
    except Exception as exc:
        print(f"  warm-up failed: {exc}")
        return 1

    runs = []
    for level in [int(p) for p in args.parallel.split(",")]:
        run = measure(model, images, level, args.max_tokens)
        runs.append(run)
        print(f"  parallel {level:>2}:  {run.pages_per_minute:>5.1f} pages/min  "
              f"{run.seconds_per_page_median:>5.2f} s/page (max {run.seconds_per_page_max:.2f})  "
              f"{run.tokens_per_second:>6.1f} tok/s"
              + (f"  error: {run.error}" if run.error else ""))

    best = max(runs, key=lambda x: x.pages_per_minute)
    print(f"\nBest result: {best.pages_per_minute:.1f} pages/min with "
          f"{best.parallel} parallel requests")

    if args.write:
        PROTOCOLS.mkdir(parents=True, exist_ok=True)
        tag = args.timestamp or "current"
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in tag)
        (PROTOCOLS / f"stage0-server-{safe}.json").write_text(
            json.dumps({
                "measurement": "Stage 0 / 4 — server throughput",
                "model": model,
                "gpu": "NVIDIA GeForce RTX 5070 Ti, 16 GB, Blackwell",
                "deviation": "The plan requires an NVIDIA L4 24 GB, which was unavailable",
                "quality": args.quality,
                "max_tokens": args.max_tokens,
                "runs": [asdict(x) for x in runs],
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Report: {PROTOCOLS / f'stage0-server-{safe}.json'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

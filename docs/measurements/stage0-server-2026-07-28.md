# Stage 0, measurement 4: throughput of the server variant

**28 July 2026** · Is a GPU server in the customer network worth it? The
architecture decision estimated “10–40 pages per minute — estimated, not
measured”.

## Set-up and deviations

| | |
|---|---|
| Model | `Qwen/Qwen2.5-VL-7B-Instruct-AWQ` (Apache-2.0, 4-bit AWQ) |
| Runtime | vLLM 0.26.0, torch 2.11+cu130 |
| Card | **RTX 5070 Ti** (16 GB, Blackwell sm_120) — **not** the planned L4 |
| KV cache | 7.01 GiB, 131,264 tokens |
| Corpus | 10 pages, 150 dpi |

Three deviations that bias the number downwards and must therefore be named:

1. **Different card.** The plan calls for an L4 (24 GB, Ada). Blackwell has
   more raw compute but 8 GB less memory — and that turns out to be the
   limiting factor (see below).
2. **`--enforce-eager`.** CUDA graph capture had to be switched off because
   JIT compilation fails under WSL2. This costs throughput.
3. **`TORCH_SDPA` instead of FlashInfer**, for the same reason. Also slower
   than the default configuration.

A cleanly installed L4 on real Linux therefore delivers **more** than the
values measured here. How much more is open.

## Result

| parallel requests | pages/min | s/page (median) | s/page (max) | tok/s |
|--:|--:|--:|--:|--:|
| 1 | 5.4 | 10.84 | 13.33 | 40.8 |
| **2** | **10.1** | 11.83 | 13.12 | 76.1 |
| 4 | 7.1 | 35.82 | 59.16 | 53.1 |
| 8 | 5.4 | 98.59 | 100.17 | 40.6 |

**Best value: 10.1 pages/min with two parallel requests** — the lower end of
the estimated range.

## Memory limits, not compute

The most striking finding: from four parallel requests on, **throughput
collapses**. The time per page triples from 11.8 s to 35.8 s, with eight
requests it rises to 98.6 s — and overall throughput falls back to the value
of a single request.

The reason is the KV cache. A page image takes about 880 prompt tokens; with
8192 context and 7 GiB cache there is room for about two simultaneous image
requests. Beyond that vLLM has to preempt requests and read them in again —
compute that is spent twice.

**For the purchasing decision this is the most important point.** An L4 with
24 GB has about three times the cache capacity and should deliver clearly
more throughput than this consumer card despite slower compute units. With
vision models VRAM counts more than compute — and that is exactly the
criterion in which server cards differ from consumer cards.

## The comparison that puts the server variant in question

| Path | pages/min | Hardware |
|---|--:|---|
| **Tesseract, CPU, 4 threads** | **125** | none extra |
| granite-docling-258M, CPU | 4.4 | none extra |
| Qwen2.5-VL-7B-AWQ, GPU | 10.1 | 1,500–3,000 EUR |

**Tesseract on the CPU is twelve times faster than the 7B model on the
GPU** — and, according to [measurement 3](stage0-ocr-2026-07-28.md), also
more accurate (98.8% against the 96–98% of the VLM class).

Two orders of magnitude of model size and a dedicated graphics card bring no
advantage for **printed business documents**. The GPU delivers only 2.3 times
the 258M model on CPU, at 27 times the model size.

## What this means for the architecture

**The server variant remains sensible — but not for OCR.**

The benefit lies in **path B**, free field extraction by a text LLM: there
the estimate is 10–50 s per document on CPU, and a server turns that into
seconds. The two-mode architecture therefore stays right, but its
justification shifts:

* **Not** “vision models become usable on the server” — they become usable,
  but they are not needed.
* **But** “path B becomes interactive, and mass processing becomes possible”.

The reading stage stays with classical OCR, local, without extra hardware.
This simplifies the product: a customer needs the server only when extracting
a lot — not because their scans are poor.

## Five hurdles under WSL2

Worth mentioning because it affects evaluation options at the customer:
**vLLM does not start under WSL2 without five interventions**, none of which
can be inferred from the respective error message.

| Symptom | Cause | Remedy |
|---|---|---|
| `failed to discover GPU vendor from CDI` | NVIDIA Container Toolkit missing | install the toolkit (root) or run vLLM without Docker |
| `RuntimeError: UVA is not available` | pinned memory is off by default under WSL despite kernel 6.6 | `VLLM_WSL2_ENABLE_PIN_MEMORY=1` |
| `Could not find nvcc` | CUDA toolkit lives in `site-packages/nvidia/cu13`, `/usr/local/cuda` is searched | set `CUDA_HOME` |
| `FileNotFoundError: 'ninja'` | build tool missing | `pip install ninja` |
| `CUDA compiler and toolkit headers are incompatible` | nvcc 13.3 against PyTorch headers from CUDA 13.0 | switch off FlashInfer and CUDA graphs |

**Consequence for sales:** the obvious way for a customer to try the server
variant — a Windows workstation with WSL2 — is blocked. Anyone who wants to
evaluate needs real Linux with a matching CUDA toolkit, i.e. the same
environment as in later operation. This belongs in the operations
documentation as soon as the server variant is built (stage 3).

## Limitations

* Consumer card instead of server card, and the memory limit demonstrably
  biases the result.
* Conservative configuration (`--enforce-eager`, `TORCH_SDPA`).
* Only one model and only one context length (8192).
* Ten pages per load level — enough for the order of magnitude, too few for
  reliable percentiles.
* Batching through concurrent HTTP requests, not through vLLM's offline batch
  interface. The latter would be faster for pure mass processing.

## Reproducing

Real Linux with a CUDA toolkit is required. Under WSL2, additionally the five
interventions above.

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct-AWQ \
  --port 18000 --max-model-len 8192 --gpu-memory-utilization 0.88

cd sidecar && uv run python ../bench/server.py --write
```

The commands use today's flag; the run on 28 July 2026 used the former German
flag. Raw data: [`stage0-server-2026-07-28.json`](stage0-server-2026-07-28.json).

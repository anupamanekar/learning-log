---
title: "Dev Log: GPU Infrastructure Cost Comparison for Batch Ingestion"
slug: "gpu-infrastructure-cost-comparison-batch-ingestion"
project: "market-signals-platform"
topic: "claude-vs-runpod-cost-and-provider-switch"
date: "2026-10-10"
status: "Published"
tags: ["runpod", "gpu", "infrastructure", "cost-optimization", "ollama", "dev-log"]
references:
  - "market-signals-platform/docs/RUNPOD_SETUP_GUIDE.md:21-52"
  - "market-signals-platform/docs/ARCHITECTURE.md:70-78"
  - "market-signals-platform/docs/PHASE_13.md:100-103"
---

# Dev Log: GPU Infrastructure Cost Comparison for Batch Ingestion

**Project**: `market-signals-platform`  
**Source Ref**: [`docs/RUNPOD_SETUP_GUIDE.md:21-52`](file:///Users/anupmanekar/DevWorkspace/market-signals-platform/docs/RUNPOD_SETUP_GUIDE.md#L21-L52)  
**Config Reference**: [`docs/ARCHITECTURE.md:70-78`](file:///Users/anupmanekar/DevWorkspace/market-signals-platform/docs/ARCHITECTURE.md#L70-L78)

---

## Context & Workload

We run a 100% LLM-driven Wikipedia ingestion pipeline (`backend/scripts/ingest_wikipedia.py`). The pipeline extracts structured profiles and historical event timestamps into SQLite.

- **Batch Size**: 1,000 to 5,000 entity profiles per ingestion run.
- **Input Size**: 4,000 to 12,000 tokens of raw Markdown per entity.
- **Target Model**: `llama3.1:8b` (4-bit/8-bit quant via Ollama) + `nomic-embed-text` (768-dim embeddings).

---

## Infrastructure Benchmarks & Cost Breakdown

| Infrastructure Tier | GPU / Hardware | Hourly Cost | Time per Profile | Throughput (24h) | Cost per 1,000 Profiles | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Local Dev Machine** | Apple M-series CPU | \$0.00 | ~600s (10 min) | ~140 profiles | \$0.00 | Freezes local dev; unviable for large batches |
| **AWS EC2 (`g5.xlarge`)** | 1x NVIDIA A10G (24GB) | ~\$1.01/hr | ~48s | ~1,800 profiles | ~\$13.40 | High ingress/egress fees, EBS volume costs |
| **GCP (`a2-highgpu-1g`)** | 1x NVIDIA A100 (40GB) | ~\$3.67/hr | ~22s | ~3,900 profiles | ~\$22.40 | Enterprise reliability; severe cost overkill for 8B models |
| **RunPod Secure Cloud** | 1x NVIDIA RTX 4090 (24GB) | ~\$0.69/hr | ~35s | ~2,400 profiles | ~\$6.70 | Guaranteed uptime, dedicated pod |
| **RunPod Community Cloud** | 1x NVIDIA RTX 4090 (24GB) | **~\$0.44/hr** | **~35s** | **~2,400 profiles** | **~\$4.28** | Best cost-to-performance ratio |
| **RunPod 4-Worker (`NUM_PARALLEL=4`)** | 1x NVIDIA RTX 4090 (24GB) | **~\$0.44/hr** | **~20s effective** | **~4,300 profiles** | **~\$2.45** | Maximizes VRAM utilization per dollar |

---

## Configuration & Setup Gotchas

### 1. VRAM Pinning (`RUNPOD_SETUP_GUIDE.md:32-40`)
By default, Ollama unloads inactive models after 5 minutes. If a batch pauses between HTTP requests, reloading `llama3.1:8b` from disk takes 12-15 seconds.
```bash
# Keep weights in GPU VRAM indefinitely
OLLAMA_KEEP_ALIVE=-1
OLLAMA_NUM_PARALLEL=4
CUDA_VISIBLE_DEVICES=0
```

### 2. Avoiding Re-download Overhead (`RUNPOD_SETUP_GUIDE.md:46-52`)
Every pod stop/restart deletes the container filesystem unless mapped to a persistent volume.
```text
Container Disk: 20 GB (ephemeral)
Volume Disk:    30 GB mapped to /root/.ollama (persistent)
```
Without mapping `/root/.ollama` to volume storage, the pod spends 10 minutes re-pulling 7.3 GB of weights on every startup.

### 3. CPU Fallback Trap (`RUNPOD_SETUP_GUIDE.md:71-78`)
If the Docker image lacks CUDA runtime libraries, Ollama silently falls back to CPU execution without throwing an error. Always verify via web terminal:
```bash
ollama ps
# Expected:
# NAME           SIZE      PROCESSOR    CONTEXT
# llama3.1:8b    7.3 GB    100% GPU     4096
```
If it says `100% CPU`, rebuild the pod using a PyTorch 2.1 / CUDA 12 base template.

---

## Takeaways

- For batch processing open weights (8B–14B models), **RunPod Community Cloud RTX 4090 at \$0.44/hr** beats major hyperscalers by **3x to 5x** on pure cost per token.
- Multi-threading inference via `OLLAMA_NUM_PARALLEL=4` on a 24GB VRAM card cuts effective cost per 1,000 profiles from \$4.28 to \$2.45.
- Always attach persistent volume storage to `/root/.ollama` to avoid burning bandwidth and startup latency on model pulls.

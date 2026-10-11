---
id: "claude-vs-runpod-cost-and-provider-switch"
title: "Claude API vs RunPod Self-Hosted GPU: Cost-per-Profile Analysis and .env Provider Switching"
project: "astrological-signals-engine"
date: "2026-10-10"
category: "performance-and-infra"
tags: ["runpod", "claude", "cost-optimization", "llm", "infrastructure", "environment-config"]
severity_or_impact: "High"
showcase_potential: "Blog"
status: "Synthesized"
source_references:
  - "backend/app/engine/llm/provider.py:367-381"
  - "docs/RUNPOD_SETUP_GUIDE.md:21-52"
  - "commit:bdf9f27"
---

# Claude API vs RunPod Self-Hosted GPU: Cost-per-Profile Analysis and .env Provider Switching

## Problem
The Wikipedia ingestion pipeline (`backend/scripts/ingest_wikipedia.py`) processes batches of 1,000–5,000 entities, parsing 4k–12k tokens of raw text per profile into structured events and biographical metadata. Local M-series CPU execution was infeasible (~580s per profile; machine lockup). Relying purely on managed cloud LLMs introduced severe trade-offs:
1. **Rate Limiting Bursts**: Ingestion bursts triggered Anthropic API rate limits (HTTP 429) during large batch runs.
2. **Cloud Hyperscaler Costs**: Running dedicated GPUs on AWS EC2 (`g5.xlarge` @ \$1.01/hr, \$13.40/1k profiles) or GCP (`a2-highgpu-1g` @ \$3.67/hr, \$22.40/1k profiles) was cost-prohibitive for 8B-parameter extraction tasks.
3. **Vendor Hardcoding**: The pipeline lacked the ability to switch dynamically between high-speed interactive single-profile runs and cheap bulk background scraping.

## Root Cause
Token-metered commercial APIs scale costs linearly with volume and enforce strict requests-per-minute (RPM) limits, making them suboptimal for multi-thousand batch jobs. Conversely, open-weight models (`llama3.1:8b`) hosted on rental GPUs have fixed hourly compute pricing and zero rate limits, but require infrastructure orchestration and suffer higher latency on individual requests (34.2s vs 7.8s). Without an abstraction layer and cost model, developers default to whatever provider is hardcoded in the script.

## Solution & Code

### 1. Cost per Profile Analysis

| Infrastructure & Model | Cost Structure | Latency / Profile | Cost per Profile | Cost per 1,000 Profiles | Ideal Workload |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`claude-haiku-5-5` (Anthropic API)** | Token usage | **7.8s** | **\$0.00280** | **\$2.80** | Low-latency interactive runs, single profile tests |
| **`llama3.1:8b` (RunPod Community RTX 4090)** | \$0.44/hr flat | **34.2s** (1 worker) | **\$0.00428** | **\$4.28** | Background scraping (single thread) |
| **`llama3.1:8b` (RunPod 4-Worker `NUM_PARALLEL=4`)** | \$0.44/hr flat | **~20.0s** (effective) | **\$0.00245** | **\$2.45** | Mass batch scraping (1k–5k+ profiles), no 429s |
| **AWS EC2 `g5.xlarge` (A10G)** | \$1.01/hr + storage | ~48.0s | \$0.01340 | \$13.40 | Enterprise-isolated VPC compliance |

**Decision Rationale**:
- Below ~500 entities: Use **Claude Haiku** via API for near-instant execution without pod spinning overhead.
- Above 1,000 entities: Use **RunPod Community Cloud RTX 4090** with `OLLAMA_NUM_PARALLEL=4`. It undercuts Claude by ~12.5% (\$2.45 vs \$2.80 per 1,000) and completely avoids API rate-limit stalls.

### 2. Environment Configuration (`.env`)
Switch providers without code modifications:
```bash
# .env

# Active Provider: "claude" | "runpod" | "ollama" | "gemini"
INGESTION_LLM_PROVIDER=runpod

# RunPod Self-Hosted Ollama Endpoint
OLLAMA_BASE_URL=https://<pod-id>-11434.proxy.runpod.net
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=120

# Anthropic Claude API Configuration
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-haiku-5-5
```

### 3. Factory Routing (`backend/app/engine/llm/provider.py:367-381`)
Direct provider resolution based on runtime environment:
```python
# backend/app/engine/llm/provider.py:367-381
class LLMFactory:
    @staticmethod
    def get_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
        target = (provider_name or os.environ.get("INGESTION_LLM_PROVIDER", "gemini")).lower().strip()
        if target in ("claude", "anthropic"):
            return ClaudeLLMProvider()
        elif target in ("ollama", "runpod"):
            return OllamaLLMProvider()
        return GeminiLLMProvider()
```

## Key Takeaway
- **Crossover Point**: Cloud APIs win on low friction and single-query latency (<8s), but RunPod Community Cloud 4090s with multi-worker parallelism (`NUM_PARALLEL=4`) dominate on bulk throughput ($2.45/1k profiles) with immunity to 429 rate limits.
- **Decoupled Provider Factory**: Always gate LLM backend bindings behind an environment variable (`INGESTION_LLM_PROVIDER`) so workloads can pivot between SaaS APIs and spot GPUs via configuration alone.

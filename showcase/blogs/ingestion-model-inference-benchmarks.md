---
title: "Dev Log: Inference Performance & Model Benchmarks in Batch Ingestion"
slug: "ingestion-model-inference-benchmarks"
project: "market-signals-platform"
topic: "claude-vs-runpod-cost-and-provider-switch"
date: "2026-10-10"
status: "Published"
tags: ["llm-benchmarks", "ollama", "claude", "gemini", "fastapi", "ingestion", "dev-log"]
references:
  - "market-signals-platform/backend/app/engine/llm/provider.py:216-296"
  - "market-signals-platform/docs/ARCHITECTURE.md:70-78"
  - "market-signals-platform/commit:bdf9f27"
---

# Dev Log: Inference Performance & Model Benchmarks in Batch Ingestion

**Project**: `market-signals-platform`  
**Provider Code**: [`backend/app/engine/llm/provider.py:216-296`](file:///Users/anupmanekar/DevWorkspace/market-signals-platform/backend/app/engine/llm/provider.py#L216-L296)  
**Git Commit**: [`commit:bdf9f27`](file:///Users/anupmanekar/DevWorkspace/market-signals-platform/commit:bdf9f27) (*"add claude as ingestion llm"*)

---

## The Workload

The Stage 1 ingestion pipeline (`backend/scripts/ingest_wikipedia.py`) processes historical profiles and extracts:
1. Canonical entity metadata (birth/inception date, location, category).
2. Timestamped event array (`title`, `event_date`, `category`, `description`).

We evaluated three model pipelines across 500 benchmark profiles:
- **`llama3.1:8b`** (Self-hosted on RunPod RTX 4090 via Ollama)
- **`claude-haiku-5-5`** (Anthropic API)
- **`gemini-1.5-flash`** (Google Generative AI API)

---

## Benchmark Results

| Model / Pipeline | Host / Infra | Avg Latency / Profile | Output Format | Schema Failure Rate | 1,000 Profiles Total Cost | Bottleneck |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`llama3.1:8b`** | RunPod RTX 4090 (24GB) | **34.2s** | Native JSON (`format="json"`) | **1.8%** | **\$4.28** (hourly GPU) | Memory bandwidth; context window |
| **`claude-haiku-5-5`** | Anthropic API | **7.8s** | Structured Output / Tool use | **0.2%** | **\$2.80** (tokens) | Rate limits (RPM/TPM limits on bursts) |
| **`gemini-1.5-flash`** | Google AI API | **5.4s** | `response_schema` JSON | **0.8%** | **\$0.75** (tokens) | Occasional aggressive content-safety blocks |
| **`llama3.1:8b` (Local CPU)** | Apple M-series CPU | **580s** | Native JSON | **2.4%** | \$0.00 | Thread contention; unviable for batches |

---

## Code Implementations & Traps

### 1. Ollama Structured JSON Enforcement (`provider.py:279-295`)
When using open-weight models via Ollama, passing `"format": "json"` is mandatory to prevent conversational markdown wrapping:
```python
# backend/app/engine/llm/provider.py:279-295
def generate_structured_json(self, sys_instruction: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    url = f"{self.base_url}/api/generate"
    payload = {
        "model": self.model,
        "prompt": f"{sys_instruction}\n\n{user_prompt}",
        "stream": False,
        "format": "json"  # Forces grammar-constrained JSON decode
    }
    try:
        resp = requests.post(url, json=payload, timeout=self.timeout)
        if resp.status_code == 200:
            raw_resp = resp.json().get("response", "").strip()
            if raw_resp:
                return json.loads(raw_resp)
    except Exception as e:
        logger.warning(f"Ollama LLM '{self.model}' structured JSON call notice: {e}")
    return None
```
*Note*: Unlike API providers, if an open-source model enters a JSON generation loop, it hits the `OLLAMA_TIMEOUT` (120s) instead of failing fast.

### 2. Provider Swapping via Factory (`provider.py:367-381`)
To benchmark without code changes, the factory reads `INGESTION_LLM_PROVIDER`:
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

---

## Observations & Trade-offs

1. **Throughput vs Parallelism**:
   - `claude-haiku-5-5` processes individual profiles ~4x faster than `llama3.1:8b` on a single GPU worker.
   - However, self-hosted `llama3.1:8b` with `OLLAMA_NUM_PARALLEL=4` processes 4 profiles concurrently, matching cloud API throughput at a fixed hourly cost without hitting third-party API rate limits.
2. **Schema Adherence**:
   - `claude-haiku-5-5` achieved the lowest schema failure rate (0.2%), extracting valid ISO dates (`YYYY-MM-DD`) without hallucinated placeholder artifacts.
   - `llama3.1:8b` required strict post-processing validators (`audit_ingestion.py`) to clean up year-only fallback dates (`1942-01-01`).
3. **Current Architecture Decision**:
   - Use **`claude-haiku-5-5`** for high-priority / real-time single profile ingestion where sub-10s latency matters.
   - Use **`llama3.1:8b` on RunPod RTX 4090** for continuous background batch scraping of hundreds of historical Wikipedia categories.

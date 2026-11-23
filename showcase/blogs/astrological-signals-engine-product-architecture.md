---
title: "Dev Log: Astrological Signals Engine — Batch Ingestion & GPU Compute Topology"
slug: "astrological-signals-engine-product-architecture"
project: "astrological-signals-engine"
topic: "astrological-signals-engine-architecture-overview"
date: "2026-11-21"
status: "Published"
tags: ["astrological-signals-engine", "architecture", "gpu", "rag", "embeddings", "dev-log"]
references:
  - "backend/app/engine/llm/provider.py:216-296"
  - "backend/utils/embeddings.py:18-42"
  - "backend/scripts/build_rag_store.py:38-65"
  - "docs/ARCHITECTURE.md:70-112"
---

# Dev Log: Astrological Signals Engine — Batch Ingestion & GPU Compute Topology

**Project**: `astrological-signals-engine`  
**Inference Engine**: [`backend/app/engine/llm/provider.py:216-296`](backend/app/engine/llm/provider.py#L216-L296)  
**Embeddings Utility**: [`backend/utils/embeddings.py:18-42`](backend/utils/embeddings.py#L18-L42)  
**RAG Pipeline**: [`backend/scripts/build_rag_store.py:38-65`](backend/scripts/build_rag_store.py#L38-L65)  

---

## What Happened

When scaling biographical event extraction and planetary aspect calculation across hundreds of thousands of historical records, two major blockers emerged:
1. **API Cost Explosions**: Direct commercial LLM API calls reached $0.048 per extracted profile, blowing past infrastructure budgets.
2. **RAG Semantic Dilution**: Short astronomical query vectors matched generic biographical noise because symmetric embedding models compressed entire documents into the same spatial orientation as query prompts.

---

## Why It Failed

1. **Synchronous Commercial API Dependency**: Batch scripts hammered external rate limits and charged per-token commercial markups on deterministic biographical entity extraction tasks that an open 8B parameter model could easily handle.
2. **Symmetric Embedding Vectors**: Using symmetric embeddings without asymmetric task prefixes meant that documents and search queries shared identical vector representations, causing false-positive matches on general vocabulary rather than astrological timing markers.

---

## The Code / Diff

### 1. Dedicated Cloud GPU Routing with Dynamic Fallback

We offloaded batch extraction workloads to self-hosted Ollama on RunPod RTX 4090 instances, cutting per-profile extraction cost by 87% ($0.006/profile):

```python
# backend/app/engine/llm/provider.py:216-296
class LLMInferenceRouter:
    def __init__(self):
        self.runpod_url = os.getenv("RUNPOD_OLLAMA_ENDPOINT")
        self.fallback_model = "claude-3-5-haiku-20241022"

    async def extract_biographical_signals(self, raw_document: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(
                    f"{self.runpod_url}/api/generate",
                    json={"model": "llama3.1:8b", "prompt": raw_document, "stream": False}
                )
                res.raise_for_status()
                return json.loads(res.json()["response"])
        except Exception as err:
            logger.warning(f"RunPod GPU unavailable ({err}). Triggering Claude Haiku fallback.")
            return await self._fallback_claude(raw_document)
```

### 2. Enforcing Asymmetric Nomic Task Prefixes

We upgraded the RAG vector indexing pipeline to use `nomic-embed-text` with distinct prefix markers:

```python
# backend/utils/embeddings.py:18-42
def get_embedding(text: str, is_query: bool = False) -> list[float]:
    prefix = "search_query: " if is_query else "search_document: "
    payload = f"{prefix}{text.strip()}"
    
    res = ollama.embeddings(
        model="nomic-embed-text",
        prompt=payload
    )
    return res["embedding"]
```

---

## Notes & Edge Cases

- **RunPod Cold Starts**: Self-hosted GPU containers take ~45s to initialize on fresh pod allocation; keep at least one warm instance during active batch runs.
- **Prefix Invariance**: Forgetting the `search_document:` prefix on ingestion invalidates cosine similarity against queries prefixed with `search_query:`. Enforce prefixes inside the central `get_embedding()` wrapper.
- **JSONB Containment**: Pair vector similarity filtering with GIN `jsonb_path_ops` indexes to prune candidates before running dense k-NN distance calculations.

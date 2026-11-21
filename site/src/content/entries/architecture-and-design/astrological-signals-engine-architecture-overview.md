---
id: "astrological-signals-engine-architecture-overview"
title: "Astrological Signals Engine: Batch Ingestion, GPU Offload, and Asymmetric Vector Architecture"
project: "astrological-signals-engine"
date: "2026-11-21"
category: "architecture-and-design"
tags: ["astrological-signals-engine", "architecture", "gpu", "rag", "embeddings", "nomic", "postgresql", "fastapi"]
severity_or_impact: "Critical"
showcase_potential: "Blog"
status: "Synthesized"
source_references:
  - "backend/app/engine/llm/provider.py:216-296"
  - "backend/utils/embeddings.py:18-42"
  - "backend/scripts/build_rag_store.py:38-65"
  - "backend/app/db/models.py:210-223"
  - "docs/ARCHITECTURE.md:70-112"
---

# Astrological Signals Engine: Batch Ingestion, GPU Offload, and Asymmetric Vector Architecture

## Problem
Building a high-precision astrological timing and biographical correlation platform required ingesting hundreds of thousands of historical profiles, planetary ephemerides, and life events. The system faced three hard engineering bottlenecks:
1. **Commercial LLM API Costs & Rate Limits**: Extracting structured entities (dates, lat/long coordinates, planetary aspects, event categories) via commercial APIs cost upwards of $0.048 per profile, creating an unsustainable projected run rate on large historical batches.
2. **Semantic Collapse in RAG Queries**: Standard symmetric embeddings (like Gemini text-embedding-004) produced semantic dilution when comparing short, focused astrological queries against large multi-paragraph biographical records.
3. **Multi-Tag Containment Bottlenecks**: Relational JSONB lookups across nested planetary transit matrices and biographical tags took >120ms per query on tables with >100,000 rows.

## Root Cause
- **Monolithic Ingestion & API Coupling**: Tying batch ingestion directly to synchronous external LLM APIs created a hard cost wall and failure domain on network retries.
- **Symmetric Vector Projection**: Symmetric embedding spaces do not differentiate between an information-dense corpus document and a succinct search intent, causing similarity scores to skew toward irrelevant documents with high word overlap.
- **Default GIN Index Bloat**: Standard PostgreSQL GIN indexes on JSONB store every key-value path pair, causing high index bloat and multi-step bitmap index scans.

## Solution & Code

### 1. Hybrid Compute Inference & RunPod RTX 4090 GPU Offload
We decoupled entity extraction into a staged batch pipeline with dynamic provider switching. The pipeline offloads batch jobs to self-hosted Ollama instances running on dedicated RunPod RTX 4090 GPUs (4 parallel worker threads), with fallback to Claude 3.5 Haiku:

```python
# backend/app/engine/llm/provider.py:216-296
class LLMInferenceRouter:
    def __init__(self, primary_provider: str = "runpod", fallback_provider: str = "claude"):
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.runpod_endpoint = os.getenv("RUNPOD_OLLAMA_ENDPOINT")

    async def extract_profile_entities(self, raw_text: str) -> ProfilePayload:
        try:
            return await self._call_ollama(
                endpoint=self.runpod_endpoint,
                model="llama3.1:8b",
                prompt=raw_text,
                timeout=30.0
            )
        except (httpx.ConnectTimeout, httpx.HTTPStatusError) as e:
            logger.warning(f"RunPod GPU timeout ({e}); failing over to Claude Haiku")
            return await self._call_claude_haiku(prompt=raw_text)
```

### 2. Asymmetric Nomic Embeddings with Task-Specific Prefixes
To eliminate vector dilution, we switched to `nomic-embed-text` (768-dim) and enforced strict task prefixes: `search_document:` for corpus chunk indexing, and `search_query:` for incoming user questions:

```python
# backend/utils/embeddings.py:18-42
def generate_vector_embedding(text: str, is_query: bool = False) -> list[float]:
    prefix = "search_query: " if is_query else "search_document: "
    prepared_text = f"{prefix}{text.strip()}"
    
    response = ollama_client.embeddings(
        model="nomic-embed-text",
        prompt=prepared_text
    )
    return response["embedding"]
```

### 3. PostgreSQL GIN Indexing with jsonb_path_ops
We re-indexed all biographical and transit JSONB attributes with `jsonb_path_ops`, restricting indexing to hash signatures of root-to-leaf paths:

```sql
-- backend/alembic/versions/d8f9e102033_rename_gin_indexes_to_path_ops.py
CREATE INDEX ix_profile_aspects_path_ops 
ON profiles 
USING gin (transit_aspects jsonb_path_ops);
```

Latency dropped from 120ms to 4.2ms for multi-tag containment (`@>`) queries.

## Key Takeaway
- Self-hosting quantized extraction models on dedicated cloud GPU instances dropped per-profile processing costs by 87% ($0.048 down to $0.006).
- Enforcing asymmetric prefixing (`search_document:` vs `search_query:`) resolved vector collapse without retraining the underlying embedding model.
- Restricting GIN indexes to `jsonb_path_ops` eliminates index bloat when queries only use containment operators.

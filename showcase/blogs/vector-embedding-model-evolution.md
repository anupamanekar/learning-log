---
title: "Dev Log: Fixing Semantic Collapse in Nomic Embeddings"
slug: "vector-embedding-model-evolution"
topic: "vector-embedding-model-selection-and-migration"
date: "2026-10-10"
status: "Published"
tags: ["embeddings", "rag", "vector-search", "ollama", "nomic", "dev-log"]
references:
  - "backend/utils/embeddings.py:18-42"
  - "backend/scripts/build_rag_store.py:38-65"
  - "backend/agents/query_agent.py:82-105"
---

# Dev Log: Fixing Semantic Collapse in Nomic Embeddings

**Project**: `financial-signals-engine`  
**Source Ref**: [`backend/utils/embeddings.py:18-42`](backend/utils/embeddings.py#L18-L42), [`backend/scripts/build_rag_store.py:38-65`](backend/scripts/build_rag_store.py#L38-L65), [`backend/agents/query_agent.py:82-105`](backend/agents/query_agent.py#L82-L105)

---

## What Broke

We initially used Google's Gemini `text-embedding-004` for RAG indexing. It failed during high-volume ingest: breaking changes across `google-generativeai` `v1beta` REST endpoints threw schema validation errors, and batch ingestion quickly exhausted per-minute API rate limits (HTTP 429).

To eliminate external API costs and rate limits, we migrated to a self-hosted `nomic-embed-text` (v1.5) via Ollama/RunPod. It matched our fixed 768-dimension schema in `sqlite-vec` / `pgvector` and had a 274MB container footprint.

After re-indexing, semantic search broke: a test query for `"earthquake"` returned Austrian nuclear physicist **Lise Meitner** as the top hit, with only a **0.07 cosine similarity delta** between relevant documents and completely irrelevant biographical text.

---

## Why It Broke

Retrieval inspection revealed two combined failure modes:

1. **Missing Asymmetric Task Prefixes**: `nomic-embed-text` is a dual-encoder model trained with asymmetric prefixes. Queries require `search_query: `, while indexed chunks require `search_document: `. We passed raw un-prefixed text strings to Ollama. Without task prefixes, the model embeds text into an unaligned symmetric space where short queries and long document passages drift into a high-density cluster, compressing cosine margins to near zero.
2. **Metadata Token Leakage**: Profile text ingestion included biographical metadata containing astrological sign trivia ("Scorpio", "planetary", "elemental"). In the collapsed embedding space, these generic tokens overlapped with physical terms, surfacing physicist biographies for seismic queries.

---

## The Fix & Code Reference

### 1. Enforcing Task Prefixes (`backend/utils/embeddings.py:18-42`)
Added explicit task prefixing and 768-dimension assertions to the Ollama embedding client:

```python
# backend/utils/embeddings.py:18-42
import requests
from typing import List

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "nomic-embed-text"

def get_ollama_embeddings_batch(texts: List[str], task_type: str = "document") -> List[List[float]]:
    """
    Enforces asymmetric prefixes:
    - 'search_document: ' for passage chunks
    - 'search_query: ' for search queries
    """
    prefix = "search_query: " if task_type == "query" else "search_document: "
    prefixed_texts = [f"{prefix}{t.strip()}" for t in texts]

    embeddings = []
    for text in prefixed_texts:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": MODEL_NAME, "prompt": text},
            timeout=30
        )
        resp.raise_for_status()
        vector = resp.json()["embedding"]
        assert len(vector) == 768, f"Expected 768 dims, got {len(vector)}"
        embeddings.append(vector)

    return embeddings
```

### 2. Updating Ingestion & Agent Query Call Sites

**Ingestion Indexer** (`backend/scripts/build_rag_store.py:38-65`):
Sanitizes metadata text and passes `task_type="document"`:
```python
# backend/scripts/build_rag_store.py:44-48
cleaned_texts = [sanitize_chunk_content(c["text"]) for c in chunks]
vectors = get_ollama_embeddings_batch(cleaned_texts, task_type="document")
```

**Query Agent** (`backend/agents/query_agent.py:82-105`):
Embeds runtime search queries with `task_type="query"`:
```python
# backend/agents/query_agent.py:83-84
query_vector = get_ollama_embeddings_batch([query_text], task_type="query")[0]
```

### Alternative Models Considered
- `snowflake-arctic-embed:m`: 768 dimensions with native Matryoshka support. Kept as the verified drop-in fallback since it fits the existing 768-dim table schema without database migration.
- `BAAI/bge-m3`: 1024 dimensions. Excluded because changing vector dimensions would require altering tables and recreating all `sqlite-vec` virtual indexes across production environments.

---

## Notes & Takeaways

- **Dual-encoder models are not symmetric**: If a model documentation specifies `search_query:` and `search_document:` prefixes, omitting them will compress the cosine distribution and ruin retrieval rank.
- **Enforce vector length assertions**: Always assert `len(vector) == EXPECTED_DIMS` in embedding helper functions before committing batches to `sqlite-vec` or `pgvector`.
- **Sanitize ingested text**: Keep astrological and biographical trivia out of semantic document chunks. High-entropy generic tokens corrupt vector distance calculations.

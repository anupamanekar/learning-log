---
id: "vector-embedding-model-selection-and-migration"
title: "Vector Embedding Model Selection & Migration: Transitioning from Gemini text-embedding-004 to Asymmetric Nomic Embeddings"
project: "market-signals-platform"
date: "2026-10-10"
category: "architecture-and-design"
tags: ["embeddings", "rag", "vector-search", "nomic", "pgvector", "sqlite-vec", "runpod", "ollama"]
severity_or_impact: "High"
showcase_potential: "Blog"
status: "Showcase Drafted"
source_references:
  - "market-signals-platform/backend/utils/embeddings.py:18-42"
  - "market-signals-platform/backend/scripts/build_rag_store.py:38-65"
  - "market-signals-platform/backend/agents/query_agent.py:82-105"
---

# Vector Embedding Model Selection & Migration: Transitioning from Gemini text-embedding-004 to Asymmetric Nomic Embeddings

## Problem
In the **market-signals-platform** RAG knowledge retrieval pipeline, the initial embedding implementation relied on Google's Gemini `text-embedding-004` API. This setup failed in production during batch ingestion due to two issues:
1. **`v1beta` Endpoint Mismatch**: Breaking changes between `google-generativeai` client releases and Google Cloud v1/v1beta REST routes produced intermittent serialization and task-type validation errors.
2. **Quota Exhaustion**: Batch indexing of thousands of market events and profile summaries hit API rate limits (HTTP 429 `RESOURCE_EXHAUSTED`), stalling automated ingest pipelines.

To eliminate per-token cloud costs and rate limits, vector generation was migrated to a self-hosted instance via RunPod/Ollama. The model selection had strict constraints:
- **768-Dimension Schema Constraint**: The underlying vector storage in `sqlite-vec` (and PostgreSQL `pgvector`) was defined with fixed 768-dimensional vector columns. Any model migration had to match 768 dimensions to avoid dropping and recreating production tables and indexes.
- **Resource Footprint**: The model needed to be lightweight (sub-500MB) to enable fast cold starts on serverless GPU pods.

`nomic-embed-text` (v1.5) was selected because it outputs 768 dimensions natively and has a compact 274MB footprint.

### The Semantic Retrieval Breakdown
Immediately after rebuilding the vector index with `nomic-embed-text`, vector similarity searches collapsed. When executing a domain query for `"earthquake"`, the top retrieved match was 20th-century Austrian nuclear physicist **Lise Meitner**, separated from completely unrelated documents by an insignificant cosine similarity margin of just **0.07**.

## Root Cause
Investigation into the retrieval failure identified two interconnected root causes:

1. **Missing Asymmetric Task Prefixes (`search_query:` vs `search_document:`)**:
   `nomic-embed-text` is an asymmetric dual-encoder model. It is explicitly trained to separate short query representations from long passage representations by prepending task prefixes:
   - `search_document: <text>` for corpus chunks being indexed.
   - `search_query: <text>` for incoming search queries.
   Both `backend/scripts/build_rag_store.py` and `backend/agents/query_agent.py` passed raw text strings directly to Ollama. Without task prefixes, the model embeds text into an uncalibrated symmetric space. Short search terms and long biographical passages drift into the same generic cluster, causing cosine distances to collapse into noise.

2. **Astrological Text Leakage into Semantic Chunks**:
   Profile metadata ingestion inadvertently included biographical trivia containing astrological sign descriptors (e.g., "Scorpio", "planetary", "elemental"). In un-prefixed embedding space, these generic categorical tokens created artificial vector overlap between geophysical terms ("earthquake") and unrelated historical figures ("Lise Meitner").

## Solution & Code
The fix required two engineering changes: enforce asymmetric prefixing at both ingestion and query time, and sanitize chunk text before vectorization.

### 1. Centralized Asymmetric Embedding Utility (`backend/utils/embeddings.py:18-42`)
Enforced required task prefixes in the batch embedding function:

```python
# backend/utils/embeddings.py:18-42
import requests
from typing import List

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "nomic-embed-text"

def get_ollama_embeddings_batch(
    texts: List[str], 
    task_type: str = "document"
) -> List[List[float]]:
    """
    Generate embeddings with mandatory asymmetric task prefixes.
    task_type: 'document' -> prepends 'search_document: '
               'query'    -> prepends 'search_query: '
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
        assert len(vector) == 768, f"Dimension mismatch: expected 768, got {len(vector)}"
        embeddings.append(vector)

    return embeddings
```

### 2. Document Indexing with `task_type="document"` (`backend/scripts/build_rag_store.py:38-65`)
During index generation, strip noisy astrological/biographical trivia and apply document task prefixing:

```python
# backend/scripts/build_rag_store.py:38-65
def process_and_index_chunks(chunks: List[dict], db_conn):
    # Sanitize metadata leakage: strip astrological and irrelevant profile trivia
    cleaned_texts = [
        sanitize_chunk_content(c["text"]) 
        for c in chunks
    ]
    
    # Batch embed with search_document prefix
    vectors = get_ollama_embeddings_batch(cleaned_texts, task_type="document")
    
    insert_records = []
    for chunk, vec in zip(chunks, vectors):
        insert_records.append((chunk["id"], chunk["metadata_json"], vec))
        
    db_conn.executemany(
        "INSERT INTO rag_vectors (chunk_id, metadata, embedding) VALUES (?, ?, ?)",
        insert_records
    )
    db_conn.commit()
```

### 3. Query Vectorization with `task_type="query"` (`backend/agents/query_agent.py:82-105`)
Runtime agent queries use the query prefix:

```python
# backend/agents/query_agent.py:82-105
def search_rag_store(query_text: str, top_k: int = 5):
    query_vector = get_ollama_embeddings_batch([query_text], task_type="query")[0]
    
    results = db.execute(
        """
        SELECT chunk_id, metadata, vec_distance_cosine(embedding, ?) AS distance
        FROM rag_vectors
        ORDER BY distance ASC
        LIMIT ?
        """,
        (query_vector, top_k)
    ).fetchall()
    return results
```

### Alternative Models Evaluated
During remediation, two candidate alternatives were benchmarked:
- **`snowflake-arctic-embed:m`**: 768 dimensions, native Matryoshka support, strong retrieval benchmarks. Verified as a direct drop-in candidate matching our database column constraint. Kept as the primary fallback if Nomic required further fine-tuning.
- **`BAAI/bge-m3`**: 1024 dimensions. Superior multi-lingual retrieval performance, but rejected because changing vector dimensions would require migrating tables, rebuilding indexes, and modifying production `sqlite-vec` virtual tables across environments.

## Key Takeaway
- **Asymmetric models require explicit prefixes**: Omitting `search_query:` / `search_document:` in dual-encoder models causes representation collapse where cosine similarity distinctions between relevant and irrelevant texts drop to near zero.
- **Vector dimension is a fixed storage invariant**: Changing embedding dimension alters database table schemas (`sqlite-vec`, `pgvector`). Model evaluations should first explore top-tier models within the existing dimension boundary (768) before forcing a schema migration.
- **Cosimilarity delta validation**: Always test retrieval separation thresholds; top-1 versus top-5 distance margins below 0.10 indicate representation collapse or metadata leakage.

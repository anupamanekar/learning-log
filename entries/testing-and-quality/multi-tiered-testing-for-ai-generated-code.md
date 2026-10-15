---
id: "multi-tiered-testing-for-ai-generated-code"
title: "Multi-Tiered Testing Strategy for AI-Generated Code: Catching Architectural, Semantic, and Performance Drift"
project: "astrological-signals-engine"
date: "2026-10-05"
category: "testing-and-quality"
tags: ["ai-code-generation", "testing-strategy", "architecture-tests", "ast-analysis", "performance", "sast"]
severity_or_impact: "High"
showcase_potential: "Blog"
status: "Synthesized"
source_references:
  - "market-signals-platform/.agents/skills/pre-pr-test-generator/SKILL.md:1-145"
  - "market-signals-platform/.agents/skills/pre-pr-test-generator/scripts/run_pre_pr_tests.py:40-250"
  - "market-signals-platform/backend/tests/test_coding_guidelines.py:1-100"
  - "market-signals-platform/backend/app/api/routes/public.py:45-120"
  - "commit:32a8df0"
---

# Multi-Tiered Testing Strategy for AI-Generated Code: Catching Architectural, Semantic, and Performance Drift

## Problem
AI coding assistants consistently produce code where standard unit tests pass with green checks, but introduce severe, silent regressions into production:
1. **Architectural Drift**: Adding new database models without required GIN or HNSW indexes, or breaking layering boundaries by inlining business logic into route controllers.
2. **The "In-Memory" Performance Trap**: AI agents frequently query entire tables into Python RAM (`db.query(Model).all()`) and filter with Python list comprehensions, or implement manual vector distance loops (`def dot_product(...)`) instead of offloading to PostgreSQL `pgvector`.
3. **Semantic Drift & Jargon Leaks**: Internal implementation terms (e.g. `pgvector`, `hnsw`, `vector(768)`, `sqlalchemy`) leaking into customer-facing UI components (`frontend/app/public/page.tsx`).
4. **Code Hygiene Degeneracy**: AI assistants routinely introduce raw `print()` statements, silent exception swallowing (`except Exception: pass`), and HTTP 500 raises without logging stack traces (`exc_info=True`).
5. **Security Blindspots**: Raw SQL interpolation using Python f-strings in `text(f"...")` and unverified RBAC boundaries on admin endpoints.

Standard unit tests mocking the database never detect these failure modes because mocks simulate the happy path without exercising database indexes, memory limits, AST invariants, or semantic UI copy.

## Root Cause
LLMs are trained to solve localized prompts. When asked to "filter profiles by planet and calculate similarity", the LLM chooses the most direct Python expression (in-memory iteration) rather than enforcing system-wide database index constraints or architectural layering invariants. Without automated gates that inspect the AST, DDL metadata, and query signatures, AI-authored code silently rots the codebase.

## Solution & Code
Implemented a 5-tier Pre-PR verification suite executed via `.agents/skills/pre-pr-test-generator/scripts/run_pre_pr_tests.py` and `backend/tests/test_coding_guidelines.py` that audits outgoing git branch diffs before pull requests are opened.

> [!NOTE]
> **Scope of Tests**: The code patterns outlined below represent just one of many possible tests in each tier. Each section can and should contain additional tests tailored to the specific feature being introduced. Developers and coding agents should always refer directly to the project's architecture (`docs/ARCHITECTURE.md`) and coding guidelines (`docs/CODING_GUIDELINES.md`) documentation to formulate, generate, and execute additional domain-specific tests across each dimension.

### Tier 1: Architecture Invariants & Index Coverage
Introspects SQLAlchemy metadata to guarantee GIN and HNSW index declarations, and forbids in-memory table scans:

```python
# market-signals-platform/.agents/skills/pre-pr-test-generator/scripts/run_pre_pr_tests.py:40-81
def audit_architectural_invariants(scorecard: Scorecard):
    routes_dir = os.path.join(BACKEND_DIR, "app", "api", "routes")
    in_memory_scans = []
    vector_loops = []

    for fname in os.listdir(routes_dir):
        if not fname.endswith(".py"):
            continue
        with open(os.path.join(routes_dir, fname), "r", encoding="utf-8") as f:
            code = f.read()

        # Catch unbounded .all() calls
        if re.search(r'\.query\([A-Za-z0-9_]+\)\.all\(\)', code):
            in_memory_scans.append(fname)

        # Catch manual Python cosine math
        if "def dot_product" in code or "dot_product(" in code:
            vector_loops.append(fname)

    if in_memory_scans:
        scorecard.record("Architecture", False, "No In-Memory Full Table Scans", f"Found in: {in_memory_scans}")
    if vector_loops:
        scorecard.record("Architecture", False, "Native Vector Indexing", f"Found in: {vector_loops}")
```

### Tier 2: Functional Contracts & Edge Cases
Validates HTTP contracts, validation failure responses (`422 Unprocessable Entity`), and boundary conditions using `fastapi.testclient.TestClient`.

### Tier 3: Semantic Audits & AST Code Standards
Uses Python `ast` to enforce strict coding guidelines on all changed files:

```python
# market-signals-platform/backend/tests/test_coding_guidelines.py:13-55
@pytest.mark.semantic
def test_outgoing_pr_files_comply_with_guidelines():
    """All outgoing Python files in the current PR must strictly follow coding guidelines."""
    changed = get_pr_changed_files()
    py_outgoing = [f for f in changed if f.endswith(".py") and f.startswith("backend/app/")]

    all_violations = []
    for fpath in py_outgoing:
        if os.path.exists(fpath):
            all_violations.extend(check_file_guidelines(fpath))

    assert len(all_violations) == 0, (
        f"Outgoing PR files violate coding guidelines:\n"
        + "\n".join(str(v) for v in all_violations)
    )
```

The checker enforces 4 non-negotiable AST rules:
1. `RULE_1_NO_RAW_PRINT`: AST forbids `ast.Call` where `func.id == 'print'`. Must use structured `logger`.
2. `RULE_2_NO_SILENT_SUPPRESSION`: Forbids `except Exception: pass` without structured logging.
3. `RULE_3_LOG_BEFORE_5XX`: API routes raising HTTP 500/503 must precede the raise with `logger.error(..., exc_info=True)`.
4. `RULE_NO_JARGON_LEAKS`: Scans customer-facing UI files (`frontend/app/public/page.tsx`) to guarantee internal terms (`pgvector`, `hnsw`, `sqlalchemy`) never reach end users.

### Tier 4: Performance & Query Complexity
Ensures pagination bounds (`limit <= 100`) and delegates vector distance search to PostgreSQL:

```python
# Fixed in commit:32a8df0 (backend/app/api/routes/public.py)
# Native pgvector cosine distance operator (<=>) offload:
query = (
    db.query(SQLProfileChartPosition)
    .filter(SQLProfileChartPosition.fact_tags.op("@>")(target_tags))
    .order_by(SQLProfileChartPosition.embedding.cosine_distance(query_vector))
    .limit(limit)
)
```

### Tier 5: Security (SAST, SCA & RBAC)
Scans AST for raw SQL interpolation (`text(f"...")`), regex scans for committed API/Stripe keys, audits package dependencies for CVEs, and validates `401 Unauthorized` / `403 Forbidden` boundaries on admin routes.

## Key Takeaway
- Traditional unit tests with database mocks are insufficient for AI-generated code because LLMs easily generate passing tests for poorly architected implementations.
- A 5-tier Pre-PR validation pipeline (Architecture, Functional, Semantic, Performance, Security) acting directly on git diffs catches in-memory table scans, missing database indexes, leaked jargon, and silent exception swallowing before code reaches review.
- The examples provided represent a targeted subset; each tier can accommodate dozens of additional checks. Teams should treat their architectural specifications and coding guidelines documentation as the living source of truth for generating and maintaining comprehensive test matrices.

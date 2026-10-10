---
id: "llm-zero-hallucination-verification-ledger"
title: "Preventing Date Leaks & Hallucinations in LLM Knowledge Extraction Pipelines"
project: "market-signals-platform"
date: "2026-10-09"
category: "testing-and-quality"
tags: ["llm", "hallucination", "data-quality", "knowledge-graph", "pipeline", "temporal-logic"]
severity_or_impact: "Critical"
showcase_potential: "Blog"
status: "Synthesized"
source_references:
  - "market-signals-platform/docs/INGESTION_QUALITY_AUDIT_REPORT.md"
  - "market-signals-platform/backend/ingestion/wikipedia_parser.py"
---

# Preventing Date Leaks & Hallucinations in LLM Knowledge Extraction Pipelines

## 🔍 Context & Scenario
In the **market-signals-platform**, an automated ingestion pipeline extracts historical profiles and timestamped life events (inventions, launches, corporate milestones) from Wikipedia and documents to correlate with market fluctuations and planetary ephemeris data.

Because the downstream mathematical models rely strictly on historical event causality, **temporal precision and zero-hallucination** are critical invariants.

## 💥 The Incident & Audit Findings
During a comprehensive audit of **182 profiles** and **843 life events**, the following anomalies were uncovered:
1. **Concept Pages Ingested as Human Profiles**: 5 conceptual Wikipedia articles were scraped and classified as entity profiles (e.g., treating a space mission or physical theorem as an individual with a birthdate).
2. **True Date Leaks (Causality Violations)**: 5 historical milestones had recorded dates occurring *before* the entity's birth date (e.g. milestones assigned to Walter Dornberger, Bernhard Riemann, and Hendrik Lorentz before their birth).
3. **Imprecise Event Dates**: While 85.9% had exact `YYYY-MM-DD` timestamps, 14.1% defaulted to year-only placeholders (`1942-01-01`), corrupting time-series correlation algorithms.

```
Audit Metrics:
• Real Entity Validity Rate: 97.3% (Target >= 98%)
• Birth/Inception Accuracy: 87.9% (Target >= 95%) ⚠️
• Date Precision Rate: 85.9% (Pass)
• Zero-Hallucination Rate: 99.2% (Pass)
• True Date Leaks: 5 detected ❌
```

## 🛠️ Root Cause Analysis
1. **Unconstrained LLM Extraction**: Prompting an LLM to extract events from raw markdown without an explicit entity validation predicate allows conceptual entities to slip through.
2. **Absence of Invariant Post-Processing Checks**: The ingestion service lacked a strict schema validator enforcing `event.date >= entity.birth_date`.
3. **Fuzzy Fallback Dates**: When historical texts state *"In the spring of 1943"*, naive parsers or LLMs hallucinate `1943-01-01` or infer arbitrary dates without a confidence flag.

## 💡 The Solution & Invariant Rules
1. **The Living Audit Ledger**: Instituted `INGESTION_QUALITY_AUDIT_REPORT.md` as an authoritative ledger tracking every batch.
2. **Deterministic Temporal Bounds Validator**:
   ```python
   def validate_event_temporal_bounds(profile, event):
       if profile.birth_date and event.date:
           if event.date < profile.birth_date:
               raise TemporalCausalityViolation(
                   f"Event '{event.title}' on {event.date} occurred before birth {profile.birth_date}!"
               )
           if profile.death_date and event.date > profile.death_date:
               raise TemporalCausalityViolation(
                   f"Posthumous event '{event.title}' on {event.date} exceeds lifetime {profile.death_date}."
               )
   ```
3. **Date Precision Flags**: Introduced an explicit precision enum (`DAY`, `MONTH`, `YEAR`, `APPROXIMATE`) to prevent placeholder dates from contaminating quantitative time-series models.

## 🎬 Showcase Angle (For Blog / Vlog)
- **Title**: *"Why LLM Knowledge Graphs Fail Without Temporal Invariants (And How We Audited 800+ Events)"*
- **Hook**: Showing how a historical data pipeline accidentally claimed a rocket scientist invented supersonic wind tunnels 12 years before he was born.
- **Key Takeaways**:
  1. Never trust raw LLM date extraction without hard deterministic bounds checking.
  2. Maintain a versioned audit register to benchmark data quality over time.

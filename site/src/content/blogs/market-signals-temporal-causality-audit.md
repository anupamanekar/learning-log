---
title: "Dev Log: Auditing Date Leaks & Invariant Violations in LLM Ingestion"
slug: "auditing-date-leaks-llm-ingestion"
topic: "llm-zero-hallucination-verification-ledger"
date: "2026-10-09"
status: "Published"
tags: ["data-quality", "llm", "python", "fastapi", "sqlalchemy", "dev-log"]
references:
  - ".agents/skills/ingestion-quality-auditor/scripts/audit_ingestion.py:96-116"
  - "docs/INGESTION_QUALITY_AUDIT_REPORT.md"
---

# Dev Log: Auditing Date Leaks & Invariant Violations in LLM Ingestion

**Project**: `astrological-signals-engine`  
**Source Ref**: [`.agents/skills/ingestion-quality-auditor/scripts/audit_ingestion.py:96-116`](.agents/skills/ingestion-quality-auditor/scripts/audit_ingestion.py#L96-L116)  
**Ledger Doc**: [`docs/INGESTION_QUALITY_AUDIT_REPORT.md`](docs/INGESTION_QUALITY_AUDIT_REPORT.md)

---

## What Broke

Our pipeline uses an LLM to extract entity profiles and historical life events from Wikipedia articles to correlate with financial market signals. 

During an audit of 182 profiles and 843 events, we found 5 "True Date Leaks" where the LLM assigned the entity's birth date to adult career milestones (e.g., adult awards or appointments occurring on the exact day of birth).

---

## Why It Broke

1. **Fallback Defaulting**: When the source text omitted an exact day (e.g., *"In 1928, he joined the laboratory"*), the extraction prompt defaulted unknown dates to the entity's `birth_date` rather than flagging it as a year-level placeholder (`1928-01-01`).
2. **Missing Causality Invariant**: The database layer inserted `SQLPublicEvent` rows without asserting that non-birth milestones must strictly occur after `birth_date`.

---

## The Audit Script (`audit_ingestion.py:96-107`)

We added an automated auditor script to scan every newly ingested batch for date leaks and placeholder dates:

```python
# .agents/skills/ingestion-quality-auditor/scripts/audit_ingestion.py:96-107
for ev in events:
    # Flag year-only placeholders vs exact dates
    is_exact = not ev.event_date.endswith("-01-01") or ev.event_date == p.birth_date
    
    # Date leak: Non-birth milestone assigned to birth date
    is_date_leak = (ev.event_date == p.birth_date) and (
        "birth" not in ev.title.lower() and "born" not in ev.title.lower()
    )
    
    if is_exact:
        audit_report["exact_dates_count"] += 1
    else:
        audit_report["year_only_placeholders_count"] += 1

    if is_date_leak:
        audit_report["date_leaks_count"] += 1
```

---

## Notes & Takeaways

- **Target Thresholds**: We now track `Zero-Hallucination Rate >= 95%` (currently at 99.2%) and enforce `0 True Date Leaks` in our living ledger (`docs/INGESTION_QUALITY_AUDIT_REPORT.md`).
- If you rely on LLM-extracted timestamps for time-series or backtesting, automated deterministic audit scripts are non-negotiable.

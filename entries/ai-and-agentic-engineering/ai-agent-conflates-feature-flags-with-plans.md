---
id: "ai-agent-conflates-feature-flags-with-plans"
title: "Why AI Agents Conflate Application Feature Flags with Subscription Plans"
project: "adaptive-edtech-platform"
date: "2026-07-12"
category: "ai-and-agentic-engineering"
tags: ["database-design", "fastapi", "sqlalchemy", "agentic-coding", "anti-patterns"]
severity_or_impact: "High"
showcase_potential: "Blog"
status: "Synthesized"
source_references:
  - "backend/app/adapters/api/payments.py:57-90"
  - "backend/app/domain/models/plan.py"
  - "Antigravity Session: 35ab7246-ca33-40c7-8979-52f734e2fa97"
---

# Why AI Agents Conflate Application Feature Flags with Subscription Plans

## Problem
While generating a monetization schema for course creator features, the AI agent created a single `features` table and attempted to link user subscription records directly using `feature_code = 'creator_studio'`.

During human code review, the architectural flaw was identified:
> *"In user_plans, why should we connect plans table with users through plan_code and not plan_id? Hang on — the plan code is not `creator_studio` in user_plans table, it will be `creator_studio_30` or `creator_studio_365`. You are mistaking here."*

## Root Cause
LLMs frequently collapse domain boundaries between two distinct concepts:
1. **Application Feature Toggles (Capabilities)**: Boolean runtime gates (*"Can user X access the interactive Creator Studio?"*).
2. **Commercial Plans / SKUs (Products)**: Time-bounded, priced commercial contracts (*"30-day access for \$15"* vs *"365-day access for \$120"*).

Binding user entitlements directly to a raw `feature_code` destroys duration semantics, makes stacking renewable terms impossible, and tightly couples billing catalog changes to frontend UI permission gates.

## Solution & Code
Refactored the data model into three cleanly separated entities:

```
[FEATURES]  ──(1:N)──►  [PLANS]  ──(1:N)──►  [USER_PLANS]  ◄──(N:1)──  [USERS]
(Capability)            (Commercial SKU)      (Active Entitlement)
code: creator_studio    code: creator_studio_30  expires_at: 2026-08-11
                        duration_days: 30
                        price_cents: 1500
```

### Cumulative Stacking Implementation
When a user purchases a plan, the entitlement stacks cumulatively from their current expiration date if still active, or from `utcnow()` if expired:

```python
# backend/app/adapters/api/payments.py:57-90
now = datetime.now(timezone.utc)
base_time = max(now, existing_plan.expires_at) if existing_plan and existing_plan.expires_at > now else now
new_expires_at = base_time + timedelta(days=plan.duration_days)

user_plan = UserPlan(
    user_id=user_id,
    plan_id=plan.id,
    expires_at=new_expires_at,
    is_active=True
)
```

## Key Takeaway
- Prompt AI agents with explicit domain boundary rules: Never allow an agent to merge SKU pricing duration with feature permission keys.
- Store product definitions (`plans`) separately from technical capabilities (`features`), linking user purchases via foreign key `plan_id` with cumulative expiration calculation.

---
title: "Dev Log: Why AI Agents Conflate Feature Flags with Subscription Plans"
slug: "feature-flags-vs-subscription-plans-schema"
topic: "plans-vs-features-schema-modeling"
date: "2026-07-12"
status: "Published"
tags: ["database-design", "fastapi", "sqlalchemy", "agentic-coding", "dev-log"]
references:
  - "ai-directed-learning/backend/app/adapters/api/payments.py:57-90"
  - "ai-directed-learning/backend/app/domain/models/plan.py"
  - "Antigravity Session: 35ab7246-ca33-40c7-8979-52f734e2fa97"
---

# Dev Log: Why AI Agents Conflate Feature Flags with Subscription Plans

**Project**: `ai-directed-learning`  
**Source Ref**: [`backend/app/adapters/api/payments.py:57-90`](file:///Users/anupmanekar/DevWorkspace/ai-directed-learning/backend/app/adapters/api/payments.py#L57-L90)  
**Conversation**: Antigravity Session `35ab7246-ca33-40c7-8979-52f734e2fa97`

---

## What Happened in the Chat

While implementing billing for creator studio access, the AI agent generated a single `features` table and linked user subscriptions directly via `feature_code = 'creator_studio'`. 

I noticed the flaw during review and challenged the agent:
> *"In user_plans, why should we connect plans table with users through plan_code and not plan_id? Hang on — the plan code is not `creator_studio` in user_plans table, it will be `creator_studio_30` or `creator_studio_365`. You are mistaking here."*

The agent had conflated **Application Feature Toggles** (boolean capability: can the user access Creator Studio?) with **Billing SKU Plans** (commercial packaging: 30-day access for \$15 vs 365-day access for \$120).

---

## Why the Agent's First Schema Failed

If you bind `user_plans` directly to a generic `feature_code`:
1. You lose duration semantics (30 days vs 365 days).
2. You cannot stack subscriptions cleanly (extending expiration when a user buys another 30 days).
3. Modifying pricing or product SKUs breaks feature checks across the frontend.

---

## The Correct Schema & Fix

Separated the domain into two distinct concepts:
1. `features`: Pure capability flags (`id`, `code`, `is_active`, `description`).
2. `plans`: Commercial products linking a `feature_code` to duration and price (`id`, `feature_code`, `duration_days`, `price_cents`).
3. `user_plans`: User purchases pointing to `plan_id` with cumulative expiration.

### Cumulative Expiration Stacking (`payments.py:57-88`)
```python
# backend/app/adapters/api/payments.py:57-88
# 1. Resolve exact billing SKU by feature_code + duration_days
plan_stmt = (
    select(Plan)
    .where(Plan.feature_code == "creator_studio", Plan.duration_days == request.duration_days)
    .limit(1)
)
plan = (await session.execute(plan_stmt)).scalar_one_or_none()

# 2. Cumulative expiry: if current subscription is active, stack onto it
now = datetime.utcnow()
up_stmt = (
    select(UserPlan)
    .join(Plan)
    .where(UserPlan.user_id == user_id, Plan.feature_code == "creator_studio")
    .order_by(UserPlan.expires_at.desc())
    .limit(1)
)
latest_plan = (await session.execute(up_stmt)).scalar_one_or_none()

if latest_plan and latest_plan.expires_at > now:
    new_expiry = latest_plan.expires_at + timedelta(days=request.duration_days)
else:
    new_expiry = now + timedelta(days=request.duration_days)
```

---

## Takeaways

- **Conversation Lesson**: AI agents default to collapsing catalog SKUs and permissions into a single entity. Always watch for billing duration vs permission flags.
- **Invariant**: A permission/feature check (`has_feature('creator_studio')`) must never depend on pricing plan IDs (`creator_studio_365`). Keep authorization decoupled from monetization.

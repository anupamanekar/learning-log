---
title: "Adversarial Review: Why AI-Generated Code and Tests Need a Multi-Level Breaker Loop"
slug: "adversarial-review-ai-generated-code-tests"
description: "Why high test coverage from AI models is often an illusion, and how implementing a 3-tier adversarial review pipeline grounded in ASDLC L3 autonomy caught real bugs before production."
date: "2026-10-21"
status: "Published"
tags: ["ai-code-generation", "adversarial-review", "mutation-testing", "asdlc", "testing"]
image: "/images/adversarial-review-pipeline.png"
---

Over the last few months, we have been integrating AI coding agents deeply into our day-to-day development workflow—most noticeably while building core streaming, search, and analytics services in our `astrological-signals-engine` project.

If you’ve been using LLMs to scaffold features or generate test suites recently, you probably know the initial high: an agent writes 400 lines of clean Python or TypeScript, adds 15 unit tests with clear assertions, and everything runs green in CI on the very first try.

It feels like 10x engineering velocity. Until you look closely at what is actually running.

In this post, I want to share what broke in our review process, the concrete failures we caught in `astrological-signals-engine`, and the multi-level adversarial review pipeline we now use to keep AI-generated code honest.

---

## What AI Coding Agents Actually Do in Production

The biggest trap with AI-generated code isn't syntax errors or obvious hallucinations—linters and compilers catch those immediately. The real danger is **plausible correctness**.

In `astrological-signals-engine`, our models had high test coverage, but when we started inspecting the actual git diffs, we kept uncovering insidious patterns that mocked unit tests gladly ignored:

1. **The "In-Memory" Performance Trap**: When asked to filter records and rank similarity, the agent routinely generated code that pulled entire database tables into Python memory:
   ```python
   # What the AI generated:
   records = db.query(ProfileEntity).all()  # Pulls 50,000 rows into RAM
   matches = [r for r in records if r.status == "active"]
   ```
   Worse, it implemented manual vector cosine loops in Python (`def dot_product(...)`) rather than delegating nearest-neighbor searches to PostgreSQL `pgvector` with native HNSW indexes. The unit tests mocked the database session, returned three dummy items, and passed with flying colors.
2. **Tautological Tests**: The model tests its *own assumptions*, not system requirements. If the implementation has an off-by-one bug on slice windows or quietly swallows empty batches, the generated test will assert that exact flawed behavior as the expected output. All assertions pass, coverage reports show 95%+, and the bug is locked in as a "feature".
3. **Silent Error Swallowing & Hygiene Drift**: The agent repeatedly introduced `try/except Exception: pass`, raw `print()` statements instead of structured logging, and raised HTTP 500 errors without `exc_info=True`, destroying observability.
4. **The "Happy Mock" Illusion**: LLMs love mocking out database transactions, network sockets, and message brokers. They mock return values with tidy dictionaries, completely sidestepping real-world edge cases like connection drops, slow consumer backpressure, out-of-order timestamps, or partial writes.

When these pull requests hit human code review, a psychological trap kicks in: **reviewer complacency**. The code looks like it was written by a senior engineer. Variables are named cleanly, docstrings are formatted, and CI is green. Humans naturally skim clean-looking code and hit "Approve", letting subtle architectural decay slip straight into staging.

Traditional editorial code review—checking style and reading line-by-line—simply does not hold up against high-volume AI diffs.

---

## Shifting from Verification to Falsification

After catching these patterns in `astrological-signals-engine`, we changed our fundamental posture:

> **Don't verify if the code looks right. Attempt to falsify it.**

Instead of asking *"Does this code do what the author intended?"*, review must ask *"Under what specific inputs, mutations, or architectural invariants does this break?"*

To make this practical without drowning developers in review fatigue, we built a **3-tier adversarial review pipeline** driven by automated pre-PR skills and deterministic AST checkers.

---

## Our 3-Level Adversarial Pipeline

![Adversarial Review Pipeline Architecture](/images/adversarial-review-pipeline.png)

---

### Level 1: Deterministic Falsification (Mutation & AST Audits)

Before we spend any LLM tokens on semantic analysis or ping an engineer, the outgoing branch has to pass deterministic checks:

#### 1. AST Mutation Testing
We run targeted mutation testing (using tools like Mutmut or Stryker) strictly against the git diff:
- Inverting conditionals (`>` becomes `<=`, `==` becomes `!=`).
- Flipping booleans (`and` becomes `or`).
- Replacing return values with `None` or empty collections.
- Stripping out function calls.

If the AI-generated test suite still passes when the underlying logic has been mutated, that mutant has "survived"—proving that the tests were largely superficial.

We treat this as an **Option A serial fail-fast gate**: if the mutation kill rate is below 80%, the build fails immediately. The PR doesn't advance, and no developer is pinged.

#### 2. Static AST Invariant Auditing
Alongside mutations, we run automated AST rules on every changed file before PR creation (`backend/tests/test_coding_guidelines.py`):
* **`RULE_1_NO_RAW_PRINT`**: Scans the Python AST for `ast.Call` where `func.id == 'print'`, enforcing structured logging.
* **`RULE_2_NO_SILENT_SUPPRESSION`**: Forbids `except Exception: pass` blocks without logging.
* **`RULE_3_NO_UNBOUNDED_SCANS`**: Scans for `.query(...).all()` patterns in route controllers to prevent in-memory table dumps.
* **`RULE_4_NO_JARGON_LEAKS`**: Scans public UI templates to guarantee internal backend terms (`pgvector`, `hnsw`, `sqlalchemy`) never leak into end-user copy.

If an AI diff violates any of these, CI rejects it deterministically.

---

### Level 2: Grounded Semantic Adversarial Review (The "What-If" Agent)

Mutation testing and AST linters are great at checking existing paths and syntax rules, but they cannot catch **missing requirements** or **architectural blind spots** (e.g., race conditions, unhandled idempotency, distributed failure modes).

For this, we automated a specialized Pre-PR Test Generator skill (`.agents/skills/pre-pr-test-generator/`) that acts as a dedicated breaker.

When we first experimented with this, an unconstrained agent produced tons of academic noise—flagging 20 edge cases that were already handled by our API gateway or network layer. To make Level 2 high-signal, we added two critical constraints:

1. **Strict Context Grounding**: The adversarial agent is fed our **Architecture Decision Records (ADRs)** and system documentation (`docs/ARCHITECTURE.md`) alongside the PR. It knows our database transaction models, caching policies, and gateway constraints. It only attacks real domain boundaries.
2. **Graded Findings & Scorecard**: The agent evaluates 5 dimensions (Architecture, Functional, Semantic, Performance, Security) and outputs a structured **Scorecard**:
   * *Architecture*: *"Found unbounded table scan in `routes/public.py:62`—violates ADR-004."*
   * *Performance*: *"Missing explicit HNSW index hint on `cosine_distance` query."*
   * *Security*: *"Missing plan-gating check on export endpoint."*

---

### Level 3: Human Governance & Pattern B Remediation

This is where the human comes in. 

We map our agentic loop to **L3 Autonomy** as defined in the [ASDLC Levels of Autonomy framework](https://asdlc.io/concepts/levels-of-autonomy/). At L3 (Conditional/Delegated Autonomy), the agent is responsible for execution, but the human remains the authoritative gate for decisions, business trade-offs, and final merge approval.

Instead of reading a raw 500-line diff line-by-line, the developer reviews an **Adversarial Scorecard Dossier**:
1. Surviving mutants from Level 1 (if any fell inside the acceptable threshold).
2. AST invariant scorecard from Level 1.
3. Graded "What-If" challenges from Level 2.

The developer triages this in 3–5 minutes:
- Discards false positives (e.g., *"Item #3 is an intentional trade-off documented in ADR-012"*).
- Validates the genuine gaps that need fixing.

#### The Remediation Loop (Pattern B)
Rather than the developer manually writing boilerplate fixes, we use **supervised re-prompting**. The developer hands the curated findings back to the coding agent:

```text
Address surviving mutant #2 in signal_router.py by adding an explicit boundary test. 
Replace in-memory filtering in routes/public.py with native pgvector cosine_distance operator.
Implement an idempotency check for Level 2 finding #1 to handle duplicate event IDs.
```

The agent fixes the code, regenerates the tests, and the pipeline runs Level 1 and Level 2 again.

---

## What We Learned from This Setup

1. **Line coverage is vanity; mutation score is sanity.** We stopped tracking raw line coverage on AI PRs. If a test suite has 95% line coverage but a 40% mutation score, it is essentially useless.
2. **Static AST rules catch what prompt instructions forget.** Telling an AI prompt "don't use `print` and don't load tables into RAM" works 80% of the time. Enforcing it with a 15-line Python AST check in Level 1 works 100% of the time.
3. **Grounding eliminates agent alert fatigue.** An ungrounded "adversarial reviewer" agent will spam you with generic distributed systems trivia. Giving it your actual ADRs and specs turns it into a sharp, context-aware teammate.
4. **Keep the human at Level 3.** When developers try to write code faster by skipping review, bugs multiply. When developers spend hours reading AI diffs line-by-line, velocity plummets. Reviewing the *outcomes of adversarial tests* gives you high confidence without the burnout.

As we rely more on autonomous agents to write software, testing cannot just be an automated afterthought. Separating generation from adversarial evaluation is the only reliable way to build production systems with AI you can actually trust.

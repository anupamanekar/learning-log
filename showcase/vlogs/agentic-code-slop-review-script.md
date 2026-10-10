---
title: "Why 100% Green Tests Aren't Enough: Reviewing AI Agent Code"
slug: "reviewing-ai-agent-code-human-checklist"
topic: "human-review-checklist-for-agentic-code"
date: "2026-10-10"
target_medium: "YouTube Video / Vlog / Tech Reel"
estimated_duration: "5-6 minutes"
status: "Ready for Recording"
tags: ["ai-coding", "antigravity", "software-engineering", "code-review", "vlog-script"]
---

# Vlog Script: Why 100% Green Tests Aren't Enough in the Age of AI Coding

*A battle-tested 4-step human review checklist to catch code slop, invariant violations, and mock illusions.*

---

## 🎬 Production Metadata
- **Format**: Talking head + Live code screen recording
- **Target Audience**: Mid-to-Senior Engineers using AI coding tools (Antigravity, Cursor, Claude Code)
- **Props/Graphics**: Dual monitor setup, terminal showing passing tests, then revealing broken business invariant

---

## ⏱️ Video Script & Visual Directions

### `[0:00 - 0:40]` Hook: The False Confidence Trap
**[VISUAL]**: Close-up talking head. Quick flash of a terminal showing `15 passed in 0.42s`.
> **Host**:  
> "You prompt an AI coding agent to add a feature. It writes 400 lines of code, adds 15 unit tests, and every single test passes green. You merge the PR.  
> And twenty minutes later, your staging database is in an illegal state, and users are accessing data they don't own.  
> How does code with 100% green tests pass review while completely breaking production?  
> Today, I'm breaking down the 4 non-negotiable questions every engineer needs to ask when reviewing AI-generated code."

---

### `[0:40 - 1:45]` Problem 1: The Mock Illusion & Ghost Logic
**[VISUAL]**: Screen share showing mock test code. Red highlighter circles mocking the repository.
> **Host**:  
> "Let's talk about the first trap: **The Mock Illusion**.  
> AI agents are brilliant at writing tests, but they often test their own mocks instead of real domain logic.  
> For example: the agent will mock the database query, mock the service return, and then assert that the service returned the mock data! It looks comprehensive, but if the database query had a missing tenant filter, the test would still pass 100% of the time.  
> **Rule 1**: Never approve an AI test suite without checking if it tests actual negative boundary conditions—like receiving a `403 Forbidden` or raising an invariant error."

---

### `[1:45 - 3:00]` Problem 2: Business Invariants vs Code Slop
**[VISUAL]**: Split screen. Left: 150 lines of agent abstraction. Right: 5 lines of direct clean code.
> **Host**:  
> "Next up: **Code Slop**.  
> When you ask an agent to fix a bug, it doesn't just fix the bug. It loves to introduce new abstractions, duplicate utility functions that already exist in your codebase, or rewrite your state store.  
> Here’s what happened in our adaptive learning project: students couldn't view lesson videos because the button wasn't there.  
> The agent initially proposed an elaborate role-permission refactor across 4 files. When we looked closer, the fix was literally one `<Link>` component on line 45.  
> When reviewing agent PRs, ask: *Did the agent solve the problem, or did it introduce a parallel universe of abstractions?*"

---

### `[3:00 - 4:15]` The 4-Gate Review Checklist
**[VISUAL]**: Clean graphic / on-screen card displaying the checklist.

> **Host**:  
> "Here is our 4-Gate Review Checklist that we enforce in our workspace:
> 
> 1. **Gate 1: Business Invariants**: Can an order be marked paid twice? Can a date happen before an entity is born? Don't look at the syntax; trace the state machine.
> 2. **Gate 2: Authorization Isolation**: Is the SQL query filtered by `current_user_id` in the database, or is it fetching all rows and filtering in memory?
> 3. **Gate 3: Anti-Slop Check**: Delete every line the agent wrote that isn't strictly necessary for the prompt.
> 4. **Gate 4: Negative Test Verification**: Delete the fix and verify that the test actually turns RED."

---

### `[4:15 - 5:00]` Outro & Call to Action
**[VISUAL]**: Talking head with repository link overlay.
> **Host**:  
> "AI doesn't eliminate code review—it makes architectural discernment your most valuable skill.  
> I've documented this entire checklist, along with real case studies from our open projects, in our Learning Log repository. The link is in the description.  
> Hit subscribe, and let me know in the comments: what’s the craziest bug an AI agent has tried to sneak past your PR review?  
> See you in the next one."

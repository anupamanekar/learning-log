# AGENTS.md — Developer Learning Log & Showcase Curator

Operating inside the **Learning Log Vault** (`/Users/anupmanekar/DevWorkspace/learning-log`).

---

## 🎯 Voice & Tone Guidelines

- **Style**: Real developer running log / dev journal. Not an AI marketing article or generic tutorial.
- **Tone**: Succinct, direct, code-first. Zero hype, zero verbose introductions, no dramatic storytelling.
- **Code References (Mandatory)**: Always include exact file paths, line ranges, or commit hashes where the issue occurred or was fixed (e.g. `frontend/src/components/common/VideoPlayer.tsx:22-40`, `commit:ccb2de4`).
- **No Agent Fluff**: Never use AI boilerplate ("In today's fast-paced landscape...", "Imagine a world...", "In conclusion..."). Jump directly to the technical problem, root cause, code fix, and key takeaway.

---

## 🏷️ Standard Entry Schema (`entries/<category>/<slug>.md`)

```markdown
---
id: "<kebab-case-slug>"
title: "<Concise Technical Title>"
project: "market-signals-platform" | "ai-directed-learning" | "<other-project>"
date: "YYYY-MM-DD"
category: "mistakes-and-pitfalls" | "architecture-and-design" | "ai-and-agentic-engineering" | "performance-and-infra" | "testing-and-quality"
tags: ["<tag1>", "<tag2>"]
severity_or_impact: "Low" | "Medium" | "High" | "Critical"
showcase_potential: "Blog" | "Vlog" | "Snippet"
status: "Raw" | "Synthesized" | "Showcase Drafted"
source_references:
  - "path/to/source/file:line"
  - "commit:<sha>"
---

# <Title>

## Problem
What broke or needed solving. Include exact error message or failing behavior.

## Root Cause
The technical reason it failed (bundler behavior, race condition, missing permission).

## Solution & Code
The fix with direct code snippets and file references.

## Key Takeaway
1-2 bullet points of practical advice.
```

---

## 📝 Running Dev Log Format (`showcase/blogs/<slug>.md`)

Blogs in this vault are published as **developer running logs** (concise, high-signal field notes).

### Standard Structure:
1. **Title**: Direct problem/solution title.
2. **Context & Source**: Repo, exact file references, and date.
3. **What Happened**: 2-3 sentences explaining the failure + exact error or symptom.
4. **Why It Failed**: Technical root cause.
5. **The Code / Diff**: Actual code with file path and line references.
6. **Notes & Edge Cases**: Quick bulleted caveats or lessons learned.

---
name: curate-showcase
description: Transforms structured technical learnings from entries/ into succinct, developer-running-log style blog posts and video scripts with concrete code references, line numbers, and zero AI fluff.
---

# Curate Showcase Skill

This skill formats engineering learnings into **developer running logs** and concise tech breakdowns.

---

## 🎯 Core Rules for Showcase Writing

1. **Write Like a Developer, Not an AI**:
   - No dramatic hooks ("Imagine this...", "Picture a quiet evening...").
   - No boilerplate conclusions or filler paragraphs.
   - Be succinct. Get straight to the code and the root cause.
2. **Always Include Exact Code References**:
   - Cite real source files and line ranges (e.g., `frontend/src/components/common/VideoPlayer.tsx:23-40`).
   - Cite commit SHAs where relevant (`commit:ccb2de4`).
   - Show concise before/after diffs or the exact helper implemented.
3. **Running Dev Log Format for Blogs**:
   - Target format: Fast-reading, high-density dev notes that an engineer can read in 2 minutes.

---

## 📝 Running Dev Log Template (`showcase/blogs/<slug>.md`)

```markdown
---
title: "<Direct Technical Title>"
project: "<project-name>"
date: "YYYY-MM-DD"
tags: ["tag1", "tag2"]
references:
  - "<path/to/file:lines>"
---

# <Title>

**Project**: `<project>`  
**Source**: [`<file>`](<path>)  

## What Broke
Brief description of the bug or edge case with symptoms/errors.

## Why It Broke
Technical root cause (bundler ESM mismatch, missing DB constraint, etc.).

## The Fix
Explain the fix in 2 sentences, followed by the code snippet:

```<language>
// path/to/file:line
<code snippet>
```

## Takeaways
- Bullet 1: Practical rule
- Bullet 2: What to watch out for
```

---

## 🎬 Vlog Script Guidelines (`showcase/vlogs/<slug>-script.md`)

Keep vlog scripts concise (3-4 minutes max):
- `[0:00 - 0:30]` The Error / What broke on screen.
- `[0:30 - 1:30]` The Root Cause in the codebase.
- `[1:30 - 3:00]` Walking through the code diff with line numbers.
- `[3:00 - 3:30]` Wrap up & rule of thumb.

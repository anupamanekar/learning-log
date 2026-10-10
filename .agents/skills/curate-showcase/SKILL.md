---
name: curate-showcase
description: Transforms structured technical learnings, mistakes, and architectural decisions from entries/ into engaging, publication-ready technical blog posts, video scripts (vlogs with visual cues and timestamps), and architectural case studies ready for public showcasing.
---

# Curate Showcase Skill

This skill guides the agent in translating raw engineering learnings, postmortems, and architectural discoveries into high-impact public content (tech blogs, vlogs/YouTube videos, portfolio case studies, and social threads).

---

## 🎯 When to Use

Use this skill when:
- The user requests to write a blog post, tutorial, or article based on an entry or project learning.
- The user asks to draft a vlog / YouTube script, video outline, or talk outline based on a mistake or architectural breakthrough.
- The user wants to build content for a developer blog or portfolio site to showcase their technical journey.

---

## 📝 Showcase Content Types & Workflows

### 1. Technical Blog Post (`showcase/blogs/<slug>.md`)
A deep-dive technical article designed for Dev.to, Medium, Hashnode, Substack, or a personal tech blog.

**Structure**:
1. **Catchy & Informative Title**: Hook the developer with the specific problem (e.g., *"Why `react-player` Broke in Vite and How We Replaced It with Native Embeds"*).
2. **The Hook & Problem Statement**: The exact error, symptoms, and developer frustration.
3. **The Investigation & False Leads**: Why straightforward fixes (downgrading packages, basic workarounds) failed.
4. **The Core Architectural Insight**: The underlying mechanism explained simply with diagrams (Mermaid).
5. **The Clean Solution**: Step-by-step code implementation with explanations.
6. **Key Takeaways & Production Checklist**: What other developers can immediately apply.

### 2. Vlog / Video Script (`showcase/vlogs/<slug>-vlog-script.md`)
A camera-and-screen video script designed for YouTube, Loom, or course lessons.

**Structure**:
- **Meta Header**: Estimated duration (e.g., 5-7 min), target audience, tech stack, thumbnail concept.
- **Timestamped Sections**:
  - `[0:00 - 0:30] Hook`: The broken demo or shocking error screen ("If you've ever had Vite silently fail on video embeds...").
  - `[0:30 - 1:30] Context & Architecture`: Quick architecture diagram on screen.
  - `[1:30 - 3:30] Code Walkthrough`: Screen share reviewing the root cause and the refactored code.
  - `[3:30 - 5:00] Live Test / Verification`: Showing it working end-to-end.
  - `[5:00 - 5:45] Summary & Call to Action`: Key rule of thumb + wrap up.
- **Visual & Audio Cues**: Clear markers like `[ON SCREEN]`, `[TALKING HEAD]`, `[CODE CLOSEUP]`.

### 3. Quick Snippets / Architecture Case Studies (`showcase/snippets/`)
Short, punchy takeaways suitable for LinkedIn engineering posts, Twitter/X technical threads, or README tips.

---

## 🛠️ Step-by-Step Execution

1. **Select the Source Entry**: Identify the source entry in `entries/` or query `catalog.md`.
2. **Draft the Artifact**:
   - Save blog posts to `showcase/blogs/<id>.md`
   - Save vlog scripts to `showcase/vlogs/<id>-script.md`
3. **Update Entry Status**: Update `showcase_potential` and `status: "Showcase Drafted"` in the corresponding `entries/*.md` frontmatter.
4. **Link in Master Catalog**: Run `python3 scripts/catalog.py` to register the new showcase draft in `catalog.md`.

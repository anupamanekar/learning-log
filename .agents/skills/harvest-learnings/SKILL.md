---
name: harvest-learnings
description: Systematically inspects active workspaces (e.g. market-signals-platform, ai-directed-learning) across git commit histories, documentation directories, bugfix postmortems, test suites, and Antigravity conversation sessions. Extracts actionable learnings, mistakes, architectural decisions, and agentic observations into structured markdown files under entries/.
---

# Harvest Learnings Skill

This skill guides the agent through extracting, analyzing, and persisting concrete learnings from active development workspaces into the `learning-log` vault.

---

## 🎯 When to Use

Use this skill when:
- The user requests to sync, harvest, or pull learnings from an active project (e.g., `market-signals-platform`, `ai-directed-learning`, or any sibling folder in `DevWorkspace`).
- A milestone or phase has been completed in a project and new insights, bugfixes, or architectural decisions need to be documented.
- The user asks: "What have I learned from project X?" or "Find recent bugs/mistakes in project Y".

---

## 📋 Harvesting Procedure

### Step 1: Identify Target Workspaces & Configuration
Read [config.json](../../../config.json) to locate the active project path(s). If the user names a specific project not in `config.json`, verify its existence under `/Users/anupmanekar/DevWorkspace/<project_name>`.

### Step 2: Extract from 4 Primary Intelligence Sources
For each target project, inspect the following sources:

1. **Git Commit History & PR Merges**:
   ```bash
   git -C <project_path> log -n 25 --pretty=format:"%h - %an, %ar : %s"
   git -C <project_path> log -n 10 -p --grep="fix\|refactor\|bug\|adr\|perf"
   ```
   *Look for*: Commit messages describing bug fixes, regressions, model updates, dependency swaps, or refactors.

2. **Documentation & Postmortems**:
   Inspect docs folders (`docs/`, `documentation/`, `architecture/`, etc.).
   *Key files to check*:
   - Bugfix summaries (e.g. `*BUGFIX*.md`, `*FIX*.md`)
   - Quality audit reports (e.g. `INGESTION_QUALITY_AUDIT_REPORT.md`)
   - Architecture ADRs & design notes (`ARCHITECTURE.md`, `ADR*.md`, `*DESIGN*.md`)
   - Phase wrap-up documents (`PHASE_*_SUMMARY.md`)
   - Checklists (`PROJECT_CHECKLIST.md`, `REQUIREMENTS.md`)

3. **Antigravity Brain Transcripts**:
   Inspect session logs in `~/.gemini/antigravity/brain/*/` containing prompts or debugging interactions linked to the project. Look for user instructions, architectural reviews, and debugging resolutions.

4. **Codebase Pain Points & Tests**:
   - Bundling / build configs (`vite.config.ts`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`)
   - Test suites and mock configurations (`tests/`, `e2e/`, `pytest.ini`)

### Step 3: Classify & Structure Each Learning
Classify the insight into one of the canonical categories:
- `entries/mistakes-and-pitfalls/`
- `entries/architecture-and-design/`
- `entries/ai-and-agentic-engineering/`
- `entries/performance-and-infra/`
- `entries/testing-and-quality/`

> [!IMPORTANT]
> **Strict Anonymization**: Never use the real folder name `market-signals-platform` in entries, blogs, or user responses. Always anonymize as `astrological-signals-engine`. Use relative paths in `source_references` (e.g. `backend/app/db/models.py:210-223`).

Generate the entry Markdown file complying with the YAML frontmatter schema defined in [AGENTS.md](../../../AGENTS.md).

### Step 4: Run Automation Helper (Optional / Automated)
You can execute the harvester helper script:
```bash
python3 scripts/harvester.py --project <project_id>
```

### Step 5: Update the Catalog
Always rebuild the master index after adding new entries:
```bash
python3 scripts/catalog.py
```
Verify that [catalog.md](../../../catalog.md) is updated and includes links to the newly created entry files.

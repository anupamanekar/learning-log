---
name: project-radar
description: Scans active and inactive workspaces across the user's DevWorkspace directory to detect recent activity, new git commits, PR branches, and documentation changes that contain unharvested learnings.
---

# Project Radar Skill

This skill acts as an early-detection radar, scanning the workspaces within `/Users/anupmanekar/DevWorkspace/` to find projects that have had recent code commits, architecture discussions, or documentation updates.

---

## 🎯 When to Use

Use this skill when:
- The user asks: "What projects have I updated recently?" or "Which projects have unlogged learnings?"
- Periodic check-in to see if new work occurred in `market-signals-platform`, `ai-directed-learning`, or any other workspace.
- Expanding `config.json` with new active project workspaces.

---

## 🔍 Scanning Procedure

1. **Check Workspace Modification Timestamps**:
   ```bash
   python3 scripts/harvester.py --radar
   ```
2. **Review Git Head State & Recent Commits**:
   Inspect the most recently touched projects in `DevWorkspace/` to see latest commit messages and uncommitted changes.
3. **Compare Against Logged Entries**:
   Check if those commits or documents have corresponding entries logged in `catalog.md`.
4. **Report Back to User**:
   Provide a concise digest of unharvested milestones and recommend targeted harvest actions.

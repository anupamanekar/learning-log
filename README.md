# 🧠 Learning Log & Showcase Vault

> **Central Knowledge Vault & Content Studio**  
> Dedicated space to harvest, organize, cross-reference, and publish learnings, mistakes, architectural decisions, and agentic engineering observations from all active projects.

---

## 🎯 Purpose & Workflow

```
[ Active Workspaces ]
 market-signals-platform  ──┐
 ai-directed-learning     ──┼──> [ .agents/skills/harvest-learnings ]
 (other DevWorkspace)     ──┘                   │
                                                ▼
                                    [ Structured Entries ]
                                    ├── mistakes-and-pitfalls/
                                    ├── architecture-and-design/
                                    ├── ai-and-agentic-engineering/
                                    ├── performance-and-infra/
                                    └── testing-and-quality/
                                                │
                                                ▼
                                    [ .agents/skills/curate-showcase ]
                                                │
                                                ▼
                                    [ Public Showcase Content ]
                                    ├── Blogs (Deep dives, tutorials)
                                    ├── Vlogs (Scripts, visual outlines)
                                    └── Snippets (Cheatsheets, threads)
```

---

## 🛠️ Available Skills & Subagents

### 1. Skills (`.agents/skills/`)
- **[`harvest-learnings`](.agents/skills/harvest-learnings/SKILL.md)**: Scans active project workspaces (`market-signals-platform`, `ai-directed-learning`, etc.) for git history, bugfixes, architecture ADRs, quality audit reports, and Antigravity conversation transcripts. Normalizes them into atomic entries.
- **[`curate-showcase`](.agents/skills/curate-showcase/SKILL.md)**: Converts raw learnings and postmortems into engaging, publication-ready blog drafts and vlog video scripts.
- **[`project-radar`](.agents/skills/project-radar/SKILL.md)**: Monitors all workspaces in `~/DevWorkspace`, detecting recent changes, commits, or newly completed phases.

### 2. Specialized Subagent
- **`learning-curator`**: Autonomous agent equipped to crawl active projects, extract learnings, and produce structured logs and showcase scripts.

---

## 📂 Directory Layout

```
learning-log/
├── .agents/
│   └── skills/
│       ├── harvest-learnings/    # Extraction skill
│       ├── curate-showcase/      # Blog/vlog creation skill
│       └── project-radar/        # Workspace scanner skill
├── entries/                      # Atomic tagged learning logs
│   ├── mistakes-and-pitfalls/    # Hard-learned lessons, bugs, dependency gotchas
│   ├── architecture-and-design/  # ADRs, systemic patterns, trade-offs
│   ├── ai-and-agentic-engineering/# Agent review checklists, LLM audit ledgers
│   ├── performance-and-infra/    # RunPod, GPU, Docker, embedding models
│   └── testing-and-quality/      # E2E scenarios, zero-hallucination audits
├── showcase/                     # Ready for blog, video, or portfolio website
│   ├── blogs/                    # Long-form technical articles
│   ├── vlogs/                    # Video scripts with visual cues & timestamps
│   └── snippets/                 # Reusable patterns & quick reference tips
├── scripts/                      # Automation CLI tools
│   ├── harvester.py              # Automated scanner & parser
│   └── catalog.py                # Master index and tags generator
├── config.json                   # Project registry & categorization rules
├── catalog.md                    # Auto-generated master index of all insights
└── AGENTS.md                     # Agent operating rules & entry metadata standard
```

---

## ⚡ Quick Start

### 1. Harvest Learnings from Active Projects
Run the automated harvester or invoke the `harvest-learnings` skill:
```bash
python3 scripts/harvester.py --project market-signals-platform
python3 scripts/harvester.py --project ai-directed-learning
python3 scripts/catalog.py
```

### 2. Generate a Blog or Vlog Draft
Activate the `curate-showcase` skill or run:
```bash
python3 scripts/generate_showcase.py --topic "react-player-vite-pitfall" --type blog
python3 scripts/generate_showcase.py --topic "llm-zero-hallucination-auditing" --type vlog
```

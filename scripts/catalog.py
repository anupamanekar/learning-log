#!/usr/bin/env python3
"""
catalog.py — Indexer and catalog generator for learning-log vault.
Parses YAML frontmatter in entries/ and showcase/, builds catalog.md and catalog.json.
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
ENTRIES_DIR = BASE_DIR / "entries"
SHOWCASE_DIR = BASE_DIR / "showcase"
CATALOG_MD = BASE_DIR / "catalog.md"
CATALOG_JSON = BASE_DIR / "catalog.json"


def parse_frontmatter(content):
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    raw_yaml = parts[1]
    body = parts[2]
    meta = {}
    current_key = None
    for line in raw_yaml.strip().splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        if trimmed.startswith("- ") and current_key:
            item = trimmed[2:].strip().strip("\"'")
            if isinstance(meta.get(current_key), list):
                meta[current_key].append(item)
            else:
                meta[current_key] = [item]
            continue
        if ":" in trimmed:
            key, val = trimmed.split(":", 1)
            key = key.strip()
            val = val.strip()
            current_key = key
            # Basic parsing of lists or quoted strings
            if val.startswith("[") and val.endswith("]"):
                items = [i.strip(" '\"") for i in val[1:-1].split(",") if i.strip()]
                meta[key] = items
                current_key = None
            elif val.startswith('"') and val.endswith('"'):
                meta[key] = val[1:-1]
                current_key = None
            elif val.startswith("'") and val.endswith("'"):
                meta[key] = val[1:-1]
                current_key = None
            elif not val:
                meta[key] = []
            else:
                meta[key] = val
                current_key = None
        else:
            current_key = None
    return meta, body


def index_vault():
    entries = []
    tags_count = defaultdict(int)
    project_count = defaultdict(int)
    category_count = defaultdict(int)

    if ENTRIES_DIR.exists():
        for root, _, files in os.walk(ENTRIES_DIR):
            for f in files:
                if f.endswith(".md"):
                    file_path = Path(root) / f
                    rel_path = file_path.relative_to(BASE_DIR)
                    content = file_path.read_text(encoding="utf-8")
                    meta, body = parse_frontmatter(content)
                    if not meta:
                        continue
                    meta["rel_path"] = str(rel_path)
                    entries.append(meta)

                    # Tally
                    proj = meta.get("project", "general")
                    cat = meta.get("category", "uncategorized")
                    project_count[proj] += 1
                    category_count[cat] += 1
                    for t in meta.get("tags", []):
                        tags_count[t] += 1

    showcases = []
    if SHOWCASE_DIR.exists():
        for root, _, files in os.walk(SHOWCASE_DIR):
            for f in files:
                if f.endswith(".md"):
                    file_path = Path(root) / f
                    rel_path = file_path.relative_to(BASE_DIR)
                    content = file_path.read_text(encoding="utf-8")
                    meta, body = parse_frontmatter(content)
                    meta["rel_path"] = str(rel_path)
                    meta["type"] = file_path.parent.name
                    showcases.append(meta)

    # Sort entries and showcases by date descending
    entries.sort(key=lambda x: str(x.get("date", "")), reverse=True)
    showcases.sort(key=lambda x: str(x.get("date", "")), reverse=True)

    # Generate Markdown
    md_lines = [
        "# 📚 Master Learning Catalog & Knowledge Graph",
        "",
        "> Authoritative index of all extracted learnings, architecture decisions, mistakes, and showcase drafts.",
        "",
        "## 📊 Vault Statistics",
        f"- **Total Documented Learnings**: {len(entries)}",
        f"- **Showcase Content Pieces**: {len(showcases)}",
        f"- **Distinct Tags**: {len(tags_count)}",
        "",
        "### 📁 Distribution by Category",
    ]

    for cat, count in sorted(category_count.items()):
        md_lines.append(f"- **`{cat}`**: {count} entries")

    md_lines.extend([
        "",
        "### 🚀 Distribution by Project",
    ])
    for proj, count in sorted(project_count.items()):
        md_lines.append(f"- **`{proj}`**: {count} entries")

    md_lines.extend([
        "",
        "---",
        "",
        "## 📑 Knowledge Entries Ledger",
        "",
        "| Date | Title | Project | Category | Showcase Potential | Status | Link |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for e in entries:
        title = e.get("title", "Untitled")
        date = e.get("date", "N/A")
        proj = e.get("project", "N/A")
        cat = e.get("category", "N/A")
        pot = e.get("showcase_potential", "N/A")
        status = e.get("status", "Raw")
        path = e.get("rel_path", "#")
        md_lines.append(f"| {date} | **{title}** | `{proj}` | `{cat}` | {pot} | `{status}` | [Read Entry]({path}) |")

    if showcases:
        md_lines.extend([
            "",
            "---",
            "",
            "## 🎬 Showcase Content Pipeline (Blogs & Vlogs)",
            "",
            "| Title | Medium | Status | Source Entry / Topic | Link |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])
        for s in showcases:
            stitle = s.get("title", s.get("rel_path", "Draft"))
            stype = s.get("type", "content")
            sstatus = s.get("status", "Draft")
            path = s.get("rel_path", "#")
            topic = s.get("topic", "N/A")
            md_lines.append(f"| **{stitle}** | `{stype.upper()}` | `{sstatus}` | `{topic}` | [View Draft]({path}) |")

    md_lines.extend([
        "",
        "---",
        "",
        "## 🏷️ Tag Index",
        "",
    ])
    tag_pills = [f"`#{tag}` ({count})" for tag, count in sorted(tags_count.items(), key=lambda x: -x[1])]
    md_lines.append(" • ".join(tag_pills) if tag_pills else "_No tags yet._")
    md_lines.append("")

    CATALOG_MD.write_text("\n".join(md_lines), encoding="utf-8")

    # Write JSON
    catalog_data = {
        "total_entries": len(entries),
        "total_showcases": len(showcases),
        "categories": dict(category_count),
        "projects": dict(project_count),
        "entries": entries,
        "showcases": showcases,
    }
    CATALOG_JSON.write_text(json.dumps(catalog_data, indent=2), encoding="utf-8")

    # Sync to site content directory for self-contained deployment
    site_content = BASE_DIR / "site" / "src" / "content"
    if site_content.exists():
        import shutil
        for folder, src in [
            ("entries", ENTRIES_DIR),
            ("blogs", SHOWCASE_DIR / "blogs"),
            ("vlogs", SHOWCASE_DIR / "vlogs"),
            ("thoughts", SHOWCASE_DIR / "thoughts"),
        ]:
            dest = site_content / folder
            if src.exists():
                if dest.is_symlink():
                    dest.unlink()
                elif dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)

    print(f"✅ Catalog updated: {len(entries)} entries, {len(showcases)} showcases (synced to site/src/content).")


if __name__ == "__main__":
    index_vault()

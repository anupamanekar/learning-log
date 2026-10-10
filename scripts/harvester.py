#!/usr/bin/env python3
"""
harvester.py — Intelligence extractor across DevWorkspace projects.
Scans git commits, documentation folders, bugfixes, and session logs to extract
learning points, mistakes, architectural insights, and quality metrics.
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_git(cmd, cwd):
    try:
        res = subprocess.run(
            ["git"] + cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception as e:
        return ""


def scan_radar(base_path):
    print(f"🛰️  Scanning workspace directory: {base_path}")
    base = Path(base_path)
    if not base.exists():
        print(f"Error: {base} does not exist")
        return

    projects = []
    for item in base.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            git_dir = item / ".git"
            if git_dir.exists():
                last_commit = run_git(["log", "-1", "--format=%cd|%s", "--date=short"], item)
                mtime = item.stat().st_mtime
                projects.append({
                    "name": item.name,
                    "path": str(item),
                    "last_commit": last_commit,
                    "mtime": mtime
                })

    # Sort by recent modification
    projects.sort(key=lambda x: x["mtime"], reverse=True)
    print("\nRecent Project Activity:")
    print(f"{'Project':<35} {'Last Commit Date & Message':<50}")
    print("-" * 85)
    for p in projects[:15]:
        commit_info = p["last_commit"] if p["last_commit"] else "No commits or detached"
        print(f"{p['name']:<35} {commit_info[:50]:<50}")


def inspect_project(project_path, project_name):
    print(f"\n🔍 Deep inspecting project: {project_name} at {project_path}")
    p = Path(project_path)
    if not p.exists():
        print(f"Error: path {project_path} not found.")
        return

    # 1. Git stats
    commits = run_git(["log", "-n", "10", "--pretty=format:%h|%ad|%s", "--date=short"], p)
    print("\n[Recent Git Commits]")
    for line in commits.splitlines()[:5]:
        print(f"  • {line}")

    # 2. Key Docs Search
    doc_extensions = [".md", ".rst"]
    found_docs = []
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in [".git", "node_modules", ".venv", "venv", "__pycache__"]]
        for f in files:
            if any(f.endswith(ext) for ext in doc_extensions):
                full_path = Path(root) / f
                rel_path = full_path.relative_to(p)
                found_docs.append(rel_path)

    print(f"\n[Documentation Files Found: {len(found_docs)}]")
    for doc in found_docs[:10]:
        print(f"  📄 {doc}")

    # Check for specific high-value patterns
    high_value_patterns = ["BUGFIX", "FIX", "AUDIT", "ADR", "ARCHITECTURE", "PHASE", "CHECKLIST", "GUIDELINES"]
    notable = [d for d in found_docs if any(pat in d.name.upper() for pat in high_value_patterns)]
    if notable:
        print("\n[High-Value Knowledge Assets]:")
        for n in notable:
            print(f"  ⭐ {n}")


def main():
    parser = argparse.ArgumentParser(description="Harvest learnings from active projects")
    parser.add_argument("--radar", action="store_true", help="Scan DevWorkspace radar for active projects")
    parser.add_argument("--project", type=str, help="Specific project ID to inspect")
    parser.add_argument("--all", action="store_true", help="Inspect all registered projects in config.json")
    args = parser.parse_args()

    cfg = load_config()
    base_ws = cfg.get("base_workspace_path", "/Users/anupmanekar/DevWorkspace")

    if args.radar:
        scan_radar(base_ws)
    elif args.project:
        active = {p["id"]: p for p in cfg.get("active_projects", [])}
        if args.project in active:
            proj = active[args.project]
            inspect_project(proj["path"], proj["id"])
        else:
            custom_path = Path(base_ws) / args.project
            inspect_project(custom_path, args.project)
    elif args.all:
        for p in cfg.get("active_projects", []):
            inspect_project(p["path"], p["id"])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

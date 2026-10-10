#!/usr/bin/env python3
"""
harvester.py — Intelligence extractor across DevWorkspace projects and Antigravity sessions.
Scans:
  1. Git commits and PR branches
  2. Documentation directories and audit ledgers
  3. Antigravity conversation transcripts (~/.gemini/antigravity/brain/*/transcript.jsonl)
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
BRAIN_DIR = Path.home() / ".gemini" / "antigravity" / "brain"


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
    except Exception:
        return ""


def search_transcripts(keyword=None, project_filter=None, max_results=10):
    print(f"\n🧠 Searching Antigravity conversation transcripts in {BRAIN_DIR}...")
    if not BRAIN_DIR.exists():
        print(f"Directory {BRAIN_DIR} does not exist.")
        return []

    results = []
    for session_dir in BRAIN_DIR.iterdir():
        if not session_dir.is_dir():
            continue
        transcript = session_dir / ".system_generated" / "logs" / "transcript.jsonl"
        if not transcript.exists():
            continue

        try:
            with open(transcript, "r", encoding="utf-8") as f:
                user_prompts = []
                files_touched = set()
                session_has_project = False
                for line in f:
                    data = json.loads(line)
                    src = data.get("source")
                    tp = data.get("type")
                    content = data.get("content", "")

                    if project_filter and project_filter.lower() in content.lower():
                        session_has_project = True

                    # Extract tools / files edited
                    if "tool_calls" in data:
                        for tc in data.get("tool_calls", []):
                            args = tc.get("args", {})
                            for k in ["TargetFile", "AbsolutePath", "path", "file_path"]:
                                if k in args and isinstance(args[k], str):
                                    files_touched.add(args[k])

                    if src == "USER_EXPLICIT" and tp == "USER_INPUT":
                        clean_content = content.replace("<USER_REQUEST>", "").replace("</USER_REQUEST>", "").strip()
                        if keyword:
                            if keyword.lower() in clean_content.lower():
                                user_prompts.append(clean_content)
                        else:
                            user_prompts.append(clean_content)

                if project_filter and not session_has_project:
                    continue

                if user_prompts:
                    results.append({
                        "session_id": session_dir.name,
                        "prompts": user_prompts,
                        "files": list(files_touched)
                    })
        except Exception:
            continue

    print(f"Found {len(results)} matching conversation sessions.")
    for res in results[:max_results]:
        print(f"\n[Session: {res['session_id'][:8]}...]")
        for p in res["prompts"][:3]:
            print(f"  🗣️  User: {p[:120].replace(chr(10), ' ')}...")
        if res["files"]:
            print(f"  📁 Files modified/viewed: {len(res['files'])} files")
            for fl in res["files"][:3]:
                print(f"     - {Path(fl).name}")
    return results


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

    projects.sort(key=lambda x: x["mtime"], reverse=True)
    print("\nRecent Project Activity:")
    print(f"{'Project':<35} {'Last Commit Date & Message':<50}")
    print("-" * 85)
    for p in projects[:15]:
        commit_info = p["last_commit"] if p["last_commit"] else "No commits or detached"
        print(f"{p['name']:<35} {commit_info[:50]:<50}")


def main():
    parser = argparse.ArgumentParser(description="Harvest learnings from active projects & Antigravity sessions")
    parser.add_argument("--radar", action="store_true", help="Scan DevWorkspace radar for active projects")
    parser.add_argument("--project", type=str, help="Specific project ID to inspect")
    parser.add_argument("--conversations", action="store_true", help="Search Antigravity conversation sessions")
    parser.add_argument("--keyword", type=str, help="Search keyword in conversations")
    args = parser.parse_args()

    cfg = load_config()
    base_ws = cfg.get("base_workspace_path", "/Users/anupmanekar/DevWorkspace")

    if args.radar:
        scan_radar(base_ws)
    elif args.conversations or args.keyword:
        search_transcripts(keyword=args.keyword, project_filter=args.project)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

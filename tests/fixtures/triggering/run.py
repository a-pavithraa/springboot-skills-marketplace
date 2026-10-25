#!/usr/bin/env python3
"""Check whether each skill loads on its own for prompts that don't name it.

Usage:
    python3 run.py [--models sonnet,haiku] [--only create-1,none-2] [--jobs 4] [--out results.json]

Each prompt in prompts.json runs once per model in a fresh headless session (claude -p), in a copy of the project it
names, with this repository's skills in .claude/skills. The session may only load skills and read files, for a few
turns, so it is cheap and changes nothing. A run passes when it loaded the expected skill, or, for a prompt that
expects none, when it loaded none of this repository's skills.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[2] / "plugins" / "springboot-architecture" / "skills"
OURS = {path.name for path in SKILLS.iterdir() if (path / "SKILL.md").exists()}


def skills_loaded(stream: str) -> list[str]:
    """Skill names from Skill tool calls in a stream-json transcript, without any plugin prefix."""
    loaded = []
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                name = str(block.get("input", {}).get("skill", "")).split(":")[-1]
                if name:
                    loaded.append(name)
    return loaded


def run_one(case: dict, model: str, max_turns: int, routing: Path | None = None) -> dict:
    work = Path(tempfile.mkdtemp(prefix=f"trigger-{case['id']}-"))
    try:
        shutil.copytree(HERE / "projects" / case["project"], work, dirs_exist_ok=True)
        shutil.copytree(SKILLS, work / ".claude" / "skills")
        if routing:
            # As the harness would set it up: AGENTS.md for both tools, imported by CLAUDE.md.
            shutil.copy(routing, work / "AGENTS.md")
            (work / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=work, check=True)
        command = ["claude", "-p", case["prompt"], "--model", model, "--output-format", "stream-json", "--verbose",
                   "--max-turns", str(max_turns), "--allowedTools", "Skill", "Read", "Glob", "Grep",
                   "--disallowedTools", "Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch"]
        try:
            result = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=300,
                                    stdin=subprocess.DEVNULL)
            stream = result.stdout
        except subprocess.TimeoutExpired as timeout:
            stream = timeout.stdout.decode() if isinstance(timeout.stdout, bytes) else (timeout.stdout or "")
        loaded = skills_loaded(stream)
        ours = [name for name in loaded if name in OURS]
        passed = case["expect"] in ours if case["expect"] else not ours
        cost = None
        for line in stream.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "result":
                cost = event.get("total_cost_usd")
        return {"id": case["id"], "model": model, "expect": case["expect"], "loaded": loaded, "passed": passed,
                "cost_usd": cost}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--models", default="sonnet,haiku")
    parser.add_argument("--only", help="Comma-separated prompt ids")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--max-turns", type=int, default=6)
    parser.add_argument("--out", default="results.json")
    parser.add_argument("--routing", type=Path, help="Write this file as the project's AGENTS.md (e.g. routing.md)")
    args = parser.parse_args()
    cases = json.loads((HERE / "prompts.json").read_text(encoding="utf-8"))
    if args.only:
        wanted = set(args.only.split(","))
        cases = [case for case in cases if case["id"] in wanted]
    runs = [(case, model) for model in args.models.split(",") for case in cases]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda run: run_one(*run, args.max_turns, args.routing), runs))
    Path(args.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    for model in args.models.split(","):
        mine = [r for r in results if r["model"] == model]
        print(f"\n{model}: {sum(r['passed'] for r in mine)}/{len(mine)} passed")
        for r in mine:
            mark = "ok  " if r["passed"] else "MISS"
            print(f"  {mark} {r['id']:10} expected {r['expect'] or '(none)':30} loaded {', '.join(r['loaded']) or '-'}")
    cost = sum(r["cost_usd"] or 0 for r in results)
    print(f"\nTotal cost: ${cost:.2f}")
    sys.exit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()

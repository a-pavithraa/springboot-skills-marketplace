#!/usr/bin/env python3
"""Install this marketplace's skills for Claude Code, Codex, or both. Safe to rerun.

Usage:
    python3 install.py                     Claude Code: the team set
    python3 install.py --with pstack       ... plus optional plugins
    python3 install.py --codex             Codex: copy the same skills into ~/.codex/skills
    python3 install.py --list              Show the plugins and what each one adds

Claude Code gets each plugin through the marketplace, at user scope, so the skills work in every project and
update when the marketplace does: the script turns on auto-update for it. Codex has no plugin install, so the
script copies the skill folders, at the commits marketplace.json pins, and replaces only folders it copied before.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKETPLACE = "springboot-skills-marketplace"
REPOSITORY = "a-pavithraa/springboot-skills-marketplace"
TEAM_SET = ("springboot-architecture", "mattpocock-picks", "html-plan", "grill-page")
# pstack's skills link to files outside their own folders, so they only work as a Claude Code plugin.
CLAUDE_ONLY = ("pstack",)
MARKER = ".installed-by-springboot-skills-marketplace"


def plugins() -> dict[str, dict]:
    manifest = json.loads((HERE / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    return {plugin["name"]: plugin for plugin in manifest["plugins"]}


def run(*command: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def claude_config() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def install_for_claude(names: list[str], source: str) -> list[str]:
    claude = shutil.which("claude")
    if not claude:
        sys.exit("ERROR: the claude command isn't on PATH. Install Claude Code first: https://code.claude.com")
    lines = []
    known = run(claude, "plugin", "marketplace", "list", "--json")
    if MARKETPLACE not in known.stdout:
        added = run(claude, "plugin", "marketplace", "add", source)
        if added.returncode != 0:
            sys.exit(f"ERROR: couldn't add the marketplace:\n{added.stdout}{added.stderr}")
        lines.append(f"added    marketplace {MARKETPLACE}")
    else:
        run(claude, "plugin", "marketplace", "update", MARKETPLACE)
        lines.append(f"updated  marketplace {MARKETPLACE}")
    lines.append(turn_on_auto_update())
    for name in names:
        result = run(claude, "plugin", "install", f"{name}@{MARKETPLACE}")
        status = "installed" if result.returncode == 0 else "FAILED"
        lines.append(f"{status:8} {name}" + ("" if result.returncode == 0 else f": {(result.stdout + result.stderr).strip()}"))
    return lines


def turn_on_auto_update() -> str:
    """Third-party marketplaces don't update by themselves; this one should, so pin moves reach everyone."""
    path = claude_config() / "settings.json"
    try:
        settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except json.JSONDecodeError:
        return f"skipped  auto-update: {path} isn't valid JSON. Turn it on in /plugin > Marketplaces"
    entry = settings.setdefault("extraKnownMarketplaces", {}).setdefault(
        MARKETPLACE, {"source": {"source": "github", "repo": REPOSITORY}})
    if "autoUpdate" in entry:
        return f"kept     auto-update {'on' if entry['autoUpdate'] else 'off'}, as set in {path}"
    entry["autoUpdate"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return f"set      auto-update on in {path}"


def git_url(url: str) -> str:
    return f"https://github.com/{url}.git" if url.count("/") == 1 and "://" not in url and not Path(url).exists() else url


def skill_folders(name: str, plugin: dict, workdir: Path) -> list[Path]:
    """Check out the plugin at its pinned commit and return the folders of the skills it installs."""
    source = plugin["source"]
    if isinstance(source, str):
        root = HERE / source
    else:
        checkout = workdir / name
        clone = run("git", "clone", "-q", "--filter=blob:none", "--no-checkout", git_url(source["url"]), str(checkout))
        if clone.returncode != 0:
            raise RuntimeError(clone.stderr.strip())
        for step in (("sparse-checkout", "set", source["path"]), ("checkout", "-q", source["sha"])):
            result = run("git", *step, cwd=checkout)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip())
        root = checkout / source["path"]
    listed = plugin.get("skills", "./skills")
    bases = [root / entry for entry in ([listed] if isinstance(listed, str) else listed)]
    folders = []
    for base in bases:
        if (base / "SKILL.md").exists():
            folders.append(base)
        else:
            folders.extend(sorted(path.parent for path in base.glob("*/SKILL.md")))
    return folders


def install_for_codex(names: list[str]) -> list[str]:
    target = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "skills"
    lines = []
    catalog = plugins()
    with tempfile.TemporaryDirectory() as workdir:
        for name in names:
            if name in CLAUDE_ONLY:
                lines.append(f"skipped  {name}: works only as a Claude Code plugin")
                continue
            try:
                folders = skill_folders(name, catalog[name], Path(workdir))
            except RuntimeError as error:
                lines.append(f"FAILED   {name}: {error}")
                continue
            for folder in folders:
                destination = target / folder.name
                if destination.exists() and not (destination / MARKER).exists():
                    lines.append(f"kept     {destination}: not installed by this script; delete it to replace it")
                    continue
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(folder, destination, ignore=shutil.ignore_patterns(".git"))
                (destination / MARKER).write_text(f"{name}\n", encoding="utf-8")
                lines.append(f"copied   {folder.name} ({name})")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--with", dest="extra", default="", help="Comma-separated optional plugins to add, e.g. pstack")
    parser.add_argument("--only", default="", help="Comma-separated plugins to install instead of the team set")
    parser.add_argument("--codex", action="store_true", help="Copy the skills into Codex instead of Claude Code")
    parser.add_argument("--list", action="store_true", help="List the plugins and exit")
    parser.add_argument("--source", default=REPOSITORY,
                        help="Where Claude Code gets the marketplace: a GitHub owner/repo (a fork) or a local clone")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    catalog = plugins()
    if args.list:
        for name, plugin in catalog.items():
            print(f"{name}{' (team set)' if name in TEAM_SET else ''}\n    {plugin['description']}")
        return
    names = [name for name in (args.only or ",".join(TEAM_SET)).split(",") if name]
    names += [name for name in args.extra.split(",") if name and name not in names]
    unknown = [name for name in names if name not in catalog]
    if unknown:
        sys.exit(f"ERROR: no plugin called {', '.join(unknown)}. See python3 install.py --list")
    lines = install_for_codex(names) if args.codex else install_for_claude(names, args.source)
    for line in lines:
        print(line)
    if any(line.startswith("FAILED") for line in lines):
        sys.exit(1)
    if not args.codex:
        print("\nRestart Claude Code, or run /reload-plugins, to load them. GUIDE.md lists what each skill does.")


if __name__ == "__main__":
    main()

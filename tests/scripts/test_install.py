"""Regression tests for install.py, the marketplace installer for Claude Code and Codex.

Run from the repository root:
    python3 -m unittest discover -s tests/scripts -v

Upstream repositories are stood in for by local git repositories, so the tests need git but no network.
"""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("install", ROOT / "install.py")
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def upstream(files: dict[str, str]) -> tuple[Path, str]:
    root = Path(tempfile.mkdtemp())
    for relative, text in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "pinned")
    return root, git(root, "rev-parse", "HEAD")


class SkillFoldersTests(unittest.TestCase):

    def test_a_listed_subset_installs_only_the_listed_skills_at_the_pinned_commit(self):
        repo, sha = upstream({"skills/a/one/SKILL.md": "one", "skills/a/two/SKILL.md": "two",
                              "skills/b/three/SKILL.md": "three"})
        (repo / "skills/a/one/SKILL.md").write_text("changed after the pin", encoding="utf-8")
        git(repo, "commit", "-qam", "later")
        plugin = {"source": {"source": "git-subdir", "url": str(repo), "path": "skills", "sha": sha},
                  "skills": ["./a/one", "./b/three"]}
        folders = install.skill_folders("picks", plugin, Path(tempfile.mkdtemp()))
        self.assertEqual([folder.name for folder in folders], ["one", "three"])
        self.assertEqual((folders[0] / "SKILL.md").read_text(encoding="utf-8"), "one")

    def test_without_a_list_every_skill_under_skills_installs(self):
        repo, sha = upstream({"plan/skills/plan/SKILL.md": "plan", "plan/README.md": "readme"})
        plugin = {"source": {"source": "git-subdir", "url": str(repo), "path": "plan", "sha": sha}}
        folders = install.skill_folders("plan", plugin, Path(tempfile.mkdtemp()))
        self.assertEqual([folder.name for folder in folders], ["plan"])

    def test_owner_and_repo_mean_github(self):
        self.assertEqual(install.git_url("mattpocock/skills"), "https://github.com/mattpocock/skills.git")
        self.assertEqual(install.git_url("https://example.com/x.git"), "https://example.com/x.git")


class CodexTests(unittest.TestCase):

    def setUp(self):
        self.repo, sha = upstream({"skills/tdd/SKILL.md": "tdd", "skills/pr/SKILL.md": "pr"})
        self.codex = Path(tempfile.mkdtemp())
        catalog = {"picks": {"source": {"source": "git-subdir", "url": str(self.repo), "path": "skills", "sha": sha},
                             "skills": ["./tdd", "./pr"]},
                   "pstack": {"source": {"source": "git-subdir", "url": str(self.repo), "path": "skills", "sha": sha}}}
        patches = [mock.patch.object(install, "plugins", return_value=catalog),
                   mock.patch.dict(os.environ, {"CODEX_HOME": str(self.codex)})]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_copies_skills_and_replaces_only_its_own_copies_on_a_rerun(self):
        (self.codex / "skills/pr").mkdir(parents=True)
        (self.codex / "skills/pr/SKILL.md").write_text("someone's own pr skill", encoding="utf-8")
        lines = install.install_for_codex(["picks"])
        self.assertIn("copied   tdd (picks)", lines)
        self.assertTrue(any(line.startswith("kept") and "pr" in line for line in lines))
        self.assertEqual((self.codex / "skills/pr/SKILL.md").read_text(encoding="utf-8"), "someone's own pr skill")

        (self.codex / "skills/tdd/stale.md").write_text("from an older version", encoding="utf-8")
        install.install_for_codex(["picks"])
        self.assertFalse((self.codex / "skills/tdd/stale.md").exists())

    def test_claude_only_plugins_are_skipped(self):
        self.assertEqual(install.install_for_codex(["pstack"]), ["skipped  pstack: works only as a Claude Code plugin"])


class AutoUpdateTests(unittest.TestCase):

    def setUp(self):
        self.config = Path(tempfile.mkdtemp())
        patch = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.config)})
        patch.start()
        self.addCleanup(patch.stop)

    def settings(self) -> dict:
        return json.loads((self.config / "settings.json").read_text(encoding="utf-8"))

    def test_turns_auto_update_on_and_keeps_the_rest_of_the_settings(self):
        (self.config / "settings.json").write_text(json.dumps({"model": "opus"}), encoding="utf-8")
        install.turn_on_auto_update()
        self.assertEqual(self.settings()["model"], "opus")
        self.assertIs(self.settings()["extraKnownMarketplaces"][install.MARKETPLACE]["autoUpdate"], True)

    def test_a_choice_the_user_made_stands(self):
        (self.config / "settings.json").write_text(json.dumps(
            {"extraKnownMarketplaces": {install.MARKETPLACE: {"source": {}, "autoUpdate": False}}}), encoding="utf-8")
        self.assertIn("kept", install.turn_on_auto_update())
        self.assertIs(self.settings()["extraKnownMarketplaces"][install.MARKETPLACE]["autoUpdate"], False)


class MarketplaceTests(unittest.TestCase):

    def test_every_upstream_entry_is_pinned_to_a_full_commit(self):
        for name, plugin in install.plugins().items():
            if isinstance(plugin["source"], dict):
                self.assertRegex(plugin["source"].get("sha", ""), r"^[0-9a-f]{40}$", name)

    def test_the_team_set_exists_in_the_marketplace(self):
        self.assertLessEqual(set(install.TEAM_SET), set(install.plugins()))


if __name__ == "__main__":
    unittest.main()

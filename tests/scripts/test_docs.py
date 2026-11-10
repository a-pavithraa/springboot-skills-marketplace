"""The docs name every gate, hook, project skill and script test the repository ships.

A new one that no doc names is invisible to the user and to the next agent, so each must appear where a reader
looks for it. Whether the prose around the name is right stays a review job.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "plugins/springboot-architecture/skills/spring-boot-team-harness"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DocsNameWhatShipsTests(unittest.TestCase):

    def assert_named(self, names: list[str], doc: Path, aliases: dict[str, str] | None = None):
        content = text(doc)
        missing = [n for n in names if n not in content and (aliases or {}).get(n, n) not in content]
        self.assertEqual(missing, [], f"{doc.relative_to(ROOT)} doesn't name these")

    def test_every_gate_is_named_in_the_skill_and_the_agents_template(self):
        gates = sorted(p.stem for p in (HARNESS / "assets/tests").glob("*.java"))
        self.assert_named(gates, HARNESS / "SKILL.md")
        self.assert_named(gates, HARNESS / "assets/project/AGENTS.md")

    def test_every_hook_is_named_in_the_skill(self):
        hooks = sorted(p.name for p in (HARNESS / "assets/project/.claude/hooks").iterdir() if p.is_file())
        self.assert_named(hooks, HARNESS / "SKILL.md")

    def test_every_project_skill_is_named_in_the_readme_and_the_skill(self):
        skills = sorted(f"`{p.name}`" for p in (HARNESS / "assets/project-skills").iterdir() if p.is_dir())
        self.assert_named(skills, ROOT / "README.md")
        self.assert_named(skills, HARNESS / "SKILL.md")

    def test_every_script_test_is_described_in_the_tests_readme(self):
        tests = sorted(p.name for p in (ROOT / "tests/scripts").glob("test_*.py"))
        self.assert_named(tests, ROOT / "tests/README.md")


if __name__ == "__main__":
    unittest.main()

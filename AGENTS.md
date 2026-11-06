# springboot-skills-marketplace

Claude Code and Codex skills for Spring Boot 4. `README.md` describes each skill; `tests/README.md` describes every test.

- The team harness lives in `plugins/springboot-architecture/skills/spring-boot-team-harness/`: `SKILL.md`, `scripts/` (`apply_harness.py`, `baseline.py`), and `assets/`, which holds what it copies into a project (`project/` for `AGENTS.md`, hooks and CI, `tests/` for the gates, `project-skills/`).
- Script tests: `python -m unittest discover -s tests/scripts`, about four minutes on Windows. For one file: `python -m unittest tests.scripts.test_harness_hooks`.
- The harness end to end: `tests/harness-sample/check.sh all`, or `tests/harness-sample/check-in-docker.sh all` on Windows. On Gradle: `check-gradle.sh groovy` (or `kotlin`), or `check-gradle-in-docker.sh groovy`.
- This repository is public. Name no client, client project or client data in code, docs, commits or pull requests; write `a real codebase` instead.
- Before you edit, run `git status`. Changes this task didn't make belong to another session: work in a new worktree from `origin/main` (`git worktree add ../<name> -b <branch> origin/main`), and don't switch branches, stash or commit in that checkout.
- In a pull request's evidence, each item names a command run on this branch and what it printed.

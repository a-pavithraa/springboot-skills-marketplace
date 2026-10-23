---
name: spring-boot-team-harness
description: Adds a shared agent harness to a Maven Spring Boot 4 project so every teammate's Claude Code or Codex session works under the same rules. It writes AGENTS.md (read by both tools), a committed .claude/settings.json, ./mvnw verify gates that fail on null-safety bugs (NullAway with JSpecify), module-boundary breaches (Spring Modulith), unknown or deprecated Boot property keys, Spring mistakes that compile (ArchUnit) and unformatted code, Claude Code hooks that run those gates before a turn ends, and a CI workflow. Use when setting up or standardizing a Spring Boot repository for a team that uses coding agents, or when asked for guardrails, AGENTS.md, or consistent agent behaviour across developers.
---

# Spring Boot team harness

The harness steers the agent in three places. `AGENTS.md` tells it how this repository works before it starts. Hooks check its work before a turn ends, so it fixes its own mistakes. `./mvnw verify` in CI holds the same gates for every developer and every tool. Rules live in the build wherever they can: a gate holds whoever writes the code and costs no context.

## Apply it

1. Run the script from the project root. Preview with `--dry-run` first:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/apply_harness.py . --dry-run
   python3 ${CLAUDE_SKILL_DIR}/scripts/apply_harness.py .
   ```
   Run it in the Maven project's folder. When that folder is inside a larger repository (for example `backend/` next to `frontend/`), the CI workflow, `.claude/settings.json`, the hooks and `.gitattributes` go to the repository root, where GitHub and Claude Code read them, and the root `AGENTS.md` gets a line pointing to the project's own. The Stop hook then reacts only to changes in that folder.

   Pass `--no-modules` when the base package's subpackages are layers (`controller`, `service`, `domain`) rather than modules; Spring Modulith would report them as cycles.

   It adds only what the project lacks. In the pom, it skips any property, dependency or plugin that is already declared, so an existing Spotless or Spring Modulith setup stays as it is. It adds `CLAUDE.md` (one line, `@AGENTS.md`), `.claude/settings.json` and its two hook scripts, `.mvn/jvm.config`, the three tests, a CI workflow, and project skills in both `.claude/skills/` and `.agents/skills/`. It merges its permissions, hooks and plugin into an existing `.claude/settings.json`, adds its CI workflow only when no workflow runs Maven (as `harness-verify.yml` if `verify.yml` is taken), appends its gate section to an existing `AGENTS.md`, skips the boundary test when a test already calls `ApplicationModules.of(...)`, and never overwrites a file the team has edited. Rerun it after updating this plugin: it adds the pieces the project is missing and updates the files it owns (hooks, tests, project skills, its workflow) that nobody has changed since, which it tracks in `.claude/harness.lock`. It reports each edited one so you can merge the new version by hand. If `<build><plugins>` already configures `maven-compiler-plugin`, it stops: merge that part of `assets/pom/plugins.xml` by hand and run it again.
2. Run `./mvnw spotless:apply` and commit the result on its own, so the reformat stays out of later diffs. On an existing codebase, add that commit's hash to `.git-blame-ignore-revs` so `git blame` skips it.
3. Get `./mvnw verify` green. New code must meet the gates; code that already fails them is recorded, not rewritten:
   - If there are only a few findings, fix them with the user. Each NullAway finding is a question about what a missing value means, so don't guess.
   - Otherwise run `python3 ${CLAUDE_SKILL_DIR}/scripts/baseline.py .`. It marks each class NullAway rejects today `@NullUnmarked`, and records today's `CodeRulesTests` violations in `src/test/resources/archunit_store`. New code is checked in full, and a fixed violation drops out of the record. Remove `@NullUnmarked` from a class once it's fixed.
   Don't suppress warnings or skip tests to get green. The Stop hook only blocks on problems in files the agent changed, but until `verify` is green it can't fully check those either.
4. Draft the `Modules`, `Run and test` and `Team conventions` sections of `AGENTS.md` from the code, then go through them with the user. Read the packages, the pom, compose files, the test setup, and repeated patterns such as error handling, DTO mapping and naming. Write only what an agent would get wrong without being told: one line per module, the commands and services the app needs, and the conventions the code follows. Mark each convention you inferred `(inferred)`; the user confirms or deletes it. Leave out generic Spring advice and anything the code makes obvious, and keep the file short: every session reads all of it.
5. Commit everything, including `.claude/settings.json`, the marked classes and `archunit_store`.

## What each piece does

| File | Effect |
| --- | --- |
| `AGENTS.md` | Instructions both Claude Code and Codex read. Says that done means `./mvnw verify` passed, and how to fix each gate |
| `CLAUDE.md` | Imports `AGENTS.md` for Claude Code versions that don't read it directly |
| `.claude/settings.json` | Lets `./mvnw` run without prompts, blocks reading `.env` files, offers this plugin to every teammate, and registers the hooks |
| `.claude/hooks/verify-on-stop.sh` | SessionStart and Stop hook. It records the code each session starts from. When a turn ends and the session has changed the code under `src` or `pom.xml`, committed or not, it formats the code and runs the gates that need no Docker (compile with NullAway, `CodeRulesTests`, `ConfigurationKeysTests`, the module and ArchUnit tests). It blocks the turn only on errors in files the session changed, so Claude fixes its own mistakes and never code it didn't touch; when the build fails only elsewhere, it tells the user the change couldn't be fully verified. A formatting failure blocks too. It skips code that already passed, and gives up after one failed retry on the same code. A session that changes no code costs nothing; a check takes 25 to 75 s |
| `.claude/hooks/guard.sh` | PreToolUse hook. Refuses `git push --force`, `git reset --hard`, `git clean -f`, edits to a Flyway migration that is already on the main branch, and edits to the ArchUnit freeze record |
| `scripts/baseline.py` | For an existing codebase: marks the classes NullAway rejects today `@NullUnmarked` and records today's `CodeRulesTests` violations, so `verify` passes while new code is held to the gates |
| `ConfigurationKeysTests` | Fails on `spring.`, `management.`, `server.` and `logging.` keys that no dependency defines, or that are deprecated. Boot ignores those keys silently |
| `ModuleBoundariesTests` | Spring Modulith `verify()`: no use of another module's nested packages, no cycles |
| `CodeRulesTests` | ArchUnit rules for mistakes that compile and pass most tests: a class calling its own `@Transactional`, `@Async`, `@Cacheable` or `@Retryable` method (the proxy is skipped), controllers that start transactions or use repositories, `@Autowired` fields, `System.out`, Jackson 2 (Boot 4 ignores it), Spring's deprecated nullness annotations, and JUnit 4 tests (never run). Each failure message says how to fix it. It uses the project's ArchUnit or Taikai, and adds ArchUnit only when neither is declared |
| `.github/workflows/verify.yml` | Runs `./mvnw verify` on every pull request, so the gates hold for code nobody ran locally. Added only when no workflow already runs `mvnw` |
| pom gates | NullAway in JSpecify mode on main code at compile time (tests are excluded, since they routinely dereference response bodies), Spotless check |
| Project skills | `add-module` (module layout and test, for module-based projects) and `db-migration` (Flyway naming and safe changes, when the pom uses Flyway). Each tool sees only their names and descriptions until one is used |

## Limits

- Maven only. A Gradle build needs the same gates written as Gradle plugins.
- The hooks are Claude Code only. Codex sessions get `AGENTS.md`, the project skills and the CI gates, and `AGENTS.md` tells them to run `./mvnw verify` themselves.
- The hooks are bash scripts. On Windows, Claude Code runs them with Git for Windows; without it they fail.
- Tool versions are pinned in the pom properties. Update them together and rerun `./mvnw verify`.

## MCP servers

Add none by default. Each server's tool definitions take context in every session, and the gates above need none. If the team already runs SonarQube, its MCP server (`sonarsource/sonarqube-mcp`) can show issues and quality gates. It needs a SonarQube Cloud or Server token and Docker. Limit it with `SONARQUBE_TOOLSETS=issues,quality-gates` and `SONARQUBE_READ_ONLY=true`, and keep the token in each developer's environment, never in the repository.

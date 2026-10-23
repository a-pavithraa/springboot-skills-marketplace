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

   It adds only what the project lacks. In the pom, it skips any property, dependency or plugin that is already declared, so an existing Spotless or Spring Modulith setup stays as it is. It adds `CLAUDE.md` (one line, `@AGENTS.md`), `.claude/settings.json` and its two hook scripts, `.mvn/jvm.config`, the three tests, a CI workflow, and project skills in both `.claude/skills/` and `.agents/skills/`. It merges its permissions, hooks and plugin into an existing `.claude/settings.json`, adds its CI workflow only when no workflow runs Maven (as `harness-verify.yml` if `verify.yml` is taken), appends its gate section to an existing `AGENTS.md`, skips the boundary test when a test already calls `ApplicationModules.of(...)`, and never overwrites a file. Rerun it after updating this plugin: it adds only the pieces the project is missing. If `<build><plugins>` already configures `maven-compiler-plugin`, it stops: merge that part of `assets/pom/plugins.xml` by hand and run it again.
2. Run `./mvnw spotless:apply`, then `./mvnw verify`.
3. Fix what NullAway reports. On an existing codebase there can be many findings. Fix them, or narrow `harness.base-package` in the pom to the packages that are ready, and widen it later. Don't suppress warnings to get green.
4. Draft the `Modules`, `Run and test` and `Team conventions` sections of `AGENTS.md` from the code, then go through them with the user. Read the packages, the pom, compose files, the test setup, and repeated patterns such as error handling, DTO mapping and naming. Write only what an agent would get wrong without being told: one line per module, the commands and services the app needs, and the conventions the code follows. Mark each convention you inferred `(inferred)`; the user confirms or deletes it. Leave out generic Spring advice and anything the code makes obvious, and keep the file short: every session reads all of it.
5. Commit everything, including `.claude/settings.json`.

## What each piece does

| File | Effect |
| --- | --- |
| `AGENTS.md` | Instructions both Claude Code and Codex read. Says that done means `./mvnw verify` passed, and how to fix each gate |
| `CLAUDE.md` | Imports `AGENTS.md` for Claude Code versions that don't read it directly |
| `.claude/settings.json` | Lets `./mvnw` run without prompts, blocks reading `.env` files, offers this plugin to every teammate, and registers the two hooks |
| `.claude/hooks/verify-on-stop.sh` | Stop hook. When a turn ends and the code under `src` or `pom.xml` differs from what last passed, committed or not, it formats the code and runs the gates that need no Docker (compile with NullAway, `CodeRulesTests`, `ConfigurationKeysTests`, the module and ArchUnit tests). On failure, Claude gets the errors and keeps working. A formatting failure blocks too. It records what passed in `.git/harness/`, skips code it already passed, and gives up after one failed retry on the same code, so a problem Claude can't fix is reported instead of looping. 25 to 75 s when code changed, 1 s otherwise |
| `.claude/hooks/guard.sh` | PreToolUse hook. Refuses `git push --force`, `git reset --hard`, `git clean -f`, and edits to a Flyway migration that is already on the main branch |
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

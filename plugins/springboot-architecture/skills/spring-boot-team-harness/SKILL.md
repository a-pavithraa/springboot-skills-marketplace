---
name: spring-boot-team-harness
description: Adds a shared agent harness to a Maven Spring Boot 4 project so every teammate's Claude Code or Codex session works under the same rules. It writes AGENTS.md (read by both tools), a committed .claude/settings.json, and ./mvnw verify gates that fail on null-safety bugs (NullAway with JSpecify), module-boundary breaches (Spring Modulith), unknown or deprecated Boot property keys, and unformatted code. Use when setting up or standardizing a Spring Boot repository for a team that uses coding agents, or when asked for guardrails, AGENTS.md, or consistent agent behaviour across developers.
---

# Spring Boot team harness

The harness puts the rules in the build, not in prompts. A gate in `./mvnw verify` holds for every developer, every agent and CI, and costs no context. `AGENTS.md` only says how to run the gates and what the team decided.

## Apply it

1. Run the script from the project root. Preview with `--dry-run` first:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/apply_harness.py . --dry-run
   python3 ${CLAUDE_SKILL_DIR}/scripts/apply_harness.py .
   ```
   Pass `--no-modules` when the base package's subpackages are layers (`controller`, `service`, `domain`) rather than modules; Spring Modulith would report them as cycles.

   It adds only what the project lacks. In the pom, it skips any property, dependency or plugin that is already declared, so an existing Spotless or Spring Modulith setup stays as it is. It adds `CLAUDE.md` (one line, `@AGENTS.md`), `.claude/settings.json`, `.mvn/jvm.config`, the two tests, and project skills in both `.claude/skills/` and `.agents/skills/`. It appends its gate section to an existing `AGENTS.md`, skips the boundary test when a test already calls `ApplicationModules.of(...)`, and never overwrites a file. If `<build><plugins>` already configures `maven-compiler-plugin`, it stops: merge that part of `assets/pom/plugins.xml` by hand and run it again.
2. Run `./mvnw spotless:apply`, then `./mvnw verify`.
3. Fix what NullAway reports. On an existing codebase there can be many findings. Fix them, or narrow `harness.base-package` in the pom to the packages that are ready, and widen it later. Don't suppress warnings to get green.
4. Fill in the `Modules` and `Team conventions` sections of `AGENTS.md` with the user. Keep only what a newcomer could not guess. Generic Spring advice doesn't belong there.
5. Commit everything, including `.claude/settings.json`.

## What each piece does

| File | Effect |
| --- | --- |
| `AGENTS.md` | Instructions both Claude Code and Codex read. Says that done means `./mvnw verify` passed, and how to fix each gate |
| `CLAUDE.md` | Imports `AGENTS.md` for Claude Code versions that don't read it directly |
| `.claude/settings.json` | Lets `./mvnw` run without prompts, blocks reading `.env` files, and runs `spotless:apply` when Claude stops, so formatting never fails a build |
| `ConfigurationKeysTests` | Fails on `spring.`, `management.`, `server.` and `logging.` keys that no dependency defines, or that are deprecated. Boot ignores those keys silently |
| `ModuleBoundariesTests` | Spring Modulith `verify()`: no use of another module's nested packages, no cycles |
| pom gates | NullAway in JSpecify mode on main code at compile time (tests are excluded, since they routinely dereference response bodies), Spotless check |
| Project skills | `add-module` (module layout and test, for module-based projects) and `db-migration` (Flyway naming and safe changes, when the pom uses Flyway). Each tool sees only their names and descriptions until one is used |
| Team plugin | `.claude/settings.json` offers this plugin to every teammate (`enabledPlugins`), so `code-reviewer`, `springboot-migration` and `writing-springboot-tests` are the same for everyone |

## Limits

- Maven only. A Gradle build needs the same gates written as Gradle plugins.
- Codex has no equivalent of the Stop hook here, so Codex sessions rely on `AGENTS.md` to run `spotless:apply`.
- Tool versions are pinned in the pom properties. Update them together and rerun `./mvnw verify`.

## MCP servers

Add none by default. Each server's tool definitions take context in every session, and the gates above need none. If the team already runs SonarQube, its MCP server (`sonarsource/sonarqube-mcp`) can show issues and quality gates. It needs a SonarQube Cloud or Server token and Docker. Limit it with `SONARQUBE_TOOLSETS=issues,quality-gates` and `SONARQUBE_READ_ONLY=true`, and keep the token in each developer's environment, never in the repository.

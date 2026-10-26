# Spring Boot Skills Marketplace

Claude Code and Codex skills for Spring Boot 4 and Java 25. The main one, `spring-boot-team-harness`, gives every developer on a team the same agent setup and makes `./mvnw verify` fail on the mistakes agents make. The others create, migrate, test and review Spring Boot projects.

Every skill was trialled with and without it, and content that made no difference was cut. The results are [below](#trial-results).

## The team harness

`scripts/apply_harness.py` adds the harness to a Maven project. It adds only what the project lacks, so it works on existing services, on a Maven project in a subfolder, and on top of what progen set up. `creating-springboot-projects` runs it as its last step. Rerun it after updating the plugin.

It steers the agent at three points:

1. **Before it starts.** `AGENTS.md`, which both Claude Code and Codex read, describes the repository: modules, how to run and test it, conventions, and how to work (plan larger changes first, write a failing test first for bugs, review before the pull request). The agent drafts the repository-specific sections from the code, and the team corrects them.
2. **Before it says it's done.** `AGENTS.md` tells the agent to run `./mvnw verify`. A Claude Code Stop hook runs the gates that need no Docker when a turn ends with changed code, and sends any errors back to the agent. A PreToolUse hook refuses force-pushes, `git reset --hard`, `git clean -f`, edits to Flyway migrations already on `main`, and edits to the rule tests and the ArchUnit freeze record, so an agent can't weaken a rule to get its change through.
3. **Before merge.** A CI workflow runs `./mvnw verify` on every pull request, unless one already runs `mvnw`.

`./mvnw verify` fails on:

- a null-safety bug (NullAway with JSpecify)
- a module-boundary breach (Spring Modulith)
- a Boot property key that no dependency defines, or a deprecated one, since Boot ignores both silently
- code that compiles but breaks at runtime (ArchUnit): a class calling its own `@Transactional` or `@Cacheable` method, controllers using repositories or returning JPA entities, `@Retryable` or `@Async` that nothing switches on, a transaction held open across an HTTP call, HTTP clients with no timeouts, `@ManyToOne` left eager, enums stored by position, `@ManyToMany` mapped as a `List`, `@Autowired` fields, Jackson 2 code that Boot 4 ignores, and JUnit 4 or `@Disabled` tests that never run
- build shortcuts that pass the tests while production lacks the feature: a starter in `test` scope, `spring-boot-autoconfigure-classic`, Flyway migrations that Boot 4 never runs, and a schema from `ddl-auto` instead of the migrations
- unformatted code (Spotless)

Each failure message says how to fix it. On an existing codebase, `scripts/baseline.py` makes `verify` pass on day one: it marks the classes NullAway rejects today `@NullUnmarked` and records today's ArchUnit violations with `FreezingArchRule`. New code gets the full checks, and fixed violations drop out of the record. The Stop hook blocks only on errors in files the session changed.

The harness also commits two project skills, `add-module` and `db-migration`, and enables this plugin for every teammate through `enabledPlugins`. It adds no MCP servers.

### Why it's built this way

- Rules go in build checks, because instructions in `CLAUDE.md` are advisory and hooks are deterministic ([Claude Code best practices](https://code.claude.com/docs/en/best-practices)). OpenAI's Codex team enforces architecture with linters whose messages tell the agent how to fix the problem ([Harness engineering](https://openai.com/index/harness-engineering/)).
- Fast checks run on every change, slow ones after integration ([Birgitta Böckeler, Harness engineering](https://martinfowler.com/articles/harness-engineering.html)).
- `AGENTS.md` stays short. OpenAI found one large `AGENTS.md` failed and keeps theirs to about 100 lines.
- The gates check structure, not behaviour. For behaviour, `AGENTS.md` asks for a full-API test (the whole app on a random port, with Testcontainers) of each endpoint a change touches.

## Install

```bash
git clone https://github.com/a-pavithraa/springboot-skills-marketplace.git
cd springboot-skills-marketplace
python3 install.py            # Claude Code
python3 install.py --codex    # Codex
```

The script needs Python 3.10 or later and is safe to rerun. For Claude Code it installs at user scope and turns on auto-update for this marketplace. For Codex it copies the skill folders into `~/.codex/skills`.

Without the script, in Claude Code:

```bash
/plugin marketplace add a-pavithraa/springboot-skills-marketplace
/plugin install springboot-architecture@springboot-skills-marketplace
```

Or copy the folders by hand: `cp -r plugins/springboot-architecture/skills/* ~/.claude/skills/` (or `~/.codex/skills/`).

### Optional third-party skills

The marketplace also lists plugins by other authors, unchanged and pinned to a reviewed commit. Report problems with them to their authors.

| Plugin | What it adds | Source |
|--------|--------------|--------|
| `mattpocock-picks` | grilling, pr, tdd, diagnosing-bugs, prototype, domain-modeling, handoff, writing-for-agents | [mattpocock/skills](https://github.com/mattpocock/skills) |
| `html-plan` | an implementation plan as one interactive HTML page | [claude-plugins-community](https://github.com/anthropics/claude-plugins-community/tree/main/html-plan), by Thariq Shihipar |
| `grill-page` | a grilling interview answered through clickable options | [build-compass](https://github.com/a-pavithraa/build-compass) |
| `pstack` | technical-writing, unslop, blast-radius, correct and more; Claude Code only | [cursor/plugins](https://github.com/cursor/plugins/tree/main/harness/pstack), by Lauren Tan |

`python3 install.py --with extras` adds the first three, and `--with extras,pstack` adds all four. [GUIDE.md](GUIDE.md) shows how the team workflow uses them.

## Skills

| Skill | Use it to |
|-------|-----------|
| `spring-boot-team-harness` | Add `AGENTS.md`, build gates, hooks and CI to a project, as described above |
| `creating-springboot-projects` | Start a service. It asks about the domain and team, picks an architecture, generates the project with [progen](https://github.com/sivaprasadreddy/progen) or Spring Initializr, and applies the team harness |
| `springboot-migration` | Upgrade to Boot 4, Java 25, Spring Modulith 2 and Testcontainers 2. It scans the project, then changes dependencies, code and config in that order |
| `writing-springboot-tests` | Test HTTP clients, retries, timeouts, transactions and Kafka listeners, with templates run against Postgres, Kafka and WireMock. Check who may call each route, with test logins that go through the app's own role mapping |
| `code-reviewer` | Review code or tests for Boot 4 changes, architecture fit and performance traps such as N+1 queries. It proves each test finding by breaking the guarded line and showing the test stays green |

Claude Code and Codex both load a skill when a request matches its description. To make sure one loads, name it: `$code-reviewer review this service` in Codex. Automatic loading has been trialled only in Claude Code ([Scenario 25](tests/baseline-results/scenario-25.md)).

`creating-springboot-projects` and `code-reviewer` cover five architectures, from simplest to most complex: Layered, Package-by-Module, Modular Monolith, Tomato (rich domain with value objects) and DDD+Hexagonal. Start with the simplest that fits.

## Trial results

Each trial ran the same task in fresh sessions with and without a skill, and scored the result with planted bugs, PIT mutation scores or Hibernate statement counts. Most ran once per arm, so read them as direction, not proof. Full records are in [`tests/baseline-results/`](tests/baseline-results/).

| # | Skill | Model | Result | Outcome |
|---|-------|-------|--------|---------|
| 10 | writing-springboot-tests | default | Both caught the planted bug. The skill raised the PIT score from 98% to 100%, at about twice the tokens | Small gain |
| 11 | writing-springboot-tests | Sonnet | Caught 4 to 5 of 5 edge bugs against 1 of 5. The baseline's mocks hid broker bugs, and 3 of its tests failed on correct code | Gain |
| 12 | writing-springboot-tests | Sonnet | On edge bugs the skill doesn't name, the baseline caught 4 of 4 and the skill 2 of 4, because the agent copied template shortcuts. The skill now says to take cases from the contract | Loss, fixed |
| 13 | code-reviewer (tests) | Sonnet | Both found all 6 defects. The skill proved 3 by running them, the baseline 1 | Gain in proof only |
| 14 | spring-data-jpa | Sonnet | Same fixes, identical statement counts | No gain, skill retired |
| 15 | springboot-migration | Sonnet | Same handling of silent hazards. The skill targeted 4.1 with complete dependencies; the baseline missed a starter 4.1 needs | Small gain |
| 16 | creating-springboot-projects | Sonnet | The baseline started on Boot 3. The skill used Boot 4.1 and Testcontainers 2, and added the architecture test once the workflow named it | Gain |
| 17 | code-reviewer | Sonnet | Old and trimmed `SKILL.md` both found 13 of 13 planted issues, with 42% fewer words | No loss from trim |
| 18 | code-reviewer (tests) | Sonnet | Proved 16 gaps in a green, well-kept suite | Gain, no comparison arm |
| 19 | team harness | Sonnet | With `AGENTS.md` the agent ran `verify` and avoided both traps it fell into without. The Stop hook caught nothing extra | Gain from `AGENTS.md` |
| 20 | code-reviewer | Sonnet | The fresh-context review offer appeared only when placed as a step before the review | Works |
| 21 | run-app (harness) | Sonnet | Found nothing the tests missed and couldn't sign in to secured endpoints | Dropped |
| 22 | harness, code-reviewer | Sonnet | Agents copy the comment density of the code they read. Pruning that code halved new comments | Rule and pruning pass added |
| 23 | code-reviewer | Haiku | 13 of 13 with the skill, 9 of 13 without. Without it, Haiku missed the Boot 4 changes | Gain |
| 24 | spring-data-jpa | Haiku | Gained pagination, lost a bulk update | No net gain, retirement holds |
| 25 | all five | Sonnet, Haiku | New descriptions loaded the right skill on Sonnet 15 of 15 and Haiku 11 of 15. With an `AGENTS.md` skills section, Haiku loaded it on all 10 earlier misses. No false triggers | Descriptions rewritten |

Fixtures and run scripts are in `tests/fixtures/`. [`tests/README.md`](tests/README.md) explains how to add a trial. The bundled scripts have their own tests, which need no network or Docker:

```bash
python3 -m unittest discover -s tests/scripts -v
```

## Prerequisites

- Claude Code or Codex
- Python 3.10 or later for `install.py` and the skills' scripts. The `python3` that ships with macOS is 3.9
- Java 17 or later, Java 25 for new projects. A project with the harness needs JDK 21.0.8 or later, because Error Prone does
- Maven or Gradle
- Optional: [progen](https://github.com/sivaprasadreddy/progen) (`go install github.com/sivaprasadreddy/progen@latest`)

## Credits

- Architecture patterns: [Siva Prasad Reddy](https://github.com/sivaprasadreddy), from [spring-boot-application-architecture-patterns](https://github.com/sivaprasadreddy/spring-boot-application-architecture-patterns)
- Project generator: [progen](https://github.com/sivaprasadreddy/progen)
- Spring Boot 4 features: [spring-boot-4-features](https://github.com/sivaprasadreddy/spring-boot-4-features)
- Modular monolith reference: [spring-modular-monolith](https://github.com/sivaprasadreddy/spring-modular-monolith)
- Marketplace inspiration: [sivalabs-marketplace](https://github.com/sivaprasadreddy/sivalabs-marketplace)
- JPA and Hibernate practices: [Vlad Mihalcea](https://vladmihalcea.com/blog/)

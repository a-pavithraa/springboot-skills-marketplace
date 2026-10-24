# Spring Boot Skills Marketplace

Claude Code skills that help you build Spring Boot apps with architecture that actually fits your needs.

## Why This Exists

Projects that start simple tend to grow messy. These skills help you pick the right architecture for where you are now—with a clear path forward when things get complex.

> **Start simple. Add complexity only when complexity demands it.**

Built on patterns from [spring-boot-application-architecture-patterns](https://github.com/sivaprasadreddy/spring-boot-application-architecture-patterns).

## Architecture Patterns (Progressive)

| Pattern | Complexity | When to Use |
|---------|-----------|-------------|
| **Layered** | ⭐ Low | Simple CRUD, prototypes, MVPs |
| **Package-by-Module** | ⭐⭐ Low-Medium | 3-5 distinct features, medium apps |
| **Modular Monolith** | ⭐⭐ Medium | Need module boundaries, Spring Modulith |
| **Tomato** | ⭐⭐⭐ Medium-High | Rich domain, Value Objects, type safety |
| **DDD+Hexagonal** | ⭐⭐⭐⭐ High | Complex domains, CQRS, infra independence |

## Installation

> **Using Codex?** Codex installation and usage instructions are inline below — see [Codex (Manual Installation)](#codex-manual-installation) and [Usage → Codex](#codex).

### Everything, in one command

The marketplace also lists a few skills from other authors that work well with the Spring Boot ones: grilling, PR writing, TDD and debugging from Matt Pocock, `html-plan`, and `grill-page`. Each entry points to the author's own repository, pinned to a reviewed commit, so you install their work unchanged. To install the Spring Boot plugin and those skills:

```bash
git clone https://github.com/a-pavithraa/springboot-skills-marketplace.git
cd springboot-skills-marketplace
python3 install.py            # Claude Code; add --with pstack for the optional pstack plugin
python3 install.py --codex    # Codex
```

The script is safe to rerun. For Claude Code it installs the plugins at user scope and turns on auto-update for this marketplace. For Codex it copies the skill folders at the pinned commits. [GUIDE.md](GUIDE.md) is a one-page guide to what each skill does and what to type.

### Claude Code (Plugin Marketplace)

```bash
/plugin marketplace add a-pavithraa/springboot-skills-marketplace
/plugin enable a-pavithraa/springboot-skills-marketplace
/plugin install springboot-architecture@springboot-skills-marketplace
```

### Claude Code (Manual Installation)

```bash
# Clone or download this repository
git clone https://github.com/a-pavithraa/springboot-skills-marketplace.git

# Copy skills to Claude Code skills directory
cp -r springboot-skills-marketplace/plugins/springboot-architecture/skills/* ~/.claude/skills/
```

### Codex (Manual Installation)

```bash
# Clone or download this repository
git clone https://github.com/a-pavithraa/springboot-skills-marketplace.git

# Copy skills to Codex skills directory
mkdir -p ~/.codex/skills
cp -r springboot-skills-marketplace/plugins/springboot-architecture/skills/* ~/.codex/skills/
```

## Usage

### Claude Code

Skills are automatically discovered and loaded when relevant. Claude will invoke them based on your request:

```
You: "I need to create a new Spring Boot microservice"
Claude: [Automatically loads creating-springboot-projects skill]
```

You can also explicitly request a skill:
```
You: "Use the code-reviewer skill to review this module"
```

### Codex

Skills must be manually invoked using the `$skill-name` syntax:

```
using $creating-springboot-projects create a new order service
using $springboot-migration upgrade to Spring Boot 4
using $code-reviewer review this service implementation
using $writing-springboot-tests add tests for the payment client
```

For detailed reference chapters, include the path:
```
using $code-reviewer and ~/.codex/skills/code-reviewer/references/jpa-performance.md review the persistence code
```

## Available Skills

### creating-springboot-projects

Asks a few questions about your project, then builds the right architecture from the start.

What you get: assessment-driven scaffolding, base project generation with [progen](https://github.com/sivaprasadreddy/progen) (when installed) or Spring Initializr, and templates for Value Objects, Rich Entities, CQRS patterns, converters—whatever your chosen architecture needs. Architecture rules come as a [Taikai](https://github.com/enofex/taikai) test that fails the build when code breaks them: self-invoked `@Transactional`/`@Retryable` methods, controllers using repositories, field injection, `@Disabled` tests. Each rule was verified on Boot 4.1.1 against a planted violation.

**Quick assessment covers:**
- Domain complexity (CRUD vs. business rules)
- Team size and project lifespan
- Type safety requirements
- Bounded contexts

### springboot-migration

Step-by-step migration to Spring Boot 4 + Java 25 (with Spring Modulith 2 and Testcontainers 2 support).

Scans your project first, then walks through dependencies → code → config in phases. Includes retry/resilience patterns and references for each upgrade target.

### code-reviewer

Sanity-checks your Boot 4 / Java 25 project for architecture fit and performance gotchas.

> The former `spring-data-jpa` skill was retired in favour of `code-reviewer/references/jpa-performance.md`: in a trial, Sonnet fixed every planted JPA problem the same way with and without it (`tests/baseline-results/scenario-14.md`).

Covers all five architecture patterns (when to use, when to avoid), plus checklists for events, CQRS, Modulith boundaries. Catches N+1 queries, missing caches, virtual thread pinning on Java 21-23, misuse of preview APIs, and other performance traps.

Use this when you want a second opinion or need to decide if it's time to evolve your architecture.

It also reviews tests: which bugs a suite would let through, which tests fail on correct code, and which contract clauses have no test. It proves each finding by running it, for example by breaking the guarded line and showing the test stays green. In trials it found the same defects as a plain review, with more of them proven (`tests/baseline-results/scenario-13.md`). On a real, green suite it proved 16 gaps, such as access rules tested on one route only and requests to external APIs that no test inspects (`scenario-18.md`).

Its `SKILL.md` keeps only what the model gets wrong: Boot 4 and JSpecify changes, the reference map, and the proof steps. General security, performance and architecture checklists were removed after Sonnet found every planted issue of those kinds with and without them (`scenario-17.md`).

### writing-springboot-tests

For tests where the framework decides whether a test proves anything: calls between services, retries, timeouts, transactions, and messaging. It provides Spring Boot 4.1 templates that were run against Postgres, Kafka and WireMock: outbound HTTP clients (4xx, 5xx, timeouts, retries, unusable answers), Kafka listeners (redelivery, poison messages, the dead-letter topic), and events published only after commit. It also lists the framework traps that make such tests pass silently, and the rule to take cases from the documented contract.

Trials on Sonnet showed that general testing advice (slice vs `@SpringBootTest`, no getter tests) made no difference, because the model already follows it. So this skill is deliberately small. See `tests/baseline-results/scenario-11.md` to `scenario-13.md`.

### spring-boot-team-harness

Gives every developer on a team the same agent setup, in Claude Code or Codex. It steers the agent in three places:

- **Before it starts:** `AGENTS.md`, which both tools read, says how this repository works: its modules, how to run and test it, the team's conventions, and how to work (plan first for larger changes, a failing test first for bugs, a review before the pull request). The agent drafts the repository-specific sections from the code, and the team corrects them.
- **Before it says it's done:** a Claude Code Stop hook runs the gates that need no Docker whenever a turn ends with changed code. On failure, the agent gets the errors and keeps working, so it fixes its own mistakes. A second hook refuses force-pushes, `git reset --hard`, `git clean -f`, and edits to Flyway migrations already on the main branch.
- **Before merge:** a CI workflow runs `./mvnw verify` on every pull request, unless one already runs `mvnw`.

`./mvnw verify` fails the build on:

- a null-safety bug (NullAway with JSpecify);
- a module-boundary breach (Spring Modulith);
- a Boot property key that no dependency defines, or one that is deprecated (Boot ignores such keys silently);
- mistakes that compile but break at runtime (ArchUnit): a class calling its own `@Transactional` or `@Cacheable` method, controllers using repositories, `@Autowired` fields, Jackson 2 code that Boot 4 ignores, and JUnit 4 tests that never run;
- unformatted code (Spotless).

Each failure message says how to fix the problem. On an existing codebase, `scripts/baseline.py` makes `verify` pass on day one without lowering the bar for new code: it marks the classes NullAway rejects today `@NullUnmarked`, and records today's rule violations with ArchUnit's `FreezingArchRule`. New code is checked in full, and fixed violations drop out of the record. The Stop hook does the same per session: it only blocks on errors in files the agent changed, and stays silent when a session changed no code. The harness also commits two project skills, `add-module` and `db-migration`, to both `.claude/skills/` and `.agents/skills/`, and offers this plugin to every teammate through `enabledPlugins`. `scripts/apply_harness.py` adds only what a project lacks, so it works on existing services, including a Maven project in a subfolder of a larger repository, and keeps what progen already set up. Rerun it after updating the plugin to pick up new pieces. `creating-springboot-projects` runs it as its last step.

Each gate, rule and hook was checked against a planted violation. On a fresh progen project, NullAway found three methods that return `null` without declaring it, and the key test found two Spring Modulith event settings that no dependency reads. The harness adds no MCP servers, so day-to-day sessions load only the short `AGENTS.md` and the project skills' names and descriptions.

#### Why it's built this way

- **Rules go in checks, not prose.** Instructions in `CLAUDE.md` are advisory, while hooks "are deterministic and guarantee the action happens" ([Best practices for Claude Code](https://code.claude.com/docs/en/best-practices)). OpenAI's Codex team enforces its architecture "with custom linters and structural tests", and writes the lint messages "to inject remediation instructions into agent context" ([Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)).
- **The agent checks its own work before it stops.** Anthropic's guidance names a Stop hook as the deterministic way to block a turn from ending until a check passes ([Best practices for Claude Code](https://code.claude.com/docs/en/best-practices); [hooks reference](https://code.claude.com/docs/en/hooks)). Birgitta Böckeler calls such checks sensors, and recommends running the fast, deterministic ones "on every change, alongside the agent", and the slow ones after integration ([Harness engineering](https://martinfowler.com/articles/harness-engineering.html)).
- **`AGENTS.md` is a short map.** OpenAI's team found that "one big `AGENTS.md`" failed, and keeps theirs to about 100 lines as a table of contents. Anthropic's test for each line is "Would removing this cause Claude to make mistakes?" Microsoft ISE adopted `AGENTS.md` and repository skills because "every invocation started from zero context", and keeps them in the repository so they change through code review ([Coordinating AI-Assisted Development with AGENTS.md and Skills](https://devblogs.microsoft.com/ise/ai-assisted-development-agents-skills-copilot-cli/)). [AGENTS.md](https://agents.md/) is the format both Claude Code and Codex read.
- **Behaviour is the open problem.** Böckeler calls functional correctness "the elephant in the room", and Anthropic's long-running agent harness relies on end-to-end checks of the running app ([Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)). These gates check structure, so tests and review still carry behaviour.

## Usage Examples

**"I need a REST API for products with basic CRUD."**
→ Asks about your domain, team, and timeline. Suggests Layered architecture. Generates scaffolding.

**"I need an order service with payments and inventory rules."**
→ Assesses complexity. Recommends Tomato architecture. Generates value objects, rich entities, CQRS services.

**"My product search is slow."**
→ `code-reviewer` checks the persistence code for N+1 queries, unbounded reads and projection gaps, including the Hibernate 7 specifics in `jpa-performance.md`.

**"We need to migrate from Boot 3 to Boot 4."**
→ Runs migration scanner, plans phased upgrade (dependencies → code → config), applies and verifies each step.

**"Add tests for the payment client and the restock listener."**
→ Takes the cases from the provider's documented contract, tests against WireMock and a real Kafka broker, shows each test failing once, and reports any test that fails on the current code as a likely bug.

**"Review the tests in this module."**
→ Says which bugs the suite would let through and which tests fail on correct code, and proves each finding by running it.

**"Can you review our Boot 4 service for issues?"**
→ Checks architecture pattern fit, hunts for performance problems (N+1, missing caches, virtual thread pinning on Java 21-23, entity leaks).

## Templates & Assets

**Architecture templates** (`creating-springboot-projects/assets/`)
Value Objects, Rich Entities, CQRS services, converters, REST controllers, Flyway migrations, Testcontainers, ProblemDetail handlers, Taikai architecture rules.

**Test templates** (`writing-springboot-tests/assets/`)
Service unit test, `@WebMvcTest` slice with `MockMvcTester`, `@DataJpaTest` with Testcontainers, `RestTestClient` end-to-end test with WireMock, HTTP client failure modes with WireMock, Kafka listener and event publication tests, shared `TestcontainersConfiguration`, PIT plugin config.

**Reviewer references** (`code-reviewer/references/`)
Architecture patterns, decision matrices, performance checklists, JPA/Hibernate 7 performance, and test review. The testing references (traps that let a test pass without proving anything, and the Boot 4 test toolkit with PIT) are under `testing/`.

## Testing Skills

`tests/baseline-scenarios.md` defines Scenarios 10–18. Each runs the same task with and without a skill and scores the result with planted bugs, PIT mutation scores or Hibernate statement counts. The recorded runs are in `tests/baseline-results/`. See `tests/README.md`.

**Script tests** (migration scanner, progen helper and new-project check, stdlib only, no network or Docker):
```bash
python3 -m unittest discover -s tests/scripts -v
```

On Windows, the progen tests run their fake `progen` and `java` through `sh` from Git for Windows, and are skipped without it.

## Prerequisites

- Claude Code CLI
- Java 17+ (Java 25 recommended for new projects)
- Optional: [progen](https://github.com/sivaprasadreddy/progen) for base project generation (`go install github.com/sivaprasadreddy/progen@latest`)
- Maven or Gradle
- Spring Boot 4.1+ familiarity

## Evolution Path

Start simple, evolve as needed:

```text
Layered → Package-by-Module → Modular Monolith → Tomato → DDD+Hexagonal
```

## Credits

- Architecture patterns: [Siva Prasad Reddy](https://github.com/sivaprasadreddy)
- Project generator: [progen](https://github.com/sivaprasadreddy/progen)
- Spring Boot 4 features: [spring-boot-4-features](https://github.com/sivaprasadreddy/spring-boot-4-features)
- Modular monolith reference: [spring-modular-monolith](https://github.com/sivaprasadreddy/spring-modular-monolith)
- Marketplace inspiration: [sivalabs-marketplace](https://github.com/sivaprasadreddy/sivalabs-marketplace)
- JPA/Hibernate best practices: [Vlad Mihalcea](https://vladmihalcea.com/blog/)

The marketplace also lists these plugins, unchanged and pinned. Their authors maintain them, and issues belong in their repositories:

- `mattpocock-picks`: eight skills from [Matt Pocock's skills](https://github.com/mattpocock/skills) (MIT)
- `html-plan`: by Thariq Shihipar, from [claude-plugins-community](https://github.com/anthropics/claude-plugins-community/tree/main/html-plan) (MIT)
- `grill-page`: from [build-compass](https://github.com/a-pavithraa/build-compass) (MIT)
- `pstack`: by Lauren Tan, from [cursor/plugins](https://github.com/cursor/plugins/tree/main/harness/pstack) (MIT)

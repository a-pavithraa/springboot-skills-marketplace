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

What you get: assessment-driven scaffolding, base project generation with [progen](https://github.com/sivaprasadreddy/progen) (when installed) or Spring Initializr, and templates for Value Objects, Rich Entities, CQRS patterns, converters—whatever your chosen architecture needs.

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

It also reviews tests: which bugs a suite would let through, which tests fail on correct code, and which contract clauses have no test. It proves each finding by running it, for example by breaking the guarded line and showing the test stays green. In trials it found the same defects as a plain review, with more of them proven (`tests/baseline-results/scenario-13.md`).

### writing-springboot-tests

For tests where the framework decides whether a test proves anything: calls between services, retries, timeouts, transactions, and messaging. It provides Spring Boot 4.1 templates that were run against Postgres, Kafka and WireMock: outbound HTTP clients (4xx, 5xx, timeouts, retries, unusable answers), Kafka listeners (redelivery, poison messages, the dead-letter topic), and events published only after commit. It also lists the framework traps that make such tests pass silently, and the rule to take cases from the documented contract.

Trials on Sonnet showed that general testing advice (slice vs `@SpringBootTest`, no getter tests) made no difference, because the model already follows it. So this skill is deliberately small. See `tests/baseline-results/scenario-11.md` to `scenario-13.md`.

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
Value Objects, Rich Entities, CQRS services, converters, REST controllers, Flyway migrations, Testcontainers, ProblemDetail handlers.

**Test templates** (`writing-springboot-tests/assets/`)
Service unit test, `@WebMvcTest` slice with `MockMvcTester`, `@DataJpaTest` with Testcontainers, `RestTestClient` end-to-end test with WireMock, HTTP client failure modes with WireMock, Kafka listener and event publication tests, shared `TestcontainersConfiguration`, PIT plugin config.

**Reviewer references** (`code-reviewer/references/`)
Architecture patterns, decision matrices, performance checklists, JPA/Hibernate 7 performance, and test review. The testing references (test smells, service-edge traps, the Boot 4 test toolkit, proving tests) are under `testing/`.

## Testing Skills

Want to verify skills work as intended? See the `tests/` directory for baseline scenarios.

**Quick start:**
```bash
# Run one scenario in 5 minutes
cd tests
cat QUICKSTART.md
```

**Full test suite:**
- 14 baseline scenarios defined for each skill's core behaviors
- RED-GREEN-REFACTOR methodology
- Rationalization tracking
- See `tests/README.md` for complete testing guide

**Script tests** (migration scanner and progen helper, stdlib only, no network or Docker):
```bash
python3 -m unittest discover -s tests/scripts -v
```

> **Current coverage:** the harness is set up for all 14 scenarios, but only Scenario 7 (`code-reviewer` review rigor) and Scenarios 10–14 (scored with PIT, planted bugs and query counts) have been executed and recorded in `tests/baseline-results/`. Scenarios 1–6, 8 and 9 are defined in `tests/baseline-scenarios.md` and ready to run, but no baseline/target results exist for them yet. Contributions welcome.

Based on [terraform-skill testing approach](https://github.com/antonbabenko/terraform-skill/blob/master/tests/baseline-scenarios.md).

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

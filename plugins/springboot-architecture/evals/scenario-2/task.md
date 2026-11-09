# Same rules for every developer's coding agent

## Background

The billing team at Larkspur Utilities has five developers. Some use Claude Code, some use Codex. Each agent works differently: one formats code, another doesn't, one runs the tests before saying it's done, another never does. The team lead wants every agent on this repository to follow the same rules, and wants the build to catch the mistakes agents make before code merges.

The repository is in `inputs/`: a Maven Spring Boot 4 service with packages `controller`, `service`, `repository` and `domain` under `com.example.billing`. Copy it to `billing/` in your working directory and make the changes there.

The sandbox has no network access for Maven, so don't try to run the Maven build.

## What to produce

1. The changed repository in `billing/`.
2. `setup-report.md` in your working directory, covering: what you added or changed and why, the commands you ran, what the team must still do before the build is green and how to handle code that already breaks the new rules, and the next steps.

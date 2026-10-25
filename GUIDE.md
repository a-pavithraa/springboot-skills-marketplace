# Skills guide

One page for developers: how to install the skills, what each one does, and what to type. Most of them start on their own when your request matches; the table says which ones you have to call by name.

## Install once

```bash
git clone https://github.com/a-pavithraa/springboot-skills-marketplace.git
cd springboot-skills-marketplace
python3 install.py --with extras            # Claude Code
python3 install.py --with extras --codex    # Codex, if you use it
```

Then restart Claude Code. The script installs the plugins at user scope, so they work in every project, and turns on auto-update for this marketplace. When the marketplace moves to a newer version of a skill, you get it without doing anything. Without `--with extras` you get only the Spring Boot skills, and the grilling, planning, TDD and debugging rows below won't work. Run `python3 install.py --list` to see every plugin, and add `--with extras,pstack` for pstack.

A repository that has the team harness enables `springboot-architecture` in its `.claude/settings.json`, so a teammate who skipped this step still gets the Spring Boot skills there once they trust the folder. The other plugins need this script.

## What to use when

| When you want to | Type, or just ask | Skill |
| --- | --- | --- |
| Settle what to build before building it | "grill me on this plan" | `grilling` |
| Do the same, answering in a page of clickable options | "grill me in a page" | `grill-page` |
| Get a plan you can review and answer in the browser | `/html-plan <what to build>` | `html-plan` |
| Check a design idea with throwaway code | "prototype this" | `prototype` |
| Start a Spring Boot service | "create a Spring Boot service for orders" | `creating-springboot-projects` |
| Upgrade to Spring Boot 4 and Java 25 | "migrate this project to Boot 4" | `springboot-migration` |
| Build test-first | "do this with TDD" | `tdd` |
| Write or fix Spring Boot tests | "add tests for the payment client" | `writing-springboot-tests` |
| Check who may call each route | "add tests for who may call the order endpoints" | `writing-springboot-tests` |
| Find the cause of a bug | "debug this", "this test fails" | `diagnosing-bugs` |
| Review a change before the PR | "review this branch" | `code-reviewer` |
| Write the PR description | "write the PR" | `pr` |
| Record a decision or name domain terms | "write an ADR", "update the glossary" | `domain-modeling` |
| Hand a long session to a fresh one | `/handoff` | `handoff` |
| Edit `AGENTS.md`, `CLAUDE.md` or a skill | "improve AGENTS.md" | `writing-for-agents` |
| Add the build gates and hooks to a repository | "apply the team harness" | `spring-boot-team-harness` |

For tests in a Spring Boot service, name `writing-springboot-tests`, even when you work test-first with `tdd`. `tdd` also starts on "integration tests", but it doesn't have the Boot 4 wiring or the WireMock and Testcontainers templates.

Access tests sign in as a named user through your app's own role mapping, so they fail when that mapping breaks. They also fail when a route has no access decision. To use them, expose the role mapper, the `JwtAuthenticationConverter` or the `UserDetailsService` as a bean.

Codex also picks skills by their description, but that hasn't been trialled here. To make sure a skill loads, name it: `$tdd add the discount rule`.

## A feature, end to end

1. **Agree the change.** For anything bigger than one sentence, ask to be grilled, or ask for an `/html-plan`. Answer the questions; that's where most wrong turns get caught.
2. **Build it.** For a bug, ask for a failing test first. In a repository with the team harness, a hook checks the code when each turn ends and sends back any failure in the files the agent changed.
3. **Review it.** Ask for a review of the branch, and fix what it finds.
4. **Open the PR.** Ask for the PR description.

## Optional: pstack

`python3 install.py --with pstack` adds Lauren Tan's pstack. Most of its skills run only when you type them, such as `/technical-writing`, `/unslop`, `/blast-radius` and `/correct`. It works in Claude Code only.

## Optional: share usage data during a pilot

When a team tries the harness, real numbers settle what trials can only suggest: which skills people use, how often the Stop hook blocks and how long it takes, how many commits and pull requests the agent makes, and what a session costs. Claude Code can send these as OpenTelemetry metrics and events. A repository can't turn this on, so each developer who agrees adds it to their own `~/.claude/settings.json`, using the endpoint and key the team lead shares:

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "<endpoint from the team lead>",
    "OTEL_EXPORTER_OTLP_HEADERS": "<header from the team lead>",
    "OTEL_RESOURCE_ATTRIBUTES": "team.id=<team name>",
    "OTEL_LOG_TOOL_DETAILS": "1"
  }
}
```

If `env` already exists, add these keys to it. Restart Claude Code. To stop, delete the keys and restart.

What this sends:
- counts of sessions, tokens, cost, lines changed, commits and pull requests;
- each tool call's name and, with `OTEL_LOG_TOOL_DETAILS`, which skill or MCP tool ran and each Bash command in full;
- for each hook run, how long it took and whether it blocked;
- your account ID and email, which Claude Code attaches to every record.

It doesn't send your prompts, Claude's answers or file contents. Keep it that way: leave out `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_TOOL_CONTENT` and `OTEL_LOG_RAW_API_BODIES`, above all on client code. Bash commands can still name files, classes and branches, so send the data only to an account the team controls. The full list of signals is in [Monitoring](https://code.claude.com/docs/en/monitoring-usage).

## Where the skills come from

The Spring Boot skills are maintained in this repository. The others come from their authors' repositories, pinned to a reviewed commit and unchanged: [Matt Pocock's skills](https://github.com/mattpocock/skills), [html-plan](https://github.com/anthropics/claude-plugins-community/tree/main/html-plan) by Thariq Shihipar, [build-compass](https://github.com/a-pavithraa/build-compass) for `grill-page`, and [pstack](https://github.com/cursor/plugins/tree/main/harness/pstack) by Lauren Tan. Report problems with those skills to their authors.

# Scenario 27: telemetry.py against planted server failures

**Date:** 2026-10-31. **Model:** Sonnet. **Total cost:** $0.81. Each session was capped at $0.40.

**Result: no gain.** Every session in both arms caught all 3 bugs with no false alarms. `telemetry.py` cost about $0.02 more per session, and took 2 more turns in the first two rounds.

| Round | Arm | Runs | Caught | False alarms | Turns | Cost each |
| --- | --- | --- | --- | --- | --- | --- |
| 1: bugs in source, task names the log | baseline | 1 | 3/3 | 0 | 3 | $0.09 |
| | telemetry | 1 | 3/3 | 0 | 5 | $0.10 |
| 2: bugs in source, log not named | baseline | 2 | 3/3, 3/3 | 0 | 3 | $0.06 |
| | telemetry | 2 | 3/3, 3/3 | 0 | 5 | $0.09 |
| 3: failures only at runtime, log not named | baseline | 2 | 3/3, 3/3 | 0 | 5 | $0.07 |
| | telemetry | 2 | 3/3, 3/3 | 0 | 5 | $0.09 |

Rounds 1 and 2 used a fixture whose bugs could be read in the source, so they couldn't separate the arms. Round 3 is the committed fixture: the code looks clean, and all 3 dependencies are unreachable.

In round 3, both baseline sessions found `logs/console.log` without being told, and read the failures from it.

## What this doesn't show

- **The baseline had the verify profile too.** It ran with one line per request and context propagation, and its console log sat in the working folder. So this tests the CLI, not the profile. Having a log the agent can reach may be what matters, and this trial can't separate that.
- **The app was tiny and its log was quiet.** Nearly every line was a planted failure. Trace-scoped reads should matter more in a noisy log with concurrent traffic, but that wasn't tested.
- **Too few runs for small effects.** Four runs per arm on three fixtures would only show a large gap.
- **The task asked for verification directly.** It says nothing about agents who don't look.

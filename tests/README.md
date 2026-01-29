# Spring Boot Skills Testing

RED-GREEN-REFACTOR testing for Spring Boot architecture skills.

## Purpose

Validate that skills effectively change agent behavior through systematic baseline testing. This follows TDD principles applied to process documentation.

## Test Structure

### 1. Baseline Scenarios (`baseline-scenarios.md`)

8 comprehensive scenarios testing each skill's core behaviors:

| Scenario | Skill | Focus Area |
|----------|-------|-----------|
| 1 | creating-springboot-projects | Architecture assessment before implementation |
| 2 | spring-data-jpa | Repository anti-patterns (aggregate roots) |
| 3 | spring-data-jpa | N+1 query detection and prevention |
| 4 | creating-springboot-projects | Version enforcement (Java 25 + Spring Boot 4) |
| 5 | springboot-migration | Migration phase discipline (scan first) |
| 6 | spring-data-jpa | CQRS vs simple repository decision |
| 7 | code-reviewer | Multi-dimensional review rigor |
| 8 | spring-data-jpa | DTO projection vs entity fetching |

### 2. Rationalization Tracking (`rationalizations.md`)

Documents agent excuses/workarounds and how skills counter them:
- Baseline rationalizations (what agents say without skills)
- Skill counters (how skills prevent rationalizations)
- Status tracking (pending/fails/passes/updated)

### 3. Baseline Results (`baseline-results/`)

Verbatim agent responses for each scenario without skills loaded.

## Running Tests

### Phase 1: RED (Baseline)

**Goal:** Establish what goes wrong without skills

For each scenario in `baseline-scenarios.md`:

1. **Start fresh session** (clear context)
   ```bash
   # New Claude session, no skills loaded
   ```

2. **Run test prompt exactly**
   ```
   Copy prompt from scenario → paste in Claude
   ```

3. **Save response verbatim**
   ```bash
   # Save to baseline-results/scenario-N.md
   echo "## Scenario N: [Title]

   ### Test Prompt
   [paste prompt]

   ### Agent Response (No Skill)
   [paste full response]

   ### Observed Rationalizations
   - "[quote rationalization 1]"
   - "[quote rationalization 2]"
   ...

   ### Success Criteria Check
   - [ ] Criterion 1
   - [ ] Criterion 2
   ..." > baseline-results/scenario-N.md
   ```

4. **Extract rationalizations**
   - Quote exact phrases agent uses
   - Add to `rationalizations.md`

5. **Check success criteria**
   - Mark which criteria failed
   - Document specific failures

### Phase 2: GREEN (Target)

**Goal:** Verify skills fix the problems

For each scenario:

1. **Start fresh session**
   ```bash
   # New Claude session WITH skill loaded
   ```

2. **Load relevant skill**

   **Claude Code:**
   ```
   "Use the [skill-name] skill for this task"
   ```

   **Codex:**
   ```
   using $[skill-name] [prompt]
   ```

3. **Run same test prompt**
   ```
   Copy same prompt from scenario → paste in Claude
   ```

4. **Check success criteria**
   ```
   Go through each [ ] criterion
   Mark ✅ if passes, ❌ if fails
   ```

5. **Document results**
   ```bash
   # Add to baseline-results/scenario-N.md
   echo "
   ### Agent Response (With Skill)
   [paste full response]

   ### Success Criteria Results
   - [✅/❌] Criterion 1
   - [✅/❌] Criterion 2
   ...

   ### Notes
   [any observations]
   " >> baseline-results/scenario-N.md
   ```

6. **Update rationalizations.md**
   - Mark counters as ✅ Passes or ❌ Fails

### Phase 3: REFACTOR (Pressure Testing)

**Goal:** Make skills bulletproof

For scenarios that passed:

1. **Run pressure variations**
   ```
   Each scenario has 3-4 pressure variations
   Test with skill loaded
   ```

2. **Document new rationalizations**
   ```
   Agent finds loopholes? → Add to rationalizations.md
   ```

3. **Update skill**
   ```
   Add explicit counters for new rationalizations
   Update relevant sections
   ```

4. **Re-test**
   ```
   Run scenario + pressure variations again
   Verify new counters work
   ```

5. **Iterate**
   ```
   Repeat until all pressure variations pass
   Mark as ✅ Passes in rationalizations.md
   ```

## Expected Results

### Baseline (RED) Phase

Agent WITHOUT skills should:
- Jump to implementation without assessment
- Create repositories for all entities
- Miss N+1 query issues
- Accept outdated versions
- Skip migration scanning
- Add query methods to repositories
- Give surface-level reviews
- Fetch full entities for read-only queries

### Target (GREEN) Phase

Agent WITH skills should:
- Assess complexity before suggesting architecture
- Create repositories only for aggregate roots
- Immediately identify N+1 issues with solutions
- Enforce Java 25 + Spring Boot 4
- Require project scan before migration
- Recommend CQRS query service
- Perform multi-dimensional reviews
- Suggest DTO projections for read queries

### Success Metrics

Skills are effective when:
- ✅ All 8 baseline scenarios show behavior gaps
- ✅ All 8 target scenarios pass success criteria
- ✅ Pressure variations don't break compliance
- ✅ Rationalizations are systematically countered

## File Structure

```
tests/
├── README.md                    # This file
├── baseline-scenarios.md        # 8 test scenarios
├── rationalizations.md          # Rationalization tracking
└── baseline-results/           # Test results
    ├── scenario-1.md           # Architecture assessment
    ├── scenario-2.md           # Repository anti-patterns
    ├── scenario-3.md           # N+1 detection
    ├── scenario-4.md           # Version enforcement
    ├── scenario-5.md           # Migration discipline
    ├── scenario-6.md           # CQRS decision
    ├── scenario-7.md           # Review rigor
    └── scenario-8.md           # DTO projections
```

## Templates

### Baseline Result Template

```markdown
## Scenario N: [Title]

**Date:** YYYY-MM-DD
**Claude Version:** [version]
**Skill Loaded:** None

### Test Prompt

[Exact prompt from baseline-scenarios.md]

### Agent Response (No Skill)

[Full verbatim response]

### Observed Rationalizations

- "[Exact quote 1]"
- "[Exact quote 2]"
- "[Exact quote 3]"

### Success Criteria Check

- [ ] Criterion 1: [Pass/Fail reason]
- [ ] Criterion 2: [Pass/Fail reason]
...

### Notes

[Any additional observations]
```

### Target Result Addition

```markdown
---

**Date:** YYYY-MM-DD
**Claude Version:** [version]
**Skill Loaded:** [skill-name]

### Agent Response (With Skill)

[Full verbatim response]

### Success Criteria Results

- [✅/❌] Criterion 1: [Pass/Fail reason]
- [✅/❌] Criterion 2: [Pass/Fail reason]
...

### Comparison

**Baseline:** [What went wrong]
**With Skill:** [What improved]
**Remaining Issues:** [If any]

### Notes

[Any additional observations]
```

## Running Full Test Suite

```bash
# 1. Baseline phase (RED)
# Run each scenario 1-8 without skills
# Save to baseline-results/scenario-N.md

# 2. Update rationalizations
# Extract quotes from baseline results
# Add to rationalizations.md

# 3. Target phase (GREEN)
# Run each scenario 1-8 with appropriate skill
# Add results to same baseline-results/scenario-N.md

# 4. Pressure testing (REFACTOR)
# For passing scenarios, run pressure variations
# Document new rationalizations
# Update skills
# Re-test

# 5. Summary
# Update rationalizations.md summary statistics
# Document which scenarios pass/fail
# Identify skill improvements needed
```

## Test Maintenance

### When to Re-run Tests

- After skill content updates
- After adding new skill sections
- When new Claude versions release
- After discovering new failure modes in production

### Updating Scenarios

- Add new scenarios for newly discovered issues
- Update pressure variations as agents get smarter
- Adjust success criteria if baseline behavior improves

### Version Tracking

Document in each test result:
- Date of test
- Claude version used
- Skill version/commit hash
- Any relevant environment details

## Contributing Test Results

If you run these tests, please contribute results:

1. Fork repository
2. Run tests and document results in `baseline-results/`
3. Update `rationalizations.md` with findings
4. Create PR with:
   - Test results
   - Claude version used
   - Any skill improvements needed
   - Summary of findings

## References

- **TDD for Skills:** See `skills/writing-skills/SKILL.md`
- **Original Approach:** Based on [antonbabenko/terraform-skill tests](https://github.com/antonbabenko/terraform-skill/blob/master/tests/baseline-scenarios.md)
- **Skill Testing Methodology:** See writing-skills skill for complete testing framework

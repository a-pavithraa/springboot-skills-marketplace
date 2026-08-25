# Quick Start: Testing Spring Boot Skills

Run baseline tests to validate skill effectiveness in about 35 minutes.

## Prerequisites

- Claude Code or Codex installed
- Spring Boot skills installed (see main README.md)
- Fresh terminal/session for each test

## 5-Minute Single Test

Run one scenario to understand the process:

### Step 1: Baseline (No Skill) - 2 minutes

1. **Start fresh Claude session**
   ```bash
   # New terminal, new Claude session
   # DO NOT load any skills
   ```

2. **Copy Scenario 1 prompt** from `baseline-scenarios.md`:
   ```
   I need to create a Spring Boot application for managing orders
   with payment processing and inventory tracking. Can you help me set this up?
   ```

3. **Paste into Claude and send**

4. **Save response**
   - Copy full response
   - Save to `baseline-results/scenario-1.md` using TEMPLATE.md format
   - Note any rationalizations (quotes like "standard layered architecture works")

### Step 2: Target (With Skill) - 2 minutes

1. **Start NEW fresh Claude session**
   ```bash
   # Close previous session, start new
   ```

2. **Load creating-springboot-projects skill**

   **Claude Code:**
   ```
   Use the creating-springboot-projects skill to help with this
   ```

   **Codex:**
   ```
   using $creating-springboot-projects I need to create a Spring Boot application
   for managing orders with payment processing and inventory tracking.
   Can you help me set this up?
   ```

3. **Observe behavior change**
   - Does it ask 5 assessment questions?
   - Does it recommend Tomato/DDD instead of layered?
   - Does it reference architecture-guide.md?

4. **Save response**
   - Add to same `baseline-results/scenario-1.md`
   - Check success criteria
   - Mark ✅/❌ for each criterion

### Step 3: Compare - 1 minute

**Expected difference:**

| Without Skill | With Skill |
|---------------|------------|
| Jumps to implementation | Asks 5 questions first |
| Suggests layered architecture | Suggests Tomato/DDD for complex domain |
| Generic advice | References architecture-guide.md |
| No assessment | Assessment-driven recommendation |

## 35-Minute Full Test Run

### Phase 1: Baseline All Scenarios (15 minutes)

Run each scenario WITHOUT skill:

```bash
# Scenario 1 - Architecture Assessment
# [Start fresh session, paste prompt, save response]

# Scenario 2 - Repository Anti-Patterns
# [Start fresh session, paste prompt, save response]

# Scenario 3 - N+1 Detection
# [Start fresh session, paste prompt, save response]

# ... continue through Scenario 8
```

**Tip:** Focus on capturing:
- Exact agent responses
- Rationalization quotes
- What went wrong

### Phase 2: Target All Scenarios (15 minutes)

Run each scenario WITH skill:

```bash
# Scenario 1 - WITH creating-springboot-projects
# [Start fresh session, load skill, paste prompt, check criteria]

# Scenario 2 - WITH spring-data-jpa
# [Start fresh session, load skill, paste prompt, check criteria]

# Scenario 3 - WITH spring-data-jpa
# [Start fresh session, load skill, paste prompt, check criteria]

# ... continue through Scenario 8
```

**Tip:** Focus on:
- Which criteria pass ✅
- Which criteria fail ❌
- Behavior changes from baseline

### Phase 3: Quick Summary (5 minutes)

Update `rationalizations.md`:

```markdown
## Summary Statistics

**Total Scenarios:** 8
**Scenarios Passed:** X/8
**Total Rationalizations Found:** X
**Counters Effective:** X/Y
**Skill Updates Needed:** [List]
```

## Interpretation Guide

### Good Result (Skill Working)

```
Baseline (No Skill):
"I'll create a layered architecture with repositories for
Order, OrderItem, Payment, Customer, Address, Product..."

Target (With Skill):
"Before suggesting architecture, let me ask about your requirements:
1. Domain Complexity - is this simple CRUD or complex business rules?
2. Team Size - how many developers?
..."
```

**✅ Clear behavior change. Skill is effective.**

### Bad Result (Skill Not Working)

```
Baseline (No Skill):
"I'll create a layered architecture..."

Target (With Skill):
"I'll create a layered architecture for your order management system..."

```

**❌ No behavior change. Skill needs improvement.**

### Partial Result (Skill Partially Working)

```
Baseline (No Skill):
"I'll create repositories for all entities..."

Target (With Skill):
"I'll create repositories for the main entities. Note that
you should consider aggregate roots..."
```

**🔄 Mentions concept but doesn't enforce it. Skill needs stronger counters.**

## Common Issues

### Issue: Agent ignores skill

**Solution:**
- Verify skill is properly installed
- Try explicit invocation: "Use the [skill-name] skill"
- Check skill description triggers match your prompt

### Issue: Can't see behavior change

**Solution:**
- Make sure you started fresh session (clear context)
- Verify skill actually loaded (Claude Code shows in UI, Codex requires $)
- Compare success criteria one-by-one, don't rely on general impression

### Issue: Agent finds loopholes

**Solution:**
- This is expected! Document the rationalization
- This is exactly what pressure testing finds
- Add explicit counter to skill
- Re-test

## Quick Cheat Sheet

### Running Baseline Test

```
✅ Start fresh Claude session (no skills)
✅ Copy prompt from baseline-scenarios.md
✅ Paste and send
✅ Save full response to baseline-results/scenario-N.md
✅ Extract rationalization quotes
❌ Don't load any skills
❌ Don't paraphrase the prompt
```

### Running Target Test

```
✅ Start NEW fresh Claude session
✅ Load appropriate skill first
✅ Run same prompt as baseline
✅ Check each success criterion
✅ Compare with baseline behavior
✅ Document what changed
❌ Don't reuse same session
❌ Don't modify the prompt
```

### Documenting Results

```
✅ Use TEMPLATE.md structure
✅ Include exact quotes for rationalizations
✅ Mark each criterion ✅/❌ with evidence
✅ Save both baseline and target in same file
✅ Update rationalizations.md
❌ Don't summarize responses, paste verbatim
❌ Don't skip criteria checks
```

## Next Steps

After running quick test:

1. **If scenario passed:** Run pressure variations
2. **If scenario failed:** Document which criteria failed
3. **Update rationalizations.md:** Add quotes and status
4. **Update skill if needed:** Add counters for failures
5. **Re-test:** Verify improvements

## Full Testing Workflow

```
┌─────────────────────────────────────┐
│ 1. Run Scenario WITHOUT Skill (RED) │
│    - Start fresh session            │
│    - Paste prompt                   │
│    - Save response                  │
│    - Extract rationalizations       │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 2. Run Scenario WITH Skill (GREEN)  │
│    - Start fresh session            │
│    - Load skill                     │
│    - Same prompt                    │
│    - Check criteria                 │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 3. Compare & Document               │
│    - What changed?                  │
│    - Which criteria passed?         │
│    - Update rationalizations.md     │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ 4. Pressure Test (REFACTOR)         │
│    - Run variations                 │
│    - Find loopholes                 │
│    - Update skill                   │
│    - Re-test                        │
└─────────────────────────────────────┘
```

## Time Estimates

| Activity | Time | Cumulative |
|----------|------|------------|
| Single scenario baseline | 2 min | 2 min |
| Single scenario target | 2 min | 4 min |
| Documentation | 1 min | 5 min |
| **One complete scenario** | **5 min** | **5 min** |
| All 8 baselines | 15 min | 15 min |
| All 8 targets | 15 min | 30 min |
| Update rationalizations | 5 min | 35 min |
| **Full baseline run** | **35 min** | **35 min** |
| Pressure testing (per scenario) | 5 min | varies |
| Skill updates (if needed) | varies | varies |

## Questions?

See `README.md` for detailed testing methodology or `baseline-scenarios.md` for scenario details.

# Scenario N: [Title]

**Date:** YYYY-MM-DD
**Claude Version:** [e.g., claude-sonnet-4-5-20250929]
**Skill Loaded:** None (Baseline) / [skill-name] (Target)

---

## Baseline Test (RED Phase)

### Test Prompt

```
[Paste exact prompt from baseline-scenarios.md]
```

### Agent Response (No Skill)

```
[Paste full verbatim response from Claude without skill loaded]
```

### Observed Rationalizations

Document exact quotes that represent rationalizations/excuses:

- "[Exact quote 1]"
- "[Exact quote 2]"
- "[Exact quote 3]"
- "[Exact quote 4]"

### Success Criteria Check

From baseline-scenarios.md for this scenario:

- [ ] **Criterion 1:** [Description]
  - **Result:** FAIL
  - **Evidence:** [What agent did wrong]

- [ ] **Criterion 2:** [Description]
  - **Result:** FAIL
  - **Evidence:** [What agent did wrong]

- [ ] **Criterion 3:** [Description]
  - **Result:** FAIL
  - **Evidence:** [What agent did wrong]

### Baseline Summary

**What Went Wrong:**
- [Key issue 1]
- [Key issue 2]
- [Key issue 3]

**Why This Matters:**
[Explain impact of these failures]

---

## Target Test (GREEN Phase)

**Date:** YYYY-MM-DD
**Skill Loaded:** [skill-name]

### Agent Response (With Skill)

```
[Paste full verbatim response from Claude WITH skill loaded]
```

### Success Criteria Results

From baseline-scenarios.md for this scenario:

- [✅/❌] **Criterion 1:** [Description]
  - **Result:** PASS/FAIL
  - **Evidence:** [What agent did correctly/incorrectly]

- [✅/❌] **Criterion 2:** [Description]
  - **Result:** PASS/FAIL
  - **Evidence:** [What agent did correctly/incorrectly]

- [✅/❌] **Criterion 3:** [Description]
  - **Result:** PASS/FAIL
  - **Evidence:** [What agent did correctly/incorrectly]

### Target Summary

**What Improved:**
- [Improvement 1]
- [Improvement 2]
- [Improvement 3]

**Remaining Issues (if any):**
- [Issue 1]
- [Issue 2]

---

## Pressure Testing (REFACTOR Phase)

### Pressure Variation 1: "[Prompt]"

**Agent Response:**
```
[Response with skill loaded]
```

**Result:** ✅ PASS / ❌ FAIL

**New Rationalizations Found:**
- "[Quote if agent found loophole]"

---

### Pressure Variation 2: "[Prompt]"

**Agent Response:**
```
[Response with skill loaded]
```

**Result:** ✅ PASS / ❌ FAIL

**New Rationalizations Found:**
- "[Quote if agent found loophole]"

---

### Pressure Variation 3: "[Prompt]"

**Agent Response:**
```
[Response with skill loaded]
```

**Result:** ✅ PASS / ❌ FAIL

**New Rationalizations Found:**
- "[Quote if agent found loophole]"

---

## Comparison Analysis

### Baseline vs Target

| Aspect | Baseline (No Skill) | Target (With Skill) | Change |
|--------|---------------------|---------------------|--------|
| Behavior 1 | [What happened] | [What happened] | [Improvement] |
| Behavior 2 | [What happened] | [What happened] | [Improvement] |
| Behavior 3 | [What happened] | [What happened] | [Improvement] |

### Skill Effectiveness

**Score:** X/Y criteria passed

**Overall:** ✅ EFFECTIVE / ❌ NEEDS IMPROVEMENT / 🔄 PARTIALLY EFFECTIVE

**Recommendation:**
[What needs to be updated in the skill, if anything]

---

## Notes

### Additional Observations

[Any other observations during testing]

### Environment Details

- **OS:** [Windows/Mac/Linux]
- **Claude Code Version:** [version if applicable]
- **Codex Version:** [version if applicable]
- **Skill Version:** [commit hash or version]

### Follow-up Actions

- [ ] Add rationalizations to rationalizations.md
- [ ] Update skill if criteria failed
- [ ] Re-test after skill update
- [ ] Run pressure variations
- [ ] Document in summary report

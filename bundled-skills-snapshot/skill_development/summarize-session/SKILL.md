---
name: summarize-session-into-skill
description: "Capture current session as reusable skill. Use when: user wants to turn completed work into repeatable workflow. Triggers: summarize session, capture workflow, turn into skill."
---

# Summarize Session into Skill

Transform current conversation into a reusable, parameterized skill.

## Workflow

### Step 1: Analyze Session

Review conversation to identify:
- Problem solved
- Steps taken
- Tools used
- Decisions made

Present summary:
```
**Problem:** [description]
**Steps:** 1. [step] 2. [step]
**Tools:** [list]
**Files:** [modified]

Is this accurate?
```

**⚠️ STOP**: Confirm summary.

### Step 2: Extract Pattern

1. Identify which steps are always needed vs conditional
2. Abstract specific values into parameters:

| Session Value | Parameter |
|--------------|-----------|
| `MY_DATABASE` | `<DATABASE>` |
| `file.yaml` | `<INPUT_FILE>` |

3. Present pattern for approval

**⚠️ STOP**: Approve pattern.

### Step 3: Define Parameters

```
Required: <PARAM_1>, <PARAM_2>
Optional: <OPT_1> (default: X)
```

### Step 4: Get Metadata

Ask:
1. **Name**: Suggest based on workflow
2. **Triggers**: Suggest based on session
3. **Location**: `.cortex/skills/<name>/` (project) or `$HOME/.snowflake/cortex/skills/<name>/` (or `$SNOWFLAKE_HOME/cortex/skills/<name>/` if `$SNOWFLAKE_HOME` is set) (global)

### Step 5: Generate Skill

Write SKILL.md with:
- Frontmatter (name + description with triggers)
- Parameter collection step
- Workflow steps from pattern
- Stopping points
- Output description

### Step 6: Write and Present

```
✅ Skill created: <path>/SKILL.md
Triggers: [phrases]
Parameters: [list]
```

**⚠️ STOP**: Final review.

## Common Patterns

| Pattern | Steps |
|---------|-------|
| Debug | Reproduce → Diagnose → Fix → Validate |
| Create | Requirements → Configure → Create → Verify |
| Optimize | Analyze → Identify → Apply → Measure |

## Stopping Points

- ✋ Step 1: Summary validated
- ✋ Step 2: Pattern approved
- ✋ Step 6: Final review

## Output

SKILL.md capturing session workflow, parameterized for reuse.

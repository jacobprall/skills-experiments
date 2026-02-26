---
name: create-skill-from-scratch
description: "Create new skills from scratch. Use when user wants to build a new skill with proper structure."
---

# Create Skill from Scratch

## Workflow

### Step 1: Gather Requirements

Ask user:
```
To create your skill:
1. **Name** (kebab-case): e.g., "optimize-database"
2. **Purpose**: What problem does it solve?
3. **Triggers**: Words that should activate it
4. **Tools/Scripts**: Any scripts or APIs?
```

**⚠️ STOP**: Confirm requirements before proceeding.

### Step 2: Design Structure

Determine if single-file or needs splitting:
- **Single file**: Linear workflow, <500 lines
- **With references/**: Detailed docs needed on-demand
- **With sub-skills**: Distinct workflow branches

Present structure for approval.

**⚠️ STOP**: Get approval on structure.

### Step 3: Choose Location

Options:
1. `.cortex/skills/<name>/` - Project-local (only available in this project)
2. `$HOME/.snowflake/cortex/skills/<name>/` (or `$SNOWFLAKE_HOME/cortex/skills/<name>/` if `$SNOWFLAKE_HOME` is set) - Global (available across all projects)

Create directory: `mkdir -p <path>/<skill-name>`

### Step 4: Write SKILL.md

**Frontmatter:**
```yaml
---
name: skill-name
description: "Purpose. Use when: [scenarios]. Triggers: keyword1, keyword2."
---
```

**Body:**
```markdown
# Title

## Workflow
### Step 1: [Name]
[Actions]
**⚠️ STOP**: [Checkpoint]

## Stopping Points
- ✋ After Step X

## Output
[What skill produces]
```

### Step 5: Add Tools (if needed)

```markdown
## Tools
### script.py
**Usage:** `uv run --project <DIR> python <DIR>/scripts/script.py [args]`
```

### Step 6: Write and Present

1. Write SKILL.md
2. Verify < 500 lines
3. Present result with triggers

**⚠️ STOP**: Final review.

## Stopping Points

- ✋ Step 1: Requirements confirmed
- ✋ Step 2: Structure approved  
- ✋ Step 6: Final review

## Output

Complete SKILL.md at specified location.

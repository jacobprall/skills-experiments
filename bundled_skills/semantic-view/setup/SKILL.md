---
name: semantic-view-setup
description: Initial setup for all semantic view workflows. Creates session directory structure and routes to appropriate workflow (creation or optimization).
required_for: All workflows
---

# Setup

## ⚠️ STOP - Prerequisites Check (BLOCKING)

**Before reading ANY of this skill, you MUST have loaded:**

1. ✋ **[reference/semantic_view_concepts.md](../reference/semantic_view_concepts.md)**

   - **Verify**: Can you explain the difference between logical vs physical table/column names? (If no, load it now)
   - **Verify**: Which semantic model elements can be added vs enhanced only? (If no, load it now)

2. ✋ **[reference/semantic_view_get.md](../reference/semantic_view_get.md)**
   - **Verify**: What are the required parameters for semantic_view_get.py? (If you don't know, load it now)
   - **Verify**: What does the `--component` parameter accept? (If you don't know, load it now)

**❌ If you have NOT loaded both files above, STOP and load them NOW.**

**✅ If you HAVE loaded both, state: "Prerequisites verified - proceeding with setup" and continue below.**

---

## When to Load

**ALWAYS** load this file as Step 2 from main SKILL.md, regardless of workflow type (creation or optimization).

This setup is the common initialization for ALL semantic view workflows.

## Purpose

This setup will:
1. Capture skill base directory (where scripts are located)
2. Get working directory from user (where to create files)
3. Create session directory with timestamp
4. Route to appropriate workflow (creation or optimization)

## Process

### Part 1: Directory Initialization

#### 1.1: Determine Skill Base Directory

**When the skill loads**, Cortex Code provides the skill base directory. Capture this information:

- Look for: "Base directory for this skill: /path/to/skill" in the skill launch message
- Store as: `SKILL_BASE_DIR` variable

**If base directory is not explicitly provided:**
- Use current working directory when skill was invoked

**Example:**
```
Skill launched with base: /custom-skills/semantic-view-optimization
SKILL_BASE_DIR = /custom-skills/semantic-view-optimization
Scripts located at: {SKILL_BASE_DIR}/scripts/
```

#### 1.2: Get Working Directory

Ask user for working directory where files will be created, or infer from their message:

**Question**: "Where would you like to create the semantic view files? (Press Enter to use the default: $SKILL_BASE_DIR)"

**Inference**: If user's message contains path references like "in /app", "at /workspace", extract and use that path.

**Default**: If user doesn't specify or presses Enter, use `SKILL_BASE_DIR`

**User can provide:**
- Absolute path: `/app`, `/workspace`, `/tmp/semantic_views`, `/home/user/projects`
- Relative path: Will be resolved relative to current directory
- Empty/Enter: Use `SKILL_BASE_DIR`

**Store as**: `BASE_WORKING_DIR` variable

**Example:**
```
User input: /app
BASE_WORKING_DIR = /app
```

#### 1.3: Create Session Directory

Create a timestamped directory for this session:

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p {BASE_WORKING_DIR}/semantic_view_{TIMESTAMP}
```

**Store as**: `WORKING_DIR = {BASE_WORKING_DIR}/semantic_view_{TIMESTAMP}`

**Why this is important:**
- Each session gets its own isolated directory
- Easy to identify files from specific sessions
- Prevents conflicts between multiple runs
- Consistent structure for both creation and optimization workflows

**Example:**
```
BASE_WORKING_DIR = /app
TIMESTAMP = 20260218_143022
WORKING_DIR = /app/semantic_view_20260218_143022
```

**Verify directory:**
```bash
ls -la {WORKING_DIR}
```

**⚠️ IMPORTANT**: All workflows will create subdirectories within `WORKING_DIR`:
- Creation: `{WORKING_DIR}/creation/`
- Optimization: `{WORKING_DIR}/optimization/`


### Part 2: Workflow Routing

#### 2.1: Determine Workflow Type

**Ask user or infer from context: Is this for a NEW semantic view or an EXISTING one?**

**Path A: CREATION (New Semantic View)**

If user wants to CREATE a new semantic view:
- **Action**: Load [creation/SKILL.md](../creation/SKILL.md)
- **Stop here** - do NOT proceed to Part 3

**Path B: OPTIMIZATION (Existing Semantic View)**

If user wants to OPTIMIZE an existing semantic view:
- **Continue to Part 3** below

### Part 3: Optimization Setup (ONLY for Path B)

**⚠️ ONLY execute this part if workflow type is OPTIMIZATION.**

**If you are on CREATION path, you should have already loaded creation/SKILL.md and stopped.**

#### 3.1: Semantic View Name

If the user already provided the semantic view name in the conversation (in any format: `DATABASE.SCHEMA.VIEW_NAME`, `database.schema.view_name`, or just `VIEW_NAME` with separate database/schema mentions), then move to step 3.2.

Otherwise, ask.

## Prerequisites

- Fully qualified semantic view name (DATABASE.SCHEMA.VIEW_NAME)
- Snowflake access configured
- Python environment (managed automatically via `uv`)

#### 3.2: Create Optimization Subdirectory

Create the subdirectory for optimization workflow:

```bash
mkdir -p {WORKING_DIR}/optimization
```

**Why this is important:**
- All optimization files will be saved to `{WORKING_DIR}/optimization/`
- `WORKING_DIR` is the timestamped session directory from Part 1,
- `optimization/` subdirectory keeps optimization files organized
- Use `{WORKING_DIR}/optimization/` consistently when referencing the directory and do not use global patterns like `*`.
- Consistent structure across all workflows

#### 3.3: Download Semantic Model

Use [download_semantic_view_yaml.py](../scripts/download_semantic_view_yaml.py) to download semantic model YAML to optimization directory.

```bash
cd {WORKING_DIR}/optimization && \
SNOWFLAKE_CONNECTION_NAME=<connection> uv run python {SKILL_BASE_DIR}/scripts/download_semantic_view_yaml.py <SEMANTIC_VIEW_NAME> .
```

**Note**: 
- Use `{SKILL_BASE_DIR}/scripts/` for script location (absolute path)
- Run from `{WORKING_DIR}/optimization/` so files are downloaded there

**Use semantic_view_get.py** (from prerequisites) to extract components as needed:

- Tables: `--component tables`
- Verified queries: `--component verified_queries`
- Custom instructions: `--component custom_instructions`
- Module custom instructions: `--component module_custom_instructions`
- Relationships: `--component relationships`

All commands require both `--file` and `--component` arguments.

Handle Python environment issues if they arise (clean environment approach available).

#### 3.4: Present Summary

Present ONLY this summary:

```
✅ Setup Complete
Directory: semantic_view_TIMESTAMP/
Semantic Model: X KB
VQRs: Y queries
Ready to proceed.
```

**🛑 MANDATORY STOP - DO NOT PROCEED FURTHER**

Present mode selection.

## Next Skills

- AUDIT MODE → [audit/SKILL.md](../audit/SKILL.md)
- DEBUG MODE → [debug/SKILL.md](../debug/SKILL.md)

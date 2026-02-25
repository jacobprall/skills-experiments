# Skill Schema

Detailed schema definitions for skill files. This document supplements `standard-skills-library.md` with the precise field-level schema for front-matter and the required sections for each skill type.

For principles, architecture, and execution model, see `standard-skills-library.md`.

## Skill DAG

Skills form a directed acyclic graph (DAG) with four layers and strict edge rules.

### Entry point

The agent always enters through the meta-router (`router.md` at repo root), which resolves user intent to one or more domain routers.

```
Meta-Router (router.md)
    │
    ├─→ Domain Router A
    ├─→ Domain Router B
    └─→ Domain Router C
```

### Routing graph (decision time)

Domain routers resolve user intent within their domain to a target skill.

```
Domain Router
  ├── broad intent  → Playbook (playbook mode)
  ├── moderate intent → Primitive (guided mode)
  └── narrow intent → Primitive (reference mode)
```

- The meta-router declares `domains` with `produces`/`requires` for chaining.
- Domain routers declare `routes_to` — the set of skills they can select.
- `routes_to` may include both primitives and playbooks.
- Nothing depends on a router. Routers are entry points only.

### Execution graph (execution time)

Once the agent has a playbook or guided plan, it follows the steps. Each step references one or more primitives.

```
Playbook / Guided Plan
  ├── Primitive A (step 1)
  ├── Primitive B (step 2)
  ├── Primitive C (step 3)
  └── Primitive B (sub-step 3b, if context requires)
```

- Playbooks declare `depends_on` — the primitives they compose.
- `depends_on` lists only primitives, never routers or other playbooks.
- Primitives are leaf nodes with no outgoing edges.
- The agent may add sub-steps referencing additional primitives when execution context requires it.

### Edge rules

| From | To | Field | Allowed? |
|------|----|-------|----------|
| Meta-Router | Domain Router | `domains[].router` | Yes |
| Meta-Router | Playbook/Primitive | — | **No** (always through domain router) |
| Domain Router | Primitive | `routes_to` | Yes |
| Domain Router | Playbook | `routes_to` | Yes |
| Domain Router | Domain Router | — | **No** |
| Playbook | Primitive | `depends_on` | Yes |
| Playbook | Router | — | **No** |
| Playbook | Playbook | — | **No** |
| Primitive | anything | — | **No** (leaf node) |

### Why no upward edges?

A playbook never references a router because the router was already consulted *before* the playbook was entered. The playbook is the resolved execution path — it should be self-contained. This prevents cycles and makes each layer independently testable.

## Front-matter Schema

### Common Fields (all types)

```yaml
---
type: primitive | router | playbook   # REQUIRED — skill layer
name: kebab-case-name                 # REQUIRED — unique identifier, must match directory name
domain: domain-name                   # REQUIRED — from controlled vocabulary
---
```

Versioning is at the library level (top of `skill-index.yaml`), not per-skill.

### Primitive

```yaml
---
type: primitive
name: dynamic-tables
domain: data-transformation
snowflake_docs: "https://docs.snowflake.com/en/user-guide/dynamic-tables"
tested_on:
  snowflake_version: "8.23"
  test_date: "2026-02-15"
  test_account_type: "enterprise"
last_reviewed: "2026-02-15"
---
```

No `depends_on` — primitives are leaf nodes. No `version` — library-level only.

**Staleness tracking fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `snowflake_docs` | Recommended | Link to official Snowflake documentation |
| `tested_on.snowflake_version` | Recommended | Snowflake version when last tested |
| `tested_on.test_date` | Recommended | Date of last functional test |
| `tested_on.test_account_type` | Recommended | Account edition used for testing |
| `last_reviewed` | Recommended | Date content was last reviewed for accuracy |

When `last_reviewed` exceeds `staleness_threshold_days` (configured in meta-router), the agent emits a `staleness_warning` event.

### Router

```yaml
---
type: router
name: data-security
domain: data-security
parameters:                            # REQUIRED — inputs needed to route
  - name: user_goal
    description: "What the user is trying to accomplish"
    options:
      - id: end-to-end-protection
        description: "Discover, protect, and monitor sensitive data — full workflow"
      - id: mask-columns
        description: "Hide or redact column values so unauthorized users can't see them"
routes_to:                             # REQUIRED — skills this router can select
  - primitives/data-classification
  - primitives/masking-policies
  - playbooks/secure-sensitive-data
---
```

No `depends_on` — routers are entry points, not dependencies.

### Playbook

```yaml
---
type: playbook
name: secure-sensitive-data
domain: data-security
depends_on:                            # REQUIRED — primitives this playbook composes
  - data-classification
  - masking-policies
  - row-access-policies
  - projection-policies
  - account-usage-views
inputs:                                # REQUIRED — context the agent needs
  - name: target_account
    required: false
    description: "Snowflake account to operate on (defaults to current)"
    phase: before_start
    type: account_locator
  - name: target_tables
    required: true
    description: "Tables to classify and protect"
    phase: before_start
  - name: protection_strategy
    required: true
    description: "Which columns need which type of protection"
    phase: step_2
probes:                                # REQUIRED — discovery queries before execution
  - id: account_verification
    query: "SELECT CURRENT_ACCOUNT(), CURRENT_ROLE()"
    required: true
    validate:
      - condition: "target_account IS NOT NULL AND account != target_account"
        action: block
        message: "Connected to wrong account. Expected {target_account}, got {account}."
  - id: existing_policies
    query: "SHOW MASKING POLICIES IN ACCOUNT"
    required: true
    validate:
      - condition: "count > 100"
        action: warn
        message: "Large number of existing policies — review before proceeding"
  - id: target_tables_exist
    query: "SELECT COUNT(*) FROM {target_scope}.INFORMATION_SCHEMA.TABLES"
    required: true
    validate:
      - condition: "count == 0"
        action: block
        message: "No tables found in target scope"
      - condition: "count > 500"
        action: confirm
        message: "Large scope ({count} tables) — this may take significant time"
  - id: role_check
    query: "SELECT CURRENT_ROLE()"
    required: true
    validate:
      - condition: "result NOT IN ('ACCOUNTADMIN', 'SECURITYADMIN')"
        action: block
        message: "Requires ACCOUNTADMIN or SECURITYADMIN role"
---
```

`depends_on` lists all primitives the playbook may reference, including those used in sub-steps. Never routers, never other playbooks.

`probes` are mandatory discovery queries that run before step 1. Each probe validates the environment and can block, warn, or require confirmation before proceeding.

**Input types:**

| Type | Description |
|------|-------------|
| `string` | Free-form text (default) |
| `account_locator` | Snowflake account identifier for multi-account targeting |
| `role` | Snowflake role name |
| `database`, `schema`, `table` | Snowflake object identifiers |

## Required Sections by Type

### Primitives

| Section | Required | Purpose |
|---------|----------|---------|
| `# {Name}` | Yes | Title, one-line description |
| `## Syntax` | Yes | SQL/CLI syntax with parameter descriptions |
| `## Parameters` | Yes | Parameter table: name, type, default, description |
| `## Constraints` | Yes | Limits, prerequisites, known edge cases |
| `## Examples` | Yes | Runnable SQL/code — basic and advanced |
| `## Anti-patterns` | No | Common mistakes and why they fail |

### Routers

| Section | Required | Purpose |
|---------|----------|---------|
| `# {Name}` | Yes | Title, one-line description of the decision space |
| `## Decision Criteria` | Yes | What inputs are needed to route |
| `## Routing Logic` | Yes | Decision matrix or flowchart — deterministic, not prose |
| `## Routes To` | Yes | Table of targets with selection conditions |
| `## Anti-patterns` | No | Common mis-routings and corrections |

### Playbooks

| Section | Required | Purpose |
|---------|----------|---------|
| `# {Name}` | Yes | Title, one-line description of the outcome |
| `## Objective` | Yes | What the user will have when done |
| `## Prerequisites` | Yes | What must exist before starting |
| `## Pre-execution Probes` | Yes | Discovery queries to run before step 1 |
| `## Steps` | Yes | Numbered steps referencing primitives |
| `## Anti-patterns` | No | Common workflow mistakes |

### Playbook step structure

Each step must:
1. State what it does in one line
2. Reference the primitive(s) it draws from (recommended, not mandatory for design/verification steps)
3. Include example SQL
4. Declare a **Compensation** action if the step creates or modifies objects
5. Declare **Creates** — objects this step produces (for rollback tracking)
6. Optionally define a **Checkpoint** with severity level
7. Optionally define **Expected errors** with recovery hints (overrides global categories)
8. Mark conditional steps explicitly ("This step is conditional")

Sub-steps (e.g., "3b") are allowed when execution context requires actions beyond the step's title.

## Context Gathering

Each skill declares what information the agent needs via structured fields. The agent gathers inputs lazily: infer from the user's message and session context first, ask only for what's missing, and prefer presenting choices over open-ended questions.

### Router `parameters`

Declare the inputs needed to make a routing decision. Each parameter has a set of options with human-readable descriptions.

```yaml
parameters:
  - name: user_goal
    description: "What the user is trying to accomplish"
    options:
      - id: end-to-end-protection
        description: "Discover, protect, and monitor sensitive data — full workflow"
      - id: mask-columns
        description: "Hide or redact column values so unauthorized users can't see them"
```

- Each option has an `id` (stable identifier for routing logic) and a `description` (human-readable, used when presenting choices).
- The agent matches the user's message against option descriptions. If clear, proceed without asking.

### Playbook `inputs`

Declare what the agent needs before starting and during execution.

```yaml
inputs:
  - name: target_tables
    required: true
    description: "Tables to classify and protect"
    phase: before_start
  - name: admin_role
    required: true
    description: "Role with policy creation privileges"
    default: SECURITYADMIN
    phase: before_start
```

- `phase: before_start` — gather before beginning step 1.
- `phase: step_N` — gather before or during step N.
- `default` — use this value unless the user specifies otherwise.

### Probes

Probes are mandatory discovery queries that run before step 1. They validate the environment and gate execution.

```yaml
probes:
  - id: existing_policies            # Unique identifier
    query: "SHOW MASKING POLICIES"   # SQL to execute
    required: true                   # Must pass to proceed
    validate:                        # Validation rules
      - condition: "count > 100"
        action: warn
        message: "Large number of existing policies"
```

**Validation actions:**

| Action | Behavior |
|--------|----------|
| `pass` | Continue silently (implicit when no condition matches) |
| `warn` | Log warning, continue, surface in next checkpoint |
| `confirm` | Pause for explicit user confirmation before proceeding |
| `block` | Stop execution immediately, escalate to user |

Probes execute in order. If any probe with `required: true` returns a `block` action, execution halts. The agent emits a `probes_executed` event with all results before proceeding.

### Checkpoints

Playbooks define checkpoint positions with severity levels. The agent generates options dynamically based on step results.

```yaml
**Checkpoint:**
  severity: review
  present: "Classification complete. Found {pii_count} PII columns."
```

**Severity levels:**

| Level | Behavior | Use When |
|-------|----------|----------|
| `info` | Log event, auto-proceed after 3s unless user intervenes | Low-risk informational updates |
| `review` | Pause, require explicit approval (default) | Standard checkpoints |
| `critical` | Pause, require typed confirmation | Destructive or irreversible actions |

Every checkpoint must include at minimum: **approve**, **modify**, **abort**, and **different-approach**. Checkpoints can cycle: when the human chooses "modify," the agent does more work within the step and re-presents. The step completes only after approval.

Batch approval is available: "approve_remaining" approves all subsequent `review`-level checkpoints (but not `critical`).

### Compensation Actions

Each step that creates or modifies objects must declare a compensation action for rollback.

```yaml
### Step 3: Create masking policies

Reference: `primitives/masking-policies`

```sql
CREATE MASKING POLICY {policy_name} AS (val STRING) ...
```

Compensation:
```sql
DROP MASKING POLICY IF EXISTS {policy_name};
```

Creates:
  - type: masking_policy
    name: "{policy_name}"
```

When a step completes, the agent logs a `step_completed` event with `created_objects`. On abort or failure, the agent proposes cleanup using compensation actions from completed steps.

### Error Categories

Global error categories provide default handling for common failure patterns. Step-specific `expected_errors` override these defaults.

| Category | Patterns | Retryable | Default Recovery |
|----------|----------|-----------|------------------|
| `permission` | "Insufficient privileges", "Access denied", "not authorized" | No | Check role grants, escalate |
| `object_exists` | "already exists", "duplicate", "conflicts with" | Yes | Use CREATE OR REPLACE |
| `object_not_found` | "does not exist", "not found", "unknown" | No | Verify object name, escalate |
| `transient` | "timeout", "connection", "temporarily unavailable" | Yes (3x) | Exponential backoff retry |
| `resource` | "warehouse.*suspended", "quota exceeded" | Yes (2x) | Resume warehouse or wait |
| `syntax` | "syntax error", "invalid", "unexpected" | No | Review SQL, escalate |
| `conflict` | "concurrent", "modified by", "locked" | Yes (2x) | Linear backoff retry |

Error matching priority:
1. Step-specific `expected_errors` (exact match)
2. Primitive-specific `expected_errors`
3. Global error categories (pattern match)
4. Unknown → escalate immediately

### Step-specific Expected Errors

Steps may override global categories with specific handling:

```yaml
Expected errors:

| Pattern | Recovery | Retryable |
|---------|----------|-----------|
| `Insufficient privileges` | Grant CREATE MASKING POLICY to {admin_role} | No — escalate |
| `already exists` | Use CREATE OR REPLACE syntax | Yes |
```

## File Conventions

- Skill directories: `kebab-case`, lowercase
- Main skill file: `skill.md` (primitives), `router.md` (routers), `playbook.md` (playbooks)
- Supporting files: descriptive `kebab-case.md` or `kebab-case.sql`
- Examples directory: `examples/`
- Playbook steps directory: `steps/`
- No single file over 500 lines

## References Convention

Skills reference each other by `{type}/{name}` format, never by relative file path.

| Context | Format | Example |
|---------|--------|---------|
| `depends_on` in front-matter | Bare name | `masking-policies` |
| `routes_to` in front-matter | Type-prefixed | `primitives/masking-policies` |
| Markdown body text | Type-prefixed | `primitives/masking-policies` |

References in body text follow DAG rules:
- Router bodies → primitives and playbooks
- Playbook bodies → primitives only
- Primitive bodies → other primitives (related concepts)

## Manifest

The `skill-index.yaml` indexes every skill and carries the library version. The agent reads this file to discover what exists, then reads `router.md` (the meta-router) to begin.

```yaml
version: "1.0"
entry: router.md

primitives:
  dynamic-tables:
    domain: data-transformation

routers:
  data-security:
    domain: data-security
    routes_to:
      - primitives/data-classification
      - primitives/masking-policies
      - playbooks/secure-sensitive-data

playbooks:
  secure-sensitive-data:
    domain: data-security
    depends_on: [data-classification, masking-policies, row-access-policies, projection-policies, account-usage-views]
```

The manifest is the single source of truth for discovery. The meta-router (`router.md`) is the single source of truth for entry.

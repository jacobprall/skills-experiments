# Authoring Guide

How to write skills for the Standard Skills Library. Every skill must conform to the templates in this guide, the schema in `skill-schema.md`, and the principles in `standard-skills-library.md`.

## Principles

1. **Factual over advisory** (primitives): Document what something is and how it works. Do not recommend when to use it — that is the router's job.
2. **Deterministic over interpretive** (routers): Express decisions as matrices and conditional logic, not prose the agent must interpret.
3. **Composed over monolithic** (playbooks): Reference primitives instead of duplicating their content.
4. **Strict DAG**: Meta-router routes to domain routers. Domain routers route down to playbooks/primitives. Playbooks depend down on primitives. No upward edges. No cycles.
5. **Lazy context gathering**: Declare inputs upfront. Infer from context first. Ask users only for what's missing, and prefer choices over open-ended questions.
6. **Concise**: No file over 500 lines. Move examples and step scripts to subdirectories.
7. **Agent-first**: Structure content so an LLM agent can parse it reliably. Use tables over paragraphs for structured data. Use code blocks for all SQL/CLI.
8. **Name-based references**: Always reference other skills by `{type}/{name}` (e.g., `primitives/masking-policies`), never by relative file path.
9. **Probe before mutate**: Playbooks must include pre-execution probes so the agent knows what exists before creating or altering objects.
10. **Checkpoints with exits**: Every playbook must have at least one checkpoint. Every checkpoint must offer abort and different-approach options.

## Primitive Template

```markdown
---
type: primitive
name: {kebab-case-name}
domain: {domain}
snowflake_docs: "https://docs.snowflake.com/en/..."
tested_on:
  snowflake_version: "{version}"
  test_date: "{YYYY-MM-DD}"
  test_account_type: "enterprise"
last_reviewed: "{YYYY-MM-DD}"
---

# {Display Name}

One-line description of the Snowflake concept.

## Syntax

\```sql
{SQL syntax with placeholders}
\```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| ... | ... | ... | ... | ... |

## Parameters

Detailed parameter descriptions, valid values, and interactions.

## Constraints

- Limit 1
- Known edge cases

## Examples

### Basic

\```sql
{minimal working example}
\```

### Advanced

\```sql
{complex real-world example}
\```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| ... | ... | ... |
```

## Router Template

```markdown
---
type: router
name: {kebab-case-name}
domain: {domain}
parameters:
  - name: {input_name}
    description: "{what this input captures}"
    options:
      - id: {option-id}
        description: "{human-readable description of this option}"
      - id: {option-id}
        description: "{human-readable description of this option}"
routes_to:
  - primitives/{name}
  - playbooks/{name}
---

# {Decision Space Name}

One-line description of what decision this router resolves.

## Decision Criteria

What the agent needs to know before routing:

| Input | How to Determine | Example |
|-------|-----------------|---------|
| ... | ... | ... |

## Routing Logic

\```
Start
  ├─ {broad intent}? → playbooks/{x}
  ├─ {moderate intent}? → primitives/{y} (guided)
  ├─ {narrow condition}? → primitives/{z} (reference)
  └─ else → ask for clarification
\```

## Routes To

| Target | Mode | When Selected | What It Provides |
|--------|------|---------------|------------------|
| `playbooks/{x}` | playbook | {broad condition} | {outcome} |
| `primitives/{y}` | guided | {moderate condition} | {outcome} |
| `primitives/{z}` | reference | {narrow condition} | {outcome} |

## Anti-patterns

| Mis-routing | Why It Happens | Correct Route |
|-------------|----------------|---------------|
| ... | ... | ... |
```

## Playbook Template

```markdown
---
type: playbook
name: {kebab-case-name}
domain: {domain}
depends_on: [{primitive-a}, {primitive-b}]
inputs:
  - name: target_account
    required: false
    description: "Snowflake account to operate on (defaults to current)"
    phase: before_start
    type: account_locator
  - name: {input_name}
    required: true
    description: "{what this input captures}"
    phase: before_start
  - name: {input_name}
    required: true
    description: "{what this input captures}"
    phase: step_2
probes:
  - id: account_verification
    query: "SELECT CURRENT_ACCOUNT(), CURRENT_ROLE()"
    required: true
    validate:
      - condition: "target_account IS NOT NULL AND account != target_account"
        action: block
        message: "Connected to wrong account"
  - id: {probe_name}
    query: "{discovery SQL}"
    required: true
    validate:
      - condition: "{failure condition}"
        action: block | warn | confirm | pass
        message: "{user-facing message}"
---

# {Outcome Name}

One-line description of what the user will have when done.

## Objective

What this playbook produces, in concrete terms.

## Steps

### Step 1: {Action}

{Description}

Reference: `primitives/{name}`

\```sql
{example SQL for this step}
\```

Expected errors:

| Pattern | Recovery | Retryable |
|---------|----------|-----------|
| ... | ... | ... |

**Checkpoint:**
  severity: review
  present: "{what to show the user}"

### Step 2: {Action}

Creates: `{object_type}:{object_name}`
Compensation: `DROP {object_type} IF EXISTS {object_name}`

{Description}

Reference: `primitives/{name}`

**Checkpoint:**
  severity: critical
  present: "{what to show the user}"

### Step N: {Action} (conditional)

**This step is conditional.** Skip if {condition}. Emit `step_skipped` with reason.

...

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| ... | ... | ... |
```

Note: Playbook steps reference `primitives/{name}` only. No router references — the router was already consulted before the playbook was entered. Sub-steps (e.g., "3b") are allowed when execution context requires actions beyond the step title.

**Checkpoint severity levels:**

| Severity | Behavior |
|----------|----------|
| `info` | Batch-approvable, low risk |
| `review` | Requires individual review (default) |
| `critical` | Must approve individually, high-stakes |

**Compensation actions:** Steps that create objects should declare `Creates:` and `Compensation:` so the agent can rollback on abort.

## Checklist Before Submitting

### All Skills
- [ ] Front-matter has all required fields per `skill-schema.md`
- [ ] `name` matches directory name
- [ ] `domain` is from the controlled vocabulary
- [ ] No `version` in skill front-matter (library-level only in manifest)
- [ ] DAG rules respected: no upward edges, no cycles
- [ ] All SQL is in fenced code blocks
- [ ] No file exceeds 500 lines
- [ ] No duplicated content (reference other skills instead)
- [ ] Examples are runnable (valid SQL with clear placeholders)
- [ ] All cross-skill references use `{type}/{name}` format
- [ ] `skill-index.yaml` is updated with the new skill entry

### Primitives
- [ ] No `depends_on` (primitives are leaf nodes)
- [ ] No opinions — document what, not when
- [ ] `snowflake_docs` links to official documentation
- [ ] `tested_on` and `last_reviewed` fields populated

### Routers
- [ ] `routes_to` uses type-prefixed names
- [ ] `parameters.options` use id + description format
- [ ] Routing logic indicates mode (playbook/guided/reference) for each target

### Playbooks
- [ ] `depends_on` lists all primitives it may reference, including sub-step primitives
- [ ] `inputs` declared with phase, description, and type
- [ ] `probes` section with at least one validation rule
- [ ] At least one checkpoint with `severity` level
- [ ] Steps that create objects have `Creates:` and `Compensation:` declarations
- [ ] Expected errors documented where relevant
- [ ] Conditional steps explicitly marked

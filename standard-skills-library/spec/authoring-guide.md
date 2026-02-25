# Authoring Guide

How to write skills for the Standard Skills Library. Every skill must conform to the schema in `skill-schema.md` and the principles in `standard-skills-library.md`.

## Principles

1. **Factual over advisory** (primitives): Document what, not when.
2. **Deterministic over interpretive** (routers): Decision trees, not prose.
3. **Composed over monolithic** (playbooks): Reference primitives, don't duplicate.
4. **Strict DAG**: Edges point down only. No cycles. No upward references.
5. **Probe before mutate** (playbooks): Check existing state before creating objects.
6. **Concise**: No file over 500 lines. Tables over paragraphs. Code blocks for SQL.

## Primitive Template

```markdown
---
type: primitive
name: {kebab-case-name}
domain: {domain}
snowflake_docs: "https://docs.snowflake.com/en/..."
---

# {Display Name}

One-line description of the Snowflake concept.

## Syntax

\```sql
{SQL syntax with placeholders}
\```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|

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
```

## Router Template

```markdown
---
type: router
name: {kebab-case-name}
domain: {domain}
routes_to:
  - primitives/{name}
  - playbooks/{name}
---

# {Decision Space Name}

One-line description of what decision this router resolves.

## Decision Criteria

| Input | How to Determine | Example |
|-------|-----------------|---------|

## Routing Logic

\```
Start
  ├─ {broad intent}? → playbooks/{x}
  ├─ {specific need}? → primitives/{y}
  └─ else → ask for clarification
\```

## Routes To

| Target | When Selected | What It Provides |
|--------|---------------|------------------|

## Anti-patterns

| Mis-routing | Why It Happens | Correct Route |
|-------------|----------------|---------------|
```

## Playbook Template

```markdown
---
type: playbook
name: {kebab-case-name}
domain: {domain}
depends_on: [{primitive-a}, {primitive-b}]
---

# {Outcome Name}

One-line description of what the user will have when done.

## Objective

What this playbook produces, in concrete terms.

## Prerequisites

- Required role
- Required objects

## Steps

### Step 1: {Action}

Reference: `primitives/{name}`

\```sql
{example SQL for this step}
\```

Confirm results with the user before proceeding.

### Step 2: {Action}

Reference: `primitives/{name}`

\```sql
{example SQL}
\```

### Step N: {Action} (conditional)

Skip if {condition}.

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
```

## Checklist Before Submitting

### All Skills
- [ ] Front-matter has required fields per `skill-schema.md`
- [ ] `name` matches directory name
- [ ] `domain` is from the controlled vocabulary
- [ ] DAG rules respected: no upward edges, no cycles
- [ ] All SQL in fenced code blocks
- [ ] No file exceeds 500 lines
- [ ] No duplicated content (reference other skills instead)
- [ ] Examples are runnable SQL with clear placeholders
- [ ] All cross-skill references use `{type}/{name}` format
- [ ] `index.yaml` is updated with the new skill entry

### Primitives
- [ ] No `depends_on` (leaf nodes)
- [ ] No opinions — document what, not when
- [ ] `snowflake_docs` links to official documentation

### Routers
- [ ] `routes_to` uses type-prefixed names
- [ ] Routing logic is a decision tree or matrix
- [ ] Broad intent routes to playbook, narrow to primitive

### Playbooks
- [ ] `depends_on` lists all primitives it may reference
- [ ] Steps reference primitives, not routers
- [ ] At least one confirmation point with the user
- [ ] Conditional steps explicitly marked

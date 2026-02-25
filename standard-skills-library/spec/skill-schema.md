# Skill Schema

Field-level schema for skill front-matter. For principles and architecture, see `standard-skills-library.md`.

## Front-matter Schema

### Common Fields (all types)

```yaml
---
type: primitive | router | playbook   # REQUIRED
name: kebab-case-name                 # REQUIRED — must match directory name
domain: domain-name                   # REQUIRED — from controlled vocabulary
---
```

### Primitive

```yaml
---
type: primitive
name: dynamic-tables
domain: data-transformation
snowflake_docs: "https://docs.snowflake.com/en/..."
---
```

No `depends_on` — primitives are leaf nodes.

| Field | Required | Description |
|-------|----------|-------------|
| `snowflake_docs` | Recommended | Link to official Snowflake documentation |

### Router

```yaml
---
type: router
name: data-security
domain: data-security
routes_to:
  - primitives/data-classification
  - primitives/masking-policies
  - playbooks/secure-sensitive-data
---
```

No `depends_on` — routers are entry points, not dependencies.

| Field | Required | Description |
|-------|----------|-------------|
| `routes_to` | Required | Skills this router can select (type-prefixed) |

### Playbook

```yaml
---
type: playbook
name: secure-sensitive-data
domain: data-security
depends_on:
  - data-classification
  - masking-policies
  - row-access-policies
  - projection-policies
  - account-usage-views
---
```

| Field | Required | Description |
|-------|----------|-------------|
| `depends_on` | Required | Primitives this playbook composes (bare names) |

`depends_on` lists all primitives the playbook may reference. Never routers, never other playbooks.

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
| `# {Name}` | Yes | Title, decision space description |
| `## Decision Criteria` | Yes | What inputs are needed to route |
| `## Routing Logic` | Yes | Decision tree or matrix — deterministic |
| `## Routes To` | Yes | Table of targets with selection conditions |
| `## Anti-patterns` | No | Common mis-routings and corrections |

### Playbooks

| Section | Required | Purpose |
|---------|----------|---------|
| `# {Name}` | Yes | Title, outcome description |
| `## Objective` | Yes | What the user will have when done |
| `## Prerequisites` | Yes | What must exist before starting |
| `## Steps` | Yes | Numbered steps referencing primitives |
| `## Anti-patterns` | No | Common workflow mistakes |

### Playbook Step Structure

Each step should:
1. State what it does in one line
2. Reference the primitive(s) it draws from (`Reference: primitives/{name}`)
3. Include example SQL showing the action
4. Note where to confirm with the user before proceeding
5. Mark conditional steps explicitly ("Skip if {condition}")

Sub-steps (e.g., "3b") are fine when execution context requires additional actions.

## References Convention

| Context | Format | Example |
|---------|--------|---------|
| `depends_on` in front-matter | Bare name | `masking-policies` |
| `routes_to` in front-matter | Type-prefixed | `primitives/masking-policies` |
| Markdown body text | Type-prefixed | `primitives/masking-policies` |

## File Conventions

- Skill directories: `kebab-case`, lowercase
- Main file: `skill.md` (primitives), `router.md` (routers), `playbook.md` (playbooks)
- No single file over 500 lines

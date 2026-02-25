# Standard Skills Library — Specification

Structured knowledge for coding agents working with Snowflake. Organized as a strict DAG that the agent traverses to complete tasks with precision.

---

## Principles

Ordered by importance. When principles conflict, higher-ranked wins.

### 1. Deterministic skeleton, LLM at the joints

The agent follows structured paths through the skill DAG. LLM reasoning happens at defined decision points: resolving user intent (routers), adapting to environment state (probes), and responding to feedback (user confirmation). The paths are predictable; the decisions at junctions are flexible.

### 2. Knowledge as a strict DAG

Skills compose in one direction only. The entry point routes to domain routers. Routers resolve to playbooks or primitives. Playbooks orchestrate through primitives. Primitives are leaf nodes. No cycles, no upward edges. Each layer is independently testable and replaceable.

### 3. Factual over advisory

Primitives document *what* something is and *how* it works. They never recommend *when* to use it. Recommendations live in routers (decision logic) and playbooks (workflow design). Separating facts from opinions prevents the agent from inheriting false confidence from contaminated reference material.

### 4. Probe before mutate

Before creating, altering, or dropping objects, always check what exists. Run SHOW, DESCRIBE, SELECT, and INFORMATION_SCHEMA queries to understand current state. This prevents collisions with existing objects, catches broken state, and avoids overwriting important configurations.

### 5. Small over comprehensive

No skill file exceeds 500 lines. Scope is constrained to keep the agent's context window manageable. Primitives cover one Snowflake concept. Playbooks cover one workflow. Expand scope only when quality can be maintained.

### 6. Composed over monolithic

Playbooks reference primitives; they don't duplicate them. Routers reference playbooks and primitives; they don't inline their content. Every piece of knowledge exists in exactly one place. When a Snowflake feature changes, updating one primitive propagates everywhere.

---

## Architecture

### The Skill DAG

Four layers. Edges point downward only.

```
               ┌─────────────┐
               │  SKILL.md   │  ← single entry point
               └──────┬──────┘
                      │
           ┌──────────┼──────────┐
           ▼          ▼          ▼
      ┌────────┐ ┌────────┐ ┌────────┐
      │Router A│ │Router B│ │Router C│  ← domain routers
      └───┬────┘ └───┬────┘ └───┬────┘
          │          │          │
     ┌────┴────┐     ▼     ┌───┴───┐
     ▼         ▼           ▼       ▼
┌────────┐┌─────────┐┌─────────┐┌─────────┐
│Playbook││Primitive ││Playbook ││Primitive │
└───┬────┘└─────────┘└───┬─────┘└─────────┘
    │                    │
    ▼ ▼ ▼                ▼ ▼
  Primitives           Primitives
```

### Layers

| Layer | What It Does | Edge Rules |
|-------|--------------|------------|
| **SKILL.md** | Single entry point. Routes to domain router(s). Composes cross-domain chains. | Routes to domain routers only. Never directly to playbooks or primitives. |
| **Domain Routers** | Classify intent within a domain. Select target skill. | `routes_to` playbooks and primitives. Nothing depends on routers. |
| **Playbooks** | Step-by-step workflows that compose primitives. | `depends_on` primitives only. Never reference routers or other playbooks. |
| **Primitives** | Factual reference for one Snowflake concept. | Leaf nodes. No outgoing edges. |

### Edge Rules

| From | To | Allowed |
|------|----|---------|
| SKILL.md | Domain Router | Yes |
| SKILL.md | Playbook or Primitive | No |
| Domain Router | Primitive | Yes |
| Domain Router | Playbook | Yes |
| Domain Router | Domain Router | No |
| Playbook | Primitive | Yes |
| Playbook | Router | No |
| Playbook | Playbook | No |
| Primitive | anything | No (leaf) |

**Why no upward or lateral edges:** A playbook never references a router because the router was already consulted before the playbook was entered. A playbook never references another playbook because nesting creates unbounded depth. Primitives never reference playbooks because reference material doesn't drive workflows. SKILL.md never bypasses domain routers because domain-level decision logic belongs in the domain.

### Agent Traversal

```
1. Read SKILL.md → identify domain(s) from user intent
2. Read the domain router → router picks: playbook or primitive
3. Follow the target:
   ├── Playbook → follow steps, each referencing primitives
   └── Primitive → direct SQL/syntax reference
4. If the goal spans multiple domains → chain in dependency order
```

### Cross-Domain Chaining

When user intent spans multiple domains, SKILL.md declares domain dependencies via `produces`/`requires`. The agent executes domains in topological order — producers before consumers.

Each domain produces context (table names, policy names, service URLs) that flows to subsequent domains. The agent carries concrete outputs forward naturally through conversation.

---

## Skill Types

### Primitives

Factual reference for a single Snowflake concept.

**Front-matter:**

```yaml
---
type: primitive
name: masking-policies
domain: data-security
snowflake_docs: "https://docs.snowflake.com/..."
---
```

**Required sections:**

| Section | Purpose |
|---------|---------|
| `# {Name}` | Title + one-line description |
| `## Syntax` | SQL/CLI syntax with parameter descriptions |
| `## Parameters` | Table: name, type, default, description |
| `## Constraints` | Limits, prerequisites, edge cases |
| `## Examples` | Runnable SQL — basic and advanced |

**Optional:** `## Anti-patterns` — common mistakes and why they fail.

**Rules:**
- No opinions on *when* to use this feature (routers decide that)
- All SQL in fenced code blocks with clear placeholders
- Examples must be runnable (valid SQL, not pseudocode)

### Domain Routers

Resolve user intent within a domain to a target skill.

**Front-matter:**

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

**Required sections:**

| Section | Purpose |
|---------|---------|
| `# {Name}` | Title + decision space description |
| `## Decision Criteria` | What the agent needs to determine |
| `## Routing Logic` | Decision flowchart — deterministic, not prose |
| `## Routes To` | Table of targets with selection conditions |

**Optional:** `## Anti-patterns` — common mis-routings.

**Rules:**
- Routing logic must be a decision tree or matrix, not narrative
- Check for broad intent first (playbook), then narrow (primitive)
- If ambiguous, ask the user to clarify

### Playbooks

Step-by-step workflows that compose primitives.

**Front-matter:**

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

**Required sections:**

| Section | Purpose |
|---------|---------|
| `# {Name}` | Title + one-line outcome description |
| `## Objective` | Concrete deliverables when done |
| `## Prerequisites` | What must exist before starting |
| `## Steps` | Numbered steps, each referencing primitives |

**Optional:** `## Anti-patterns` — common workflow mistakes.

**Step structure:** Each step should:
1. State what it does in one line
2. Reference the primitive(s) it draws from
3. Include example SQL
4. Note where to confirm with the user before proceeding

**Rules:**
- `depends_on` lists primitives only. Never routers or other playbooks.
- Steps reference `primitives/{name}`. No router references.
- At least one point where the agent should confirm with the user before continuing.
- Sub-steps (e.g., "3b") are fine when the context requires additional actions.

---

## Conventions

### File Structure

```
standard-skills-library/
├── SKILL.md                         # Entry point (Cursor skill)
├── index.yaml                       # Discovery manifest
├── scripts/                         # Tools (snow-sql)
├── routers/{name}/router.md         # One router per domain
├── playbooks/{name}/playbook.md     # One playbook per workflow
├── primitives/{name}/skill.md       # One primitive per concept
└── spec/                            # Design docs (for authors, not runtime)
```

### Naming

- Directories: `kebab-case`, lowercase only
- Skill files: `skill.md` (primitives), `router.md` (routers), `playbook.md` (playbooks)
- Front-matter `name` must match directory name exactly
- Full words unless abbreviation is more recognized (e.g., `spcs` is fine)

### References

Skills reference each other by `{type}/{name}` format, never by file path.

| Context | Format | Example |
|---------|--------|---------|
| `routes_to` in front-matter | Type-prefixed | `primitives/masking-policies` |
| `depends_on` in front-matter | Bare name | `masking-policies` |
| Markdown body | Type-prefixed | `primitives/masking-policies` |

References in body text follow DAG rules:
- Router bodies → primitives and playbooks
- Playbook bodies → primitives only
- Primitive bodies → other primitives (related concepts)

### Domain Taxonomy

Valid domains are defined in `spec/controlled-vocabulary.md`. Every skill must declare one.

---

## Constraints

Hard rules. If a skill breaks any of these, it is invalid.

1. **No cycles in the DAG.** A skill cannot reference itself or create a path back to itself.
2. **No upward edges.** Playbooks never reference routers. Primitives never reference playbooks or routers.
3. **No playbook-to-playbook dependencies.** Playbooks compose primitives only.
4. **No opinions in primitives.** Primitives document syntax and behavior. Routing decisions belong in routers.
5. **No duplicated knowledge.** If a fact exists in a primitive, playbooks reference it, not restate it.
6. **No file over 500 lines.** Split if needed.
7. **No unregistered skills.** Every skill must appear in `index.yaml`.
8. **SKILL.md never bypasses domain routers.** Always route through a domain router.
9. **Exactly one entry point.** `SKILL.md` at the repo root.

---

## What This Is

Structured knowledge for coding agents. Not an agent framework, not a prompt repository, not code. A collection of markdown files organized as a strict DAG that an agent traverses to complete Snowflake tasks with expert-level precision.

Any system that can read markdown and follow references can use this library. Install it as a Cursor skill, inject it into a system prompt, or use it as reference material for any coding agent.


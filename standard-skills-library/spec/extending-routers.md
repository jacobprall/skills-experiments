# Extending the Router Network

How to add new domains to the Standard Skills Library.

## Overview

Adding a new domain requires:

1. Creating a domain router, playbooks, and primitives
2. Registering them in `SKILL.md` and `index.yaml`
3. Adding the domain to the controlled vocabulary

## Quick Start

### 1. Create Your Router

```markdown
---
type: router
name: {domain-name}
domain: {domain-name}
routes_to:
  - primitives/{your-primitive}
  - playbooks/{your-playbook}
---

# {Domain Name}

One-line description.

## Decision Criteria

| Input | How to Determine | Example |
|-------|------------------|---------|

## Routing Logic

\```
Start
  ├─ {condition}? → playbooks/{x}
  └─ {condition}? → primitives/{y}
\```

## Routes To

| Target | When Selected | What It Provides |
|--------|---------------|------------------|
```

### 2. Register in SKILL.md

Add your domain to the routing table and keywords table in `SKILL.md`:

```markdown
| `your-domain` | `routers/your-domain/router.md` | keyword1, keyword2, keyword3 |
```

If the domain participates in cross-domain chaining, add it to the dependency table:

```markdown
| `your-domain` | what-it-produces | what-it-requires | position |
```

### 3. Update index.yaml

```yaml
primitives:
  your-primitive:
    domain: your-domain

routers:
  your-domain:
    domain: your-domain
    routes_to:
      - primitives/your-primitive
      - playbooks/your-playbook

playbooks:
  your-playbook:
    domain: your-domain
    depends_on: [your-primitive]
```

### 4. Update Controlled Vocabulary

Add your domain to `spec/controlled-vocabulary.md`.

## Domain Dependencies

The `produces`/`requires` declarations in SKILL.md enable cross-domain chaining:

| Domain Type | Typically Produces | Typically Requires |
|-------------|-------------------|-------------------|
| Ingestion/Transformation | tables, pipelines | — |
| Security | policies | tables |
| Analytics/AI | enriched tables, reports | tables |
| Deployment | applications | tables |
| Operations (cost, observability) | recommendations | — (standalone) |

**Rules:**
- Domains with no `requires` can start a chain or run standalone
- Domains are executed in topological order: producers before consumers
- Some domains (cost-ops, observability) are typically standalone — they don't produce artifacts for other domains

## Validation Checklist

Before registering a new domain:

- [ ] Router follows schema (`type: router`, `routes_to`)
- [ ] All `routes_to` targets exist and are registered in `index.yaml`
- [ ] Primitives follow schema
- [ ] Playbooks follow schema (including `depends_on`)
- [ ] Domain name added to controlled vocabulary
- [ ] Keywords don't conflict with existing domains
- [ ] SKILL.md routing table and keywords table updated
- [ ] `index.yaml` updated with all new entries
- [ ] No circular dependencies in domain chaining

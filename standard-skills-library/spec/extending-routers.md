# Extending the Router Network

How to add domain routers from external repos or skill packages.

## Overview

The meta-router (`router.md`) is designed for extension. Adding a new domain router requires:

1. Creating a router that follows the schema
2. Registering it in the meta-router's `domains` block
3. Adding entries to `skill-index.yaml`

## Quick Start

### 1. Create Your Router

Your router must follow the standard schema. Minimum structure:

```markdown
---
type: router
name: {domain-name}
domain: {domain-name}
parameters:
  - name: user_goal
    description: "What the user wants to accomplish"
    options:
      - id: option-1
        description: "Description for routing"
routes_to:
  - primitives/{your-primitive}
  - playbooks/{your-playbook}
---

# {Domain Name}

One-line description.

## Decision Criteria

| Input | How to Determine | Example |
|-------|------------------|---------|
| ... | ... | ... |

## Routing Logic

\```
Start
  ├─ {condition}? → playbooks/{x}
  └─ {condition}? → primitives/{y}
\```

## Routes To

| Target | Mode | When Selected |
|--------|------|---------------|
| ... | ... | ... |
```

### 2. Register in Meta-Router

Add your domain to `router.md` front-matter:

```yaml
domains:
  # Existing domains...
  
  your-domain:
    router: routers/your-domain        # or: external/your-repo/router
    produces: [output-type]            # What this domain creates
    requires: [input-type]             # What this domain needs (for chaining)
    description: "What this domain handles"
    context_mapping:                   # How previous phase outputs map to this domain's inputs
      created_tables → target_scope
    outputs:                           # Declared outputs for context handoff
      - name: created_objects
        type: list[string]
        description: "Objects created by this domain"
```

### 3. Update Manifest

Add entries to `skill-index.yaml`:

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

### 4. Add Keywords to Meta-Router

Update the domain keywords table in `router.md`:

```markdown
| Domain | Keywords |
|--------|----------|
| `your-domain` | keyword1, keyword2, keyword3 |
```

## Domain Dependencies

The `produces` and `requires` fields enable automatic chaining:

```yaml
domains:
  data-transformation:
    produces: [tables, pipelines]      # Creates these
    requires: []                       # Needs nothing
    
  your-domain:
    produces: [reports, alerts]        # Creates these
    requires: [tables]                 # Needs tables first
```

**Chaining rules:**
- Domains with no `requires` can start a chain
- Domains are topologically sorted: producers before consumers
- Context flows forward: outputs from phase N available to phase N+1

### Common Dependency Patterns

| Domain Type | Typically Produces | Typically Requires |
|-------------|-------------------|-------------------|
| Ingestion | tables, streams | — |
| Transformation | tables, pipelines | tables |
| Security | policies, governance | tables |
| Analytics | reports, dashboards | tables, policies |
| Deployment | applications, endpoints | tables |

## External Router Locations

Routers can live in different locations:

```yaml
domains:
  # Local (in this repo)
  data-security:
    router: routers/data-security
    
  # Subdirectory (external package copied in)
  ml-workflows:
    router: external/ml-skills/routers/ml-workflows
    
  # Relative path (sibling repo, monorepo)
  cost-ops:
    router: ../cost-skills/routers/cost-operations
```

**Recommended structure for external skills:**

```
your-skills-package/
├── routers/
│   └── your-domain/
│       └── router.md
├── playbooks/
│   └── your-playbook/
│       └── playbook.md
├── primitives/
│   └── your-primitive/
│       └── skill.md
└── manifest-fragment.yaml    # Partial manifest for merging
```

## Manifest Fragments

For external packages, provide a `manifest-fragment.yaml` that can be merged:

```yaml
# manifest-fragment.yaml
primitives:
  your-primitive:
    domain: your-domain

routers:
  your-domain:
    domain: your-domain
    routes_to:
      - primitives/your-primitive

playbooks:
  your-playbook:
    domain: your-domain
    depends_on: [your-primitive]
```

The integrator merges this into the main `skill-index.yaml`.

## Validation Checklist

Before registering an external router:

- [ ] Router follows `type: router` schema
- [ ] All `routes_to` targets exist and are registered
- [ ] `produces`/`requires` use consistent vocabulary across domains
- [ ] Keywords don't conflict with existing domains
- [ ] Primitives follow the primitive schema (including `tested_on`, `last_reviewed`)
- [ ] Playbooks follow the playbook schema (including `probes`, checkpoint `severity`)
- [ ] No circular dependencies in domain `requires` (manifest validation will catch this)
- [ ] Context mappings reference valid output/input names

## Example: Adding a Cost Operations Domain

**1. Create `routers/cost-operations/router.md`:**

```yaml
---
type: router
name: cost-operations
domain: cost-operations
parameters:
  - name: user_goal
    options:
      - id: analyze-spend
        description: "Understand where credits are going"
      - id: reduce-costs
        description: "Optimize warehouse and query costs"
routes_to:
  - primitives/warehouse-sizing
  - primitives/resource-monitors
  - playbooks/cost-optimization
---
```

**2. Register in `router.md`:**

```yaml
domains:
  cost-operations:
    router: routers/cost-operations
    produces: [cost-reports, budgets]
    requires: [tables]  # Needs data to analyze
    description: "Understand and control Snowflake spend"
```

**3. Add keywords:**

```markdown
| `cost-operations` | cost, credits, spend, budget, warehouse sizing, optimize |
```

**4. Update `skill-index.yaml`:**

```yaml
routers:
  cost-operations:
    domain: cost-operations
    routes_to:
      - primitives/warehouse-sizing
      - primitives/resource-monitors
      - playbooks/cost-optimization
```

Now the meta-router can:
- Route "analyze my Snowflake costs" → cost-operations domain
- Chain "build pipeline and optimize costs" → [data-transformation, cost-operations]

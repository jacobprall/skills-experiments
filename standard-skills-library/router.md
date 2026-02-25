---
type: meta-router
name: entry

routing:
  confidence_threshold: 0.7
  ambiguity_threshold: 0.2
  scoring:
    keyword_match: 0.3
    intent_pattern: 0.4
    context_signals: 0.3

guided_mode:
  max_steps: 8
  require_primitives: true
  checkpoint_frequency: every_step
  prohibited_actions:
    - "DROP DATABASE"
    - "DROP SCHEMA"
    - "GRANT OWNERSHIP"
    - "ALTER ACCOUNT"

dry_run:
  enabled: true
  estimate_duration: true
  estimate_objects: true

validation:
  check_domain_cycles: true
  check_routes_exist: true
  check_primitives_exist: true
  staleness_threshold_days: 180

domains:
  data-transformation:
    router: routers/data-transformation
    produces: [tables, pipelines]
    requires: []
    description: "Transform and reshape data within Snowflake"
    outputs:
      - name: created_tables
        type: list[string]
        description: "Fully qualified table names created"
      - name: pipeline_name
        type: string
        description: "Name of pipeline if created"
  data-security:
    router: routers/data-security
    requires: [tables]
    produces: [policies, governance]
    description: "Protect, classify, and audit data access"
    context_mapping:
      created_tables → target_scope
    outputs:
      - name: applied_policies
        type: list[string]
        description: "Policy names created/applied"
      - name: protected_tables
        type: list[string]
        description: "Tables with policies attached"
  app-development:
    router: routers/app-deployment
    requires: [tables]
    produces: [applications]
    description: "Build and deploy applications on Snowflake data"
    context_mapping:
      created_tables → data_sources
      protected_tables → data_sources
    outputs:
      - name: service_url
        type: string
        description: "Deployed application URL"
---

# Meta-Router

Single entry point for the Standard Skills Library. Resolves user intent to one or more domain routers.

## How It Works

1. **Parse user intent** — identify which domains are involved
2. **Single domain?** — route directly to that domain's router
3. **Multiple domains?** — topologically sort by `requires`/`produces`, chain in order

## Decision Criteria

| Signal | How to Detect | Example |
|--------|---------------|---------|
| **Domain keywords** | Match against domain descriptions and common terms | "mask columns" → data-security, "deploy app" → app-deployment |
| **Multi-domain intent** | User describes an end-to-end flow spanning concerns | "Ingest data from Postgres, secure it, build a dashboard" |
| **Ambiguous intent** | Keywords could map to multiple domains | "protect my pipeline" — security or transformation? |

### Domain Keywords

| Domain | Keywords |
|--------|----------|
| `data-transformation` | transform, pipeline, refresh, dynamic table, dbt, aggregate, join, ETL, ingest, load |
| `data-security` | mask, protect, classify, PII, policy, audit, access control, governance, sensitive |
| `app-deployment` | app, dashboard, Streamlit, deploy, SPCS, container, UI, frontend |

## Routing Confidence

The meta-router computes a confidence score for each candidate domain. This prevents incorrect routing on ambiguous requests.

### Scoring Components

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| `keyword_match` | 0.3 | Presence of domain keywords in user message |
| `intent_pattern` | 0.4 | Match against intent templates (e.g., "build a * pipeline") |
| `context_signals` | 0.3 | Session history, previously selected domains, data mentioned |

### Thresholds

| Threshold | Value | Behavior |
|-----------|-------|----------|
| `confidence_threshold` | 0.7 | Below this, ask for clarification instead of routing |
| `ambiguity_threshold` | 0.2 | If top two candidates are within this delta, ask for clarification |

### Routing Events

High confidence:
```yaml
- type: routed
  router: data-security
  target: playbooks/secure-sensitive-data
  mode: playbook
  confidence: 0.85
  alternatives:
    - domain: data-transformation
      confidence: 0.23
```

Ambiguous (requires clarification):
```yaml
- type: routing_ambiguous
  top_candidates:
    - domain: data-security
      confidence: 0.52
    - domain: data-transformation
      confidence: 0.48
  clarification_options:
    - id: security
      description: "I want to protect, mask, or classify data"
    - id: transformation
      description: "I want to transform, aggregate, or build pipelines"
```

## Routing Logic

```
Start
  │
  ├─ Identify domains in user intent
  │
  ├─ Single domain detected?
  │   └─ YES → Route to that domain's router
  │            (domain router decides: playbook vs guided vs reference)
  │
  ├─ Multiple domains detected?
  │   │
  │   ├─ Build dependency graph from requires/produces
  │   │
  │   ├─ Topologically sort domains
  │   │   (domains that produce what others require go first)
  │   │
  │   └─ Emit chain_started event, begin first phase
  │
  └─ No clear domain?
      └─ Ask user to clarify their goal with structured options
```

### Topological Sort Example

User: "Build a pipeline, apply masking policies, then build a dashboard"

1. **Identify domains**: data-transformation, data-security, app-deployment
2. **Build dependency graph**:
   - `data-transformation` produces `[tables, pipelines]`, requires nothing → can go first
   - `data-security` requires `[tables]` → must follow data-transformation
   - `app-deployment` requires `[tables]` → must follow data-transformation
   - `data-security` and `app-deployment` have no dependency between them, but security before app is logical
3. **Sorted order**: `[data-transformation, data-security, app-deployment]`

## Routes To

| Domain | Router | When Selected |
|--------|--------|---------------|
| `data-transformation` | `routers/data-transformation` | User wants to transform, aggregate, build pipelines, or ingest data |
| `data-security` | `routers/data-security` | User wants to classify, mask, restrict, or audit data |
| `app-deployment` | `routers/app-deployment` | User wants to build or deploy an application |

## Guided Mode Guardrails

When no playbook matches and the agent enters guided mode, these guardrails apply:

### Plan Validation Rules

| Rule | Limit | On Violation |
|------|-------|--------------|
| Max steps | 8 | Refuse plan, suggest breaking into smaller goals |
| Primitive requirement | Every step must reference a primitive | Reject step without primitive reference |
| Prohibited actions | DROP DATABASE, DROP SCHEMA, GRANT OWNERSHIP, ALTER ACCOUNT | Block — these require playbook-level review |

### Checkpoint Frequency

In guided mode, checkpoints fire **after every step** (not just at approval boundaries). This compensates for the higher risk of agent-generated plans.

### Complexity Escape Hatch

If a goal exceeds guided mode limits:

```yaml
- type: plan_rejected
  reason: "complexity_exceeded"
  message: "This goal requires 12 steps. Guided mode is limited to 8."
  options:
    - id: break_down
      description: "Help me break this into smaller goals"
    - id: request_playbook
      description: "This should be a playbook — let's document it"
    - id: proceed_anyway
      description: "I accept the risk — proceed with 12 steps"
      requires_confirmation: true
```

### Context Mapping in Guided Mode

When guided mode operates within a chain, it must respect `context_mapping` declarations. If a required input has no mapping from a previous phase and no default, the agent must gather it from the user before proceeding.

## Dry-Run Mode

Dry-run mode lets users preview what a playbook or guided plan will do without executing anything. This is critical for high-stakes workflows where the user wants to review impact before committing.

### Triggering Dry-Run

The user can request dry-run mode explicitly ("show me what this would do") or the agent can suggest it for complex workflows. Dry-run is enabled by default in the meta-router configuration.

### Dry-Run Events

Instead of `step_started` and `step_completed`, dry-run emits `step_planned`:

```yaml
- type: playbook_started
  playbook: secure-sensitive-data
  mode: dry_run

- type: probes_executed
  # Probes still run in dry-run mode — need real environment state
  
- type: step_planned
  step: 1
  action: "Classify tables in analytics schema"
  would_execute:
    - "CALL SYSTEM$CLASSIFY('analytics.orders')"
    - "CALL SYSTEM$CLASSIFY('analytics.customers')"
    - "... (23 more tables)"
  estimated_duration: "2-5 minutes"
  
- type: step_planned
  step: 3
  action: "Create masking policies"
  would_create:
    - type: masking_policy
      name: "PII_EMAIL_MASK"
      affects_columns: ["orders.customer_email", "customers.email"]
    - type: masking_policy
      name: "PII_PHONE_MASK"
      affects_columns: ["customers.phone"]
  would_execute:
    - "CREATE MASKING POLICY PII_EMAIL_MASK..."
    - "CREATE MASKING POLICY PII_PHONE_MASK..."
```

### Dry-Run Summary

At the end, a summary event shows total impact:

```yaml
- type: dry_run_summary
  playbook: secure-sensitive-data
  would_create:
    masking_policies: 4
    row_access_policies: 1
    projection_policies: 0
    functions: 1
  would_modify:
    tables: 25
    columns: 47
  estimated_duration: "15-30 minutes"
  estimated_compute: "~2 credits"
  options:
    - id: execute
      description: "Proceed with actual execution"
    - id: export_plan
      description: "Export SQL scripts for manual review"
    - id: abort
      description: "Cancel"
```

### What Runs in Dry-Run

| Component | Runs? | Why |
|-----------|-------|-----|
| Probes | ✅ Yes | Need real environment state to plan accurately |
| Input gathering | ✅ Yes | Need user inputs to generate accurate plan |
| SQL execution | ❌ No | Only planned, not executed |
| Checkpoints | ✅ Yes (modified) | Show what would be presented, but no approval needed |

## Manifest Validation

The meta-router validates the skill library structure on load to catch configuration errors before they cause runtime failures.

### Validation Checks

| Check | What It Does | Error Example |
|-------|--------------|---------------|
| `check_domain_cycles` | Detects circular `produces`/`requires` dependencies | "Cycle: data-transformation → cost-operations → data-transformation" |
| `check_routes_exist` | Verifies all `router:` paths point to real files | "Router 'routers/data-security' not found" |
| `check_primitives_exist` | Verifies all `depends_on:` primitives exist | "Primitive 'nonexistent-primitive' referenced but not found" |
| `staleness_threshold_days` | Warns when primitives haven't been reviewed | "Primitive 'masking-policies' last reviewed 192 days ago" |

### Cycle Detection

Circular dependencies between domains would cause infinite routing loops. The validator performs a topological sort on domain dependencies and reports any cycles:

```
ERROR: Domain dependency cycle detected
  data-transformation requires [reports]
  cost-operations produces [reports], requires [pipelines]
  data-transformation produces [pipelines]
  
  Cycle: data-transformation → cost-operations → data-transformation
  
  Resolution: Remove one of these dependencies or merge domains.
```

### Staleness Warnings

Primitives include `last_reviewed` dates. When a primitive exceeds the `staleness_threshold_days` (default 180), the agent emits a warning:

```yaml
- type: staleness_warning
  primitive: masking-policies
  last_reviewed: "2025-08-15"
  days_stale: 192
  message: "This primitive was last reviewed 192 days ago. Snowflake may have changed."
  options:
    - id: proceed
      description: "Use anyway — I'll verify against current docs"
    - id: check_docs
      description: "Open Snowflake documentation for this feature"
```

This helps ensure skill content stays current with Snowflake's evolving features.

## Multi-Domain Chaining

When the user's intent spans multiple domains, the meta-router composes a chain.

### Chain Events

| Event | When | Fields |
|-------|------|--------|
| `chain_started` | Meta-router decomposes multi-domain intent | `domains[]`, `order_rationale` |
| `phase_started` | New domain phase begins | `domain`, `phase_number`, `context_from_previous` |
| `phase_completed` | Domain phase finishes | `domain`, `outputs` |

### Context Handoff

Each phase produces outputs that flow to subsequent phases:

| Domain | Produces | Consumed By |
|--------|----------|-------------|
| `data-transformation` | Table names, pipeline definitions | data-security, app-deployment |
| `data-security` | Policy names, protected tables | app-deployment |
| `app-deployment` | Service endpoints, app URLs | (terminal) |

The agent carries concrete outputs (table names, policy names) from completed phases and maps them to subsequent phase inputs. The `produces`/`requires` declarations are hints — the agent uses judgment to connect outputs to inputs.

### Example Chain Thread

```yaml
thread_id: "thr_secure_dashboard"
events:
  - type: chain_started
    domains: [data-transformation, data-security, app-deployment]
    order_rationale: "data-transformation produces tables; data-security and app-deployment require tables"

  - type: phase_started
    domain: data-transformation
    phase_number: 1
    
  - type: routed
    router: data-transformation
    target: playbooks/build-streaming-pipeline
    mode: playbook
    
  # ... playbook execution events ...
  
  - type: phase_completed
    domain: data-transformation
    outputs:
      tables: ["analytics.order_summary", "analytics.daily_metrics"]
      
  - type: phase_started
    domain: data-security
    phase_number: 2
    context_from_previous:
      tables: ["analytics.order_summary", "analytics.daily_metrics"]
      
  # ... continues through remaining phases
```

## Anti-patterns

| Pattern | Problem | Correction |
|---------|---------|------------|
| Bypassing domain routers | Meta-router routes directly to a playbook or primitive | Always go through a domain router — it decides playbook vs guided vs reference |
| Guessing domain order | Chaining without checking requires/produces | Use topological sort based on declared dependencies |
| Ignoring context handoff | Starting phase 2 without outputs from phase 1 | Explicitly carry forward tables, policies, endpoints from completed phases |
| Over-chaining | Breaking a single-domain request into multiple phases | If the user's intent fits one domain, route directly — don't artificially chain |

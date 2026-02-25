# Standard Skills Library

A methodology for building production-grade, LLM-orchestrated workflows on Snowflake.

## What This Is

This is **structured knowledge for AI agents** — not a code library, not an agent framework, not a prompt repository. It's a collection of markdown files organized as a strict DAG (Directed Acyclic Graph) that an LLM agent traverses to complete Snowflake tasks.

The design prioritizes:
- **Deterministic paths** with LLM reasoning only at defined decision points
- **Human oversight** through structured checkpoints
- **Resumable execution** via stateless, event-sourced threads
- **Agent-parseable content** (tables over prose, code blocks for SQL)
- **Dynamic composition** of multi-domain workflows via dependency-based chaining

## Repository Structure

```
standard-snowflake-skills-library/
├── router.md                        # Meta-router — single entry point
├── skill-index.yaml                    # Skill index (agent reads this first)
├── spec/                            # Methodology specification
│   ├── standard-skills-library.md   # Canonical spec (principles, architecture, execution)
│   ├── skill-schema.md              # Field-level schema for front-matter
│   ├── authoring-guide.md           # Templates for writing new skills
│   └── controlled-vocabulary.md     # Domain taxonomy and naming conventions
├── routers/                         # Domain routers — decision logic per domain
│   ├── data-security/router.md
│   ├── data-transformation/router.md
│   └── app-deployment/router.md
├── playbooks/                       # End-to-end workflows
│   ├── secure-sensitive-data/playbook.md
│   ├── build-streaming-pipeline/playbook.md
│   └── build-react-app/playbook.md
└── primitives/                      # Factual reference (leaf nodes)
    ├── dynamic-tables/skill.md
    ├── dbt-snowflake/skill.md
    ├── masking-policies/skill.md
    └── ... (10 total)
```

---

## The Four-Layer DAG

Skills form a strict directed acyclic graph. Edges point **downward only** — no cycles, no upward references.

```
                 ┌─────────────┐
                 │ Meta-Router │  ← Single entry point (router.md)
                 └──────┬──────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  Domain  │  │  Domain  │  │  Domain  │  ← Domain routers
    │  Router  │  │  Router  │  │  Router  │
    └────┬─────┘  └────┬─────┘  └────┬─────┘
         │             │             │
    ┌────┴────┐        ▼        ┌────┴────┐
    ▼         ▼                 ▼         ▼
┌────────┐┌─────────┐     ┌─────────┐┌─────────┐
│Playbook││Primitive│     │Playbook ││Primitive│
└───┬────┘└─────────┘     └───┬─────┘└─────────┘
    │                         │
    ▼ ▼ ▼                     ▼ ▼
  Primitives                Primitives
```

| Layer | What It Does | Edge Rules |
|-------|--------------|------------|
| **Meta-Router** | Single entry point. Routes to domain router(s). Composes multi-domain chains. | Routes to domain routers only. Never directly to playbooks/primitives. |
| **Domain Routers** | Classify intent within a domain → select target skill and mode | `routes_to` playbooks/primitives. Nothing depends on routers. |
| **Playbooks** | Orchestrate multi-step workflows | `depends_on` primitives only. Never reference routers or other playbooks. |
| **Primitives** | Document one Snowflake feature (syntax, params, examples) | Leaf nodes. No outgoing edges. |

### Why a Four-Layer DAG?

- **Single entry point**: Agent always starts at `router.md` — no ambiguity about where to begin
- **Domain separation**: Each domain has its own routing logic; meta-router composes them
- **Dynamic chaining**: Multi-domain intents are composed at runtime, not predefined
- **Traversable**: Agent always knows where it is and what comes next
- **No infinite loops**: Cycles are structurally impossible

---

## Control Flow

### Step 1: Discovery

Agent reads `skill-index.yaml` to discover skills, then `router.md` (meta-router) to begin:

```yaml
# skill-index.yaml
version: "1.0"
entry: router.md

primitives:
  masking-policies:
    domain: data-security

routers:
  data-security:
    routes_to:
      - primitives/masking-policies
      - playbooks/secure-sensitive-data
```

### Step 2: Meta-Router Resolution

The meta-router parses user intent and determines:
- **Single domain** → route to that domain's router
- **Multiple domains** → compose a chain (topologically sorted)

```
User: "Build a pipeline and then create a dashboard"
  │
  ├─ Meta-router detects: data-transformation + app-development
  │
  ├─ Topological sort:
  │   data-transformation produces [tables] → goes first
  │   app-development requires [tables] → goes second
  │
  └─ Chain: [data-transformation, app-development]
```

### Step 3: Domain Routing

Each domain router resolves to one of **three modes**:

| Mode | When | What Happens |
|------|------|--------------|
| **Playbook** | Broad intent matches a workflow | Follow pre-built steps (highest confidence) |
| **Guided** | Moderate intent, no playbook fits | Agent builds a plan, human approves before execution |
| **Reference** | Narrow intent, needs a fact | Direct lookup, no execution |

```
"Secure all my sensitive data"     → Playbook mode (secure-sensitive-data)
"Build me a Streamlit dashboard"   → Guided mode (agent constructs plan)
"What's the syntax for masking?"   → Reference mode (direct lookup)
```

### Step 4: Input Gathering

Inputs are declared with **phases** — gathered only when needed:

```yaml
inputs:
  - name: target_scope
    phase: before_start      # Gathered before execution begins
  - name: protection_strategy
    phase: step_2            # Gathered after classification results are known
```

**Design decision**: Lazy gathering. Ask only what's missing, only when it's needed.

### Step 5: Structured Probes

Before executing, playbooks run **structured probes** — mandatory discovery queries with validation rules:

```yaml
probes:
  - id: existing_policies
    query: "SHOW MASKING POLICIES IN ACCOUNT"
    validate:
      - condition: "count > 100"
        action: warn
        message: "Large number of existing policies"
  - id: role_check
    query: "SELECT CURRENT_ROLE()"
    validate:
      - condition: "result NOT IN ('ACCOUNTADMIN', 'SECURITYADMIN')"
        action: block
        message: "Requires elevated role"
```

Validation actions: `pass` (silent), `warn` (continue with note), `confirm` (require approval), `block` (halt execution).

**Design decision**: Probe before mutate. Never blindly CREATE when something might already exist.

### Step 6: Execution

Execution is tracked as an **append-only thread of events**:

```yaml
thread_id: "thr_abc123"
events:
  - type: chain_started
    domains: [data-transformation, app-development]
    
  - type: phase_started
    domain: data-transformation
    phase_number: 1
    
  - type: routed
    router: data-transformation
    target: playbooks/build-streaming-pipeline
    mode: playbook
    
  - type: playbook_started
    playbook: build-streaming-pipeline
    
  - type: step_started
    step: 1
    primitive: dynamic-tables
    
  # ... execution continues
```

### Step 7: Checkpoints

Execution pauses at checkpoints for human review. Checkpoints have **severity levels**:

| Severity | Behavior | Example |
|----------|----------|---------|
| `info` | Batch-approvable, low risk | "Created staging table" |
| `review` | Requires individual review | "Protection strategy ready" |
| `critical` | Cannot be batched, must approve individually | "About to apply policies to production" |

Every checkpoint offers:

| Option | Meaning |
|--------|---------|
| **approve** | Proceed as proposed |
| **modify** | Adjust and re-present (stays at current step) |
| **abort** | Stop the workflow (triggers compensation rollback) |
| **different-approach** | Re-route to a different skill |

---

## Dynamic Domain Chaining

When user intent spans multiple domains, the meta-router composes a chain at runtime.

### Domain Dependencies

```yaml
# Declared in router.md
domains:
  data-transformation:
    produces: [tables, pipelines]
    requires: []
  data-security:
    requires: [tables]
    produces: [policies, governance]
  app-development:
    requires: [tables]
    produces: [applications]
```

### Example Chain

User: "Build a pipeline, secure it, then build a dashboard"

```
Thread: "Pipeline to secured dashboard"
  │
  ├── Meta-router decomposes: [data-transformation, data-security, app-development]
  │
  ├── Phase 1: data-transformation router → build-streaming-pipeline
  │     ├── (steps 1-6, checkpoints)
  │     └── produces: analytics.order_summary, analytics.daily_metrics
  │
  ├── Phase 2: data-security router → secure-sensitive-data
  │     ├── context: tables = [analytics.order_summary, analytics.daily_metrics]
  │     └── produces: PII_MASK policy applied
  │
  ├── Phase 3: app-development router → build-react-app
  │     ├── context: tables (secured), policies applied
  │     └── produces: dashboard.snowflakeapp.com
  │
  └── Thread complete
```

### Context Handoff

Outputs from earlier phases flow into later phases:

| Phase Produces | Next Phase Consumes As |
|----------------|------------------------|
| Table names | `data_sources`, `target_tables` |
| Policy names | `applied_policies` |
| Service endpoints | `backend_url` |

---

## Thread Model

The **thread** is the top-level execution unit — not the playbook. A single thread can:

- Execute one playbook
- Chain multiple playbooks across domains
- Include agent-constructed plans (guided mode)
- Survive re-routing mid-execution

### The Agent is a Stateless Reducer

```
next_step = f(thread_history)
```

Given the full event history, the agent can always determine what to do next. No in-memory session state. Threads can be paused, serialized, and resumed hours or days later.

---

## Error Handling

Errors are events on the thread, not crashes.

**Expected errors** have documented recovery:

```yaml
expected_errors:
  - pattern: "Insufficient privileges"
    recovery: "Grant CREATE MASKING POLICY to {admin_role}"
    retryable: false
    escalate: true
```

**Unexpected errors** escalate to humans immediately.

**Design decision**: Max 2 retries per step. LLM performance degrades when errors accumulate.

---

## Safety Features

The framework includes comprehensive safety mechanisms:

| Feature | Purpose |
|---------|---------|
| **Structured probes** | Validate environment before execution; can block, warn, or require confirmation |
| **Checkpoint severity** | Three levels (info/review/critical) with batch approval support |
| **Compensation actions** | Rollback SQL for each step; triggered on abort to clean up partial state |
| **Guided mode guardrails** | Max 8 steps, require primitives, prohibited actions (DROP DATABASE, etc.) |
| **Routing confidence** | Score-based routing with clarification when confidence is low |
| **Dry-run mode** | Preview execution without making changes |
| **Multi-account context** | Track and verify account context to prevent cross-account mistakes |
| **Manifest validation** | Detect domain cycles, missing references, stale primitives |

---

## Design Principles (Ranked)

When principles conflict, higher-ranked wins.

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **Deterministic skeleton, LLM at joints** | Predictable paths; reasoning only at defined points |
| 2 | **Knowledge as strict DAG** | No cycles = no infinite loops; each layer testable |
| 3 | **Agent is stateless reducer** | Resumable; no session management |
| 4 | **Factual over advisory** | Primitives say *what*, never *when* (routers decide *when*) |
| 5 | **Lazy context gathering** | Ask late; users answer better with context |
| 6 | **Human-in-the-loop first-class** | Checkpoints are structured events |
| 7 | **Errors are events** | Recovery hints for expected; escalate for unexpected |
| 8 | **Small over comprehensive** | No file >500 lines; LLM performance degrades with length |
| 9 | **Composed over monolithic** | Reference primitives; never duplicate content |
| 10 | **Agent-first structure** | Tables over prose; code blocks for SQL |

---

## What This Is NOT

| Not This | Because |
|----------|---------|
| An agent framework | No LLM runtime, no tool engine, no deployment system |
| A prompt repository | No system prompts or completion templates |
| Code | Structured knowledge only — markdown files for agent consumption |
| A chatbot | Workflows execute steps; they don't just answer questions |

---

## Critical Paths

| User Intent | Flow |
|-------------|------|
| "Protect sensitive data" | `router.md` → `routers/data-security` → `playbooks/secure-sensitive-data` → 5 primitives |
| "Continuously refreshing pipeline" | `router.md` → `routers/data-transformation` → `playbooks/build-streaming-pipeline` → 3 primitives |
| "Web app on Snowflake data" | `router.md` → `routers/app-deployment` → `playbooks/build-react-app` → 1 primitive |
| "Transform, secure, and display" | `router.md` → chain: [data-transformation, data-security, app-development] |

---

## Skill Inventory

### Primitives (10)

| Name | Domain | Purpose |
|------|--------|---------|
| `dynamic-tables` | data-transformation | Incrementally maintained tables |
| `dbt-snowflake` | data-transformation | Deploy dbt projects via `snow dbt` |
| `openflow` | data-transformation | NiFi-based external data ingestion |
| `masking-policies` | data-security | Column-level dynamic masking |
| `row-access-policies` | data-security | Row-level filtering |
| `projection-policies` | data-security | Block columns from SELECT |
| `data-classification` | data-security | Discover PII via `SYSTEM$CLASSIFY` |
| `account-usage-views` | data-security | Governance queries |
| `spcs-deployment` | app-development | Deploy containers to SPCS |
| `streamlit-in-snowflake` | app-development | Native Streamlit apps |

### Domain Routers (3)

| Router | Domain | Decision Space |
|--------|--------|----------------|
| `data-security` | data-security | Classification, policies, auditing, end-to-end protection |
| `data-transformation` | data-transformation | Dynamic tables vs dbt vs OpenFlow, or full pipeline |
| `app-deployment` | app-development | Streamlit vs SPCS, or full React app build |

### Playbooks (3)

| Name | Outcome |
|------|---------|
| `secure-sensitive-data` | Discover PII, apply policies, verify, monitor |
| `build-streaming-pipeline` | Ingestion through transformation with continuous refresh |
| `build-react-app` | Next.js app connected to Snowflake, deployed to SPCS |

---

## Specification Documents

| Document | Purpose |
|----------|---------|
| `spec/standard-skills-library.md` | Canonical spec — principles, architecture, execution model |
| `spec/skill-schema.md` | Field-level schema for skill front-matter |
| `spec/authoring-guide.md` | Templates and checklists for writing new skills |
| `spec/extending-routers.md` | How to add domain routers from external repos |
| `spec/controlled-vocabulary.md` | Domain taxonomy, naming conventions |

# Standard Snowflake Skills Library: Proposal

## Executive Summary

Cortex Code ships AI-agent skills for Snowflake operations. Today, product teams build these skills independently — no shared schema, no routing logic, no editorial oversight. The result: conflicting guidance, ambiguous skill selection, bloated context windows, and advice that advocates for features rather than user outcomes.

The **Standard Snowflake Skills Library** is a methodology for organizing Snowflake agent knowledge as a strict directed acyclic graph (DAG). Skills are structured markdown — not code — with deterministic routing, human-in-the-loop checkpoints, and event-sourced execution. A working implementation exists: 10 primitives, 3 domain routers, 3 playbooks, and a full specification.

This is a documentation product. The problems it solves — conflicting guidance, inconsistent structure, overlapping scope — are documentation problems. They require centralized editorial ownership.

---

## Problem

Product teams ship skills independently. Each team optimizes for their feature. Five problems compound:

| Problem | Example | Impact |
|---------|---------|--------|
| **Conflicting guidance** | `data-governance`, `data-policy`, and `sensitive-data-classification` all cover overlapping ground | "Protect my data" triggers three skills with different recommendations |
| **Ambiguous routing** | "Create a pipeline" could mean dynamic tables, dbt, or OpenFlow | Agent guesses or asks questions it shouldn't need |
| **Bloated skills** | Some exceed 6,000 lines | Context window saturation; agent misses instructions buried deep |
| **Feature advocacy** | Each PM's skill promotes their feature | Nobody builds the skill that says "don't use my feature — use theirs" |
| **Drift** | No single process tracks Snowflake changes across skills | Syntax, defaults, and constraints go stale silently |

The root cause is structural. A decentralized model cannot produce skills optimized for agent reliability and user success. Consistency and neutrality require centralized editorial ownership.

---

## Architecture Proposal

### Core Idea: Knowledge as a Strict DAG

The library organizes all Snowflake agent knowledge into a four-layer directed acyclic graph. Edges point downward only. No cycles. No upward references.

```
               ┌─────────────┐
               │ Meta-Router  │  ← single entry point
               └──────┬───────┘
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
  Primitives           Primitives  ← leaf nodes
```

**Why a DAG?** DAGs are traversable, debuggable, and verifiable. Cycles create infinite loops. Upward edges create hidden coupling. A strict DAG makes the system predictable for both agents and humans. Every layer is independently testable.

### The Four Layers

| Layer | Role | What It Contains | Edge Rules |
|-------|------|-----------------|------------|
| **Meta-Router** | Single entry point. Resolves user intent to domain(s). | Domain keyword matching, confidence scoring, multi-domain chaining logic | Routes to domain routers only. Never directly to playbooks or primitives. |
| **Domain Router** | Classifies intent within a domain. Selects target and mode. | Decision matrices, routing flowcharts, anti-pattern tables for mis-routing | Routes to playbooks and primitives. Nothing depends on routers. |
| **Playbook** | End-to-end workflow with checkpoints. | Ordered steps, each referencing primitives. Probes, compensation actions, expected errors. | References primitives only. Never other playbooks (no nesting). Never routers (already consulted). |
| **Primitive** | Factual reference for one Snowflake concept. | Syntax, parameters, constraints, examples, anti-patterns. | Leaf node. No outgoing edges. |

**Why these specific layers?** The separation enforces a principle the current skills violate: facts and opinions must not mix. Primitives document *what* — syntax, parameters, constraints. They never say *when* to use something. Routers and playbooks decide *when*. This prevents the false confidence that emerges when an LLM reads a skill that simultaneously explains a feature and advocates for it.

### Three Routing Modes

Domain routers don't just point to a target — they select a *mode* that determines execution behavior:

| Mode | Trigger | Behavior | Risk Level |
|------|---------|----------|------------|
| **Playbook** | Broad intent matches a pre-built workflow | Follow pre-authored steps. Highest confidence. | Lowest — plan is tested |
| **Guided** | Moderate intent, no matching playbook | Agent constructs a plan from primitives. Mandatory approval before execution. | Medium — plan is agent-generated |
| **Reference** | Narrow intent, needs a specific fact | Load primitive, answer directly. No execution. | None — read-only |

```
Router
  ├── "Secure all my data end to end"   → Playbook (secure-sensitive-data)
  ├── "Build me a Streamlit dashboard"  → Guided (agent constructs plan)
  └── "What's the syntax for masking?"  → Reference (direct lookup)
```

**Why three modes?** The current system has two failure modes: (1) loading a massive skill for a simple syntax question, and (2) having no structured workflow when the user needs end-to-end guidance. The three-mode split means a syntax question loads ~150 lines of primitive, while a full workflow loads a playbook that orchestrates multiple primitives with checkpoints. Guided mode covers the middle ground — the agent can compose primitives into a plan, but must get human approval first because the plan is agent-generated, not pre-authored.

### Edge Rules and Why They Exist

| Rule | Rationale |
|------|-----------|
| Meta-router never bypasses domain routers | Domain-level decision logic (playbook vs. guided vs. reference) belongs in the domain. The meta-router doesn't know enough to make that call. |
| Playbooks never reference routers | The router was already consulted before the playbook was entered. Referencing it back would create a cycle. |
| Playbooks never reference other playbooks | Nesting creates unbounded depth. If a workflow needs content from another playbook, it should reference the shared primitives directly. |
| Primitives never reference anything | Leaf nodes. Reference material doesn't drive workflows. This makes primitives independently testable and reusable across any number of playbooks. |

### Dynamic Multi-Domain Chaining

User intents often span domains: "Ingest data, secure it, build a dashboard." The meta-router handles this through dependency-based chaining, not predefined combinations.

Each domain declares what it `produces` and `requires`:

```yaml
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

The agent topologically sorts domains at runtime:

```
Intent: "Build a pipeline, secure it, build a dashboard"
  │
  ├── Phase 1: data-transformation (produces tables) — goes first, no dependencies
  ├── Phase 2: data-security (requires tables) — must follow transformation
  └── Phase 3: app-development (requires tables) — must follow transformation
```

Context flows between phases. Table names produced in phase 1 become input to phase 2. Policy names from phase 2 are available in phase 3.

**Why dynamic chaining?** The alternative is enumerating every valid domain combination — which doesn't scale. With dependency declarations, adding a new domain (e.g., cost-operations) means declaring `produces: [cost-reports]` and `requires: [tables]`. The agent figures out where it fits in any chain. The implementation includes explicit `context_mapping` declarations and `outputs` per domain so the handoff between phases is structured, not left to LLM judgment.

### Routing Confidence

The meta-router computes confidence scores before routing. This prevents the agent from silently picking the wrong domain on ambiguous requests.

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| `keyword_match` | 0.3 | Presence of domain keywords |
| `intent_pattern` | 0.4 | Match against intent templates |
| `context_signals` | 0.3 | Session history, data mentioned |

Two thresholds gate routing:
- **confidence_threshold (0.7)**: Below this, ask for clarification instead of routing.
- **ambiguity_threshold (0.2)**: If the top two candidates are within this delta, ask for clarification.

**Why confidence scoring?** "Protect my pipeline" is ambiguous — security or transformation? Without confidence thresholds, the agent guesses. With them, it recognizes ambiguity and asks a structured clarifying question. The implementation includes `routing_ambiguous` events with pre-built clarification options per domain pair.

---

## Execution Model

### Threads: Event-Sourced State

Execution is tracked as an append-only thread of events — not in-memory session state.

```yaml
thread_id: "thr_abc123"
events:
  - type: playbook_started
    playbook: secure-sensitive-data
    inputs: { target_scope: "PROD.CUSTOMER_DATA" }
  
  - type: probes_executed
    results: [{ probe_id: role_check, status: passed }]
  
  - type: step_completed
    step: 1
    result: { pii_found: 4 }
  
  - type: checkpoint_reached
    severity: review
    present: "Found 4 PII columns with high confidence"
    options: [approve, modify, abort, different_approach]
  
  - type: human_response
    choice: approve
```

The agent is a **stateless reducer**: `next_step = f(thread_history)`. Given the full event log, it always knows what to do next. This makes sessions resumable, auditable, and debuggable.

**Why threads are not owned by playbooks.** A thread must survive re-routing, cross-domain transitions, and mid-execution pivots. If a user starts securing data and says "actually, build me a pipeline first," the same thread continues. The thread is the top-level execution unit, not any single playbook.

### Structured Probes: Look Before You Leap

Every playbook declares mandatory probes — discovery queries that run before step 1 and gate execution.

```yaml
probes:
  - id: role_check
    query: "SELECT CURRENT_ROLE()"
    required: true
    validate:
      - condition: "result NOT IN ('ACCOUNTADMIN', 'SECURITYADMIN')"
        action: block
        message: "Requires elevated role"
  - id: existing_policies
    query: "SHOW MASKING POLICIES IN ACCOUNT"
    required: true
    validate:
      - condition: "count > 100"
        action: warn
        message: "Large number of existing policies"
```

Four validation actions: `pass` (silent), `warn` (continue with note), `confirm` (require approval), `block` (halt execution).

**Why mandatory probes?** The current skills sometimes CREATE objects that already exist or operate without the right role. Probes catch this *before* execution starts. The `secure-sensitive-data` playbook, for example, probes for existing masking/row-access/projection policies, verifies the target tables exist, checks scope size (warning at 500+ tables), and validates the current role — all before touching anything.

### Checkpoints: Structured Human Oversight

Checkpoints are pause points with severity levels — not uniform interruptions.

| Severity | Behavior | Use Case |
|----------|----------|----------|
| `info` | Auto-proceed after 3s unless interrupted | Low-risk informational updates |
| `review` | Require explicit approval (default) | Standard checkpoints |
| `critical` | Require individual confirmation | Destructive or irreversible actions |

Every checkpoint offers four options: **approve**, **modify** (stay at current step, re-present after adjustment), **abort** (trigger compensation rollback), and **different-approach** (re-route to a different skill).

**Why severity levels?** The current system interrupts the user identically for "created staging table" and "about to apply policies to production." Severity levels prevent checkpoint fatigue while maintaining strong oversight for high-stakes operations. Batch approval (`approve_remaining`) is available for `review`-level checkpoints but never for `critical`.

### Compensation Actions: Rollback on Abort

Each playbook step that creates or modifies objects declares a compensation action:

```yaml
### Step 3: Create masking policies
Creates:
  - type: masking_policy
    name: "governance.policies.mask_string"
Compensation:
  DROP MASKING POLICY IF EXISTS governance.policies.mask_string;
```

On abort, the agent proposes cleanup using compensation actions from completed steps. The user can accept, reject, or review before anything is dropped.

**Why compensation?** Partial execution leaves orphaned objects — policies half-applied, functions created but unused. Without compensation declarations, the user must manually figure out what was created and clean it up. With them, the agent can propose a precise rollback.

### Guided Mode Guardrails

Guided mode is riskier because the plan is agent-generated. Additional constraints apply:

| Rule | Limit | On Violation |
|------|-------|--------------|
| Max steps | 8 | Refuse plan, suggest breaking into smaller goals |
| Primitive requirement | Every step must reference a primitive | Reject step |
| Prohibited actions | DROP DATABASE, DROP SCHEMA, GRANT OWNERSHIP, ALTER ACCOUNT | Block — these require a playbook |
| Checkpoint frequency | After every step | Mandatory (not configurable) |

**Why these limits?** Agent-generated plans are prone to over-complexity and missing safety checks. The 8-step limit forces decomposition. The primitive requirement ensures every step is grounded in factual reference material. Prohibited actions prevent the agent from executing irreversible operations without a pre-reviewed playbook.

### Dry-Run Mode

Users can preview what a playbook will do without executing anything. Probes still run (need real environment state), but SQL is planned, not executed. A summary shows total impact:

```yaml
- type: dry_run_summary
  would_create: { masking_policies: 4, row_access_policies: 1 }
  would_modify: { tables: 25, columns: 47 }
  estimated_duration: "15-30 minutes"
  estimated_compute: "~2 credits"
```

### Error Handling

Errors are events on the thread, not crashes. A global error category system provides default handling:

| Category | Example Patterns | Default Behavior |
|----------|-----------------|-----------------|
| `permission` | "Insufficient privileges", "Access denied" | Not retryable. Escalate with grant hint. |
| `object_exists` | "already exists", "duplicate" | Retryable. Suggest CREATE OR REPLACE. |
| `transient` | "timeout", "connection" | Retryable (3x). Exponential backoff. |
| `syntax` | "syntax error", "invalid" | Not retryable. Escalate. |

Step-specific expected errors override global categories. Unknown errors escalate immediately. Max 2 retries per step.

---

## Discovery: How the Agent Enters

The agent starts with exactly two files:

1. **`skill-index.yaml`** — indexes every skill with type, domain, and relationships. The source of truth for *what exists*.
2. **`router.md`** — the meta-router. The source of truth for *how to enter*.

```yaml
# skill-index.yaml
entry: router.md

primitives:
  masking-policies:
    domain: data-security
  dynamic-tables:
    domain: data-transformation

routers:
  data-security:
    routes_to:
      - primitives/masking-policies
      - playbooks/secure-sensitive-data

playbooks:
  secure-sensitive-data:
    depends_on: [data-classification, masking-policies, row-access-policies]
```

The agent reads the manifest to discover skills, reads the meta-router to resolve intent, then loads only the specific router/playbook/primitive(s) needed. A syntax question loads ~150 lines. A full security workflow loads a playbook and its referenced primitives on demand. The 500-line-per-file limit ensures no single load saturates the context window.

### Manifest Validation

The meta-router validates the library on load:
- **Cycle detection**: Circular `produces`/`requires` dependencies would cause infinite routing loops.
- **Reference integrity**: All `routes_to` paths point to real files. All `depends_on` primitives exist.
- **Staleness warnings**: Primitives with `last_reviewed` dates older than 180 days trigger warnings.

---

## How This Solves the Problems

| Problem | Mechanism |
|---------|-----------|
| **Conflicting guidance** | Routers contain decision logic. Primitives contain facts. One authoritative recommendation per situation. The data-security router explicitly replaces the overlapping `data-governance`, `data-policy`, and `sensitive-data-classification` skills. |
| **Ambiguous routing** | Single entry point (meta-router) with confidence scoring. "Create a pipeline" goes through the data-transformation router, which uses a decision matrix (data location, freshness, existing tooling) to deterministically select dynamic tables vs. dbt vs. OpenFlow vs. the full pipeline playbook. |
| **Bloated skills** | No file exceeds 500 lines. Primitives average 100-180 lines. Agent loads only what's needed per routing mode. |
| **Feature advocacy** | Neutral editorial ownership. The data-transformation router recommends dynamic tables *or* dbt *or* OpenFlow based on user need. The anti-patterns section explicitly warns against mis-routing to the wrong tool. |
| **Drift** | Every primitive has `tested_on` (Snowflake version, date, account type) and `last_reviewed` metadata. Staleness warnings fire automatically. Updating one primitive propagates everywhere — playbooks reference, not duplicate. |

---

## What Currently Exists

The implementation is not theoretical. The library contains:

| Type | Count | Coverage |
|------|-------|----------|
| **Primitives** | 10 | dynamic-tables, dbt-snowflake, openflow, masking-policies, row-access-policies, projection-policies, data-classification, account-usage-views, spcs-deployment, streamlit-in-snowflake |
| **Domain Routers** | 3 | data-security (6 routing targets), data-transformation (4 targets), app-deployment (3 targets) |
| **Playbooks** | 3 | secure-sensitive-data (6 steps, 5 primitives), build-streaming-pipeline (6 steps, 3 primitives), build-react-app (5 steps, 1 primitive) |
| **Spec documents** | 5 | Full specification, skill schema, authoring guide, controlled vocabulary, router extension guide |

All 12 recommended framework updates from the gap analysis have been implemented: explicit context mapping, mandatory probes, compensation actions, thread compaction, guided mode guardrails, routing confidence, error categories, dry-run mode, checkpoint severity, domain cycle validation, staleness tracking, and multi-account context.

### Critical Paths (Proven)

| User Intent | Path | Skills Loaded |
|-------------|------|---------------|
| "Protect sensitive data" | meta-router → data-security router → secure-sensitive-data playbook | 1 router + 1 playbook + 5 primitives on demand |
| "Continuously refreshing pipeline" | meta-router → data-transformation router → build-streaming-pipeline playbook | 1 router + 1 playbook + 3 primitives on demand |
| "What's the syntax for masking?" | meta-router → data-security router → masking-policies primitive (reference mode) | 1 router + 1 primitive (~180 lines) |
| "Transform, secure, and display" | meta-router → chain: [data-transformation, data-security, app-development] | Phased loading across 3 domains |

---

## Known Gaps

The gap analysis identified issues across maintainability, usability, and reliability. Most have been addressed in the implementation. Key remaining open items:

| Gap | Status | Notes |
|-----|--------|-------|
| Thread persistence | Open | Where threads are stored, TTL, retrieval — requires joint design with Cortex Code CLI team |
| Idempotency declarations | Open | Primitives don't declare whether operations can safely re-run |
| Validation tooling | Open | No linter or test harness for routing decisions before shipping |
| Deprecation lifecycle | Open | No `active`/`deprecated`/`sunset` status field for skills |
| Domain overlap arbitration | Partially addressed | Confidence scoring handles ambiguity, but explicit conflict resolution rules for specific domain pairs are not yet defined |
| Partial playbook execution | Open | No `start_at_step` parameter for users who've already completed early steps |

---

## Process: Skills as Documentation

The library is maintained like documentation, not code:

1. **Domain taxonomy** — controlled vocabulary defines domains and their boundaries
2. **Primitive authoring** — factual reference, strict schema, no opinions
3. **Router authoring** — decision logic, deterministic matrices, anti-pattern tables for mis-routing
4. **Playbook authoring** — end-to-end workflows composing primitives with probes, checkpoints, and compensation
5. **Editorial review** — consistency, neutrality, cross-domain conflict resolution

A submission checklist enforces quality: front-matter schema compliance, DAG rule adherence, 500-line limit, no duplicated content, runnable examples, manifest updates, and staleness metadata.

### Extension Model

External teams can add domains without modifying the core library. The `extending-routers.md` spec defines the process:

1. Create a router following the schema
2. Register it in the meta-router's `domains` block with `produces`/`requires`
3. Add entries to `skill-index.yaml`
4. External packages provide `manifest-fragment.yaml` files that merge into the main manifest

---

## Open Questions

| Question | Considerations |
|----------|----------------|
| **Maintainer ownership** | Who staffs this? The library requires a funded maintainer with editorial authority and cross-team neutrality. Without one, it drifts like the current skills. |
| **Runtime integration** | How does the Cortex Code CLI agent discover and load skills from the library at runtime? The manifest and router are designed for it, but the integration point needs joint design. |
| **Migration path** | How do existing bundled skills transition to the library structure? Incremental migration (new skills use library, old skills migrated over time) vs. big-bang cutover. |
| **Versioning contract** | Library-level versioning exists (`skill-index.yaml` version field). Per-skill versioning was identified as a gap. What's the backward compatibility promise when a primitive changes? |

---

## Recommendation

Adopt the Standard Snowflake Skills Library as the authoritative methodology for Snowflake agent skills. Fund a dedicated maintainer with editorial authority. Migrate existing bundled skills incrementally.

The implementation proves the concept works. Ten primitives, three routers, three playbooks, and a full specification — all conforming to strict schemas, DAG rules, and the 500-line limit. The architecture solves the five identified problems through structural constraints, not process mandates.

The decentralized model will not produce skills optimized for agent and user success. Centralized editorial ownership will.

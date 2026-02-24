# Standard Skills Library — Specification

A methodology for building production-grade, LLM-orchestrated workflows on Snowflake.

Skills are structured knowledge — organized as a strict DAG, designed for agent traversal, and executed through a thread-based model that supports pause, resume, human interaction, and error recovery.

---

## Principles

These are the foundational beliefs that shape every design decision in the library. They are ordered by importance. When principles conflict, higher-ranked principles win.

### 1. Deterministic skeleton, LLM at the joints

The agent follows a largely deterministic path through the skill DAG. LLM reasoning happens at defined decision points: resolving user intent (routers), gathering missing context (inputs), and adapting to feedback (checkpoints). 

### 2. Knowledge as a strict DAG

Skills compose in one direction only. Routers resolve intent downward to playbooks or primitives. Playbooks orchestrate steps downward through primitives. Primitives are leaf nodes. No cycles, no upward edges. Each layer is independently testable.

Why: DAGs are traversable, debuggable, and verifiable. Cycles create infinite loops. Upward edges create hidden coupling. A strict DAG makes the system predictable for both agents and humans.

### 3. The agent is a stateless reducer

Given the full history of events (the thread), the agent can always determine the next step. The thread is the single source of truth for what has happened, what the user decided, what failed, and what comes next.

### 4. Factual over advisory

Primitives document what something is and how it works. They never recommend when to use it. Recommendations live in routers (decision logic) and playbooks (workflow design). Reference material is neutral; decision logic is opinionated.

When facts and opinions mix, LLMs inherit false confidence. Separating them lets the routing layer make informed decisions without contaminated reference material.

### 5. Lazy context, phased gathering

Declare what information is needed and when. Infer from the user's message and session context first. Ask only for what's missing. Prefer structured choices over open-ended questions. Gather late.

 Premature questions frustrate users and generate unreliable answers. Phased gathering ensures inputs are requested when the agent (and the user) have enough context to answer well.

### 6. Human-in-the-loop is a first-class operation

Pausing for human review is a structured event in the execution thread. Checkpoints define what to present, what options to offer, and how to proceed based on the response. Human input is just another event the reducer processes.

Production workflows on real data require human oversight. Treating it as structured rather than ad-hoc makes it reliable, auditable, and resumable.

### 7. Errors are events, not crashes

When a step fails, the error becomes a context-enriching event on the thread. Expected errors have recovery hints. Unexpected errors escalate to humans. The agent adapts or stops. It does not spin in retry loops.

Snowflake operations fail for predictable reasons. Encoding these as structured events lets the agent recover or provide actionable guidance instead of retrying blindly.

### 8. Small over comprehensive

No skill file exceeds 500 lines. No playbook exceeds approximately 20 steps. Scope is constrained to keep the LLM's context window manageable and its performance high. Expand scope only when quality can be maintained.

Why: LLM performance degrades with context length. Smaller, focused skills produce better agent behavior than large, comprehensive ones that push the context window.

### 9. Composed over monolithic

Playbooks reference primitives; they don't duplicate them. Routers reference playbooks and primitives; they don't inline their content. Every piece of knowledge exists in exactly one place. Composition happens through references.

Why? Duplication drift. When a Snowflake feature changes, updating one primitive propagates everywhere. Duplicated content creates contradictions.

### 10. Agent-first structure

Content is structured for LLM parsing: tables over paragraphs, code blocks for all SQL, deterministic decision logic over prose, structured front-matter for machine-readable metadata. Humans can read it. Agents can parse it.

Why: Prose is ambiguous. Tables, code blocks, and structured YAML are not. Agent-first structure reduces parsing errors and improves routing accuracy.

---

## Architecture

### The Skill DAG

The library is a directed acyclic graph with four layers. Edges point downward only.

```
               ┌─────────────┐
               │ Meta-Router  │  ← single entry point
               └──────┬───────┘
                      │
           ┌──────────┼──────────┐    (may chain multiple)
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

#### Meta-Router — Entry point

The meta-router is the single entry point for the entire library. It sits at the root of the DAG and resolves user intent to one or more domain routers. It lives at the repo root as `router.md`.

The meta-router has two modes:

**Single-domain routing.** The user's intent maps to one domain. The meta-router selects the domain router, and traversal continues as normal.

**Dynamic chaining.** The user's intent spans multiple domains (e.g., "ingest data, transform it, and build a dashboard"). The meta-router decomposes the intent into an ordered sequence of domain routers. Ordering is determined by declared domain dependencies — domains that produce outputs another domain needs come first.

The meta-router declares each domain with `produces` and `requires`:

```yaml
domains:
  data-transformation:
    router: routers/data-transformation
    produces: [tables, pipelines]
  data-security:
    router: routers/data-security
    requires: [tables]
    produces: [policies, governance]
  app-deployment:
    router: routers/app-deployment
    requires: [tables]
    produces: [applications]
```

When the agent detects a multi-domain intent, it:
1. Identifies the required domains
2. Topologically sorts them using `requires`/`produces` (domains that produce what others require go first)
3. Chains the domain routers in that order
4. Context produced by earlier phases flows into later phases

This is dynamic composition — the meta-router doesn't predefine every possible chain. Adding a new domain means declaring its `produces`/`requires`, and the agent figures out ordering at runtime.

The meta-router never routes directly to a playbook or primitive. It always goes through a domain router. The domain router makes the narrow vs. broad decision.

#### Domain Routers — Decision time

Domain routers resolve user intent within a specific domain to a target skill using structured decision logic (decision matrices, flowcharts, conditional trees). A router declares `routes_to` — the set of skills it can select. Nothing depends on a router.

A router never executes anything. It classifies intent and points to the right skill.

#### Playbooks — Execution time

Playbooks are end-to-end workflows. They compose a sequence of steps, each referencing one or more primitives. A playbook declares `depends_on` — the primitives it composes. Playbooks never reference routers (already consulted before entry) or other playbooks (no nesting).

A playbook is a plan. Its companion execution thread (see below) tracks how that plan runs.

#### Primitives — Reference material

Primitives are factual reference: syntax, parameters, constraints, runnable examples, and anti-patterns for a single Snowflake concept. They are leaf nodes with no outgoing edges.

A primitive documents what exists and how it works. It never tells the agent when to use it.

#### Edge rules

| From | To | Field | Allowed |
|------|----|-------|---------|
| Meta-Router | Domain Router | `domains[].router` | Yes |
| Meta-Router | Playbook or Primitive | — | No (always through a domain router) |
| Domain Router | Primitive | `routes_to` | Yes |
| Domain Router | Playbook | `routes_to` | Yes |
| Domain Router | Domain Router | — | No |
| Playbook | Primitive | `depends_on` | Yes |
| Playbook | Router | — | No |
| Playbook | Playbook | — | No |
| Primitive | anything | — | No (leaf) |

Why no upward or lateral edges: A playbook never references a router because the router was already consulted before the playbook was entered. A playbook never references another playbook because nesting creates unbounded depth. A primitive never references a playbook because reference material doesn't drive workflows. The meta-router never bypasses domain routers because domain-level decision logic (playbook vs. guided vs. reference) belongs in the domain. These constraints prevent cycles and make each layer independently testable.

### Discovery

The agent starts with two files:

1. **`router.md`** (repo root) — the meta-router. The single entry point. Declares all domains, their dependency relationships, and routing parameters.
2. **`skill-index.yaml`** — indexes every skill with its type, domain, and relationships. The source of truth for what exists.

```yaml
# skill-index.yaml
version: "1.0"
entry: router.md

primitives:
  masking-policies:
    domain: data-security

routers:
  data-security:
    domain: data-security
    routes_to:
      - primitives/data-classification
      - playbooks/secure-sensitive-data

playbooks:
  secure-sensitive-data:
    domain: data-security
    depends_on: [data-classification, masking-policies, row-access-policies]
```

The manifest is the source of truth for what exists. The meta-router is the source of truth for how to enter. Individual skill files are the source of truth for their content.

### Agent Traversal

```
1. Read skill-index.yaml → discover skills, domains, relationships
2. Read router.md (meta-router) → resolve user intent to domain(s)
   ├── Single domain → one domain router
   └── Multi-domain  → ordered chain of domain routers (topological sort)
3. For each domain router in the chain:
   a. Read the domain router
   b. Router resolves to one of three modes:
      ├── Playbook (broad intent) → follow a pre-built plan
      ├── Guided  (moderate intent) → agent constructs a plan from primitive content
      └── Reference (narrow intent) → direct lookup, no execution
   c. Gather inputs (infer first, ask only what's missing)
   d. Probe the environment (discover existing state before acting)
   e. Execute
   f. Context produced by this phase carries forward to the next
4. If requirements change mid-execution:
   → Re-route: consult the meta-router with updated context, continue the same thread
```

Steps 3c and 3d are the **pre-execution phase**: inputs are gathered and the environment is probed before any playbook step runs. Probing discovers what already exists (policies, tables, roles, configurations) so the agent doesn't collide with prior state. The sequence is always: **gather → probe → execute.** This phase repeats for each domain in a chain.

#### Three routing modes

**Playbook mode.** The user's intent matches a pre-built workflow. The agent follows the playbook's steps, referencing primitives at each step. This is the highest-confidence path — the plan is pre-authored, tested, and validated.

**Guided mode.** The user's intent requires execution, but no playbook covers it. The agent reads one or more primitives, constructs a lightweight execution plan, and presents that plan to the human for approval before executing anything. Guided mode is the escape hatch for the middle ground between "I need a fact" and "I need a full workflow."

Guided mode is riskier than playbook mode because the plan is agent-generated, not pre-authored. The mandatory approval checkpoint is the guardrail. The human sees the proposed steps and can approve, modify, or reject before any action is taken.

**Reference mode.** The user needs a specific fact — syntax, parameters, constraints. The agent loads the primitive and answers directly. No thread, no execution, no checkpoints.

The router determines the mode based on intent:

```
Router
  ├── "Secure all my data end to end"  → Playbook (broad, matches secure-sensitive-data)
  ├── "Build me a Streamlit dashboard"  → Guided (moderate, no playbook, but streamlit primitive has content)
  └── "What's the syntax for masking?"  → Reference (narrow, just needs the fact)
```

#### Cross-domain execution

A user's goal may span multiple domains: "ingest data from HubSpot, transform it, build a dashboard." The meta-router detects multiple domains in the intent and dynamically composes a chain.

**How chaining works:**

1. The meta-router identifies the required domains from the user's intent
2. It topologically sorts them using `requires`/`produces` declarations:
   - `data-transformation` produces `[tables, pipelines]` — no requirements, goes first
   - `app-deployment` requires `[tables]` — depends on data-transformation, goes second
3. The agent executes each phase in order, carrying context forward

```
Thread: "Get HubSpot data into a live dashboard"
  │
  ├── Meta-router decomposes: [data-transformation, app-deployment]
  │
  ├── Phase 1: data-transformation router → build-streaming-pipeline playbook
  │     ├── (steps 1-6, checkpoints, completion)
  │     └── produces: analytics.order_summary table
  │
  ├── Phase 2: app-deployment router → build-react-app playbook
  │     ├── context from phase 1: data_sources = analytics.order_summary
  │     └── (steps 1-5, checkpoints, completion)
  │
  └── Thread complete
```

**Context handoff between phases.** The meta-router's `produces`/`requires` declarations tell the agent what kind of context flows between phases. The agent doesn't need rigid field mappings — it carries the concrete outputs from one phase (table names, policy names, service endpoints) and maps them to the next phase's inputs. The declarations are structured hints, not contracts:

- Phase 1 produced `tables` → the agent knows the output tables from the pipeline
- Phase 2 requires `tables` → the agent maps those tables to the `data_sources` input of the app playbook

**Chaining is dynamic, not predefined.** The meta-router doesn't enumerate every possible combination. It declares domain dependencies, and the agent composes chains at runtime. Adding a new domain means declaring its `produces` and `requires` — the agent figures out where it fits in any chain.

Each phase is a self-contained routing decision. The thread accumulates the full history across phases. The agent's stateless reducer reads the entire thread and always knows where it is — whether that's mid-playbook, between phases, or recovering from a re-route.

The thread is not owned by a single domain or playbook. It survives re-routing, cross-domain transitions, and mid-execution pivots.

---

## Execution Model

The skill DAG defines **what** to do. The execution model defines **how doing it is tracked**. These are separate concerns. A playbook is a static plan. An execution thread is the live record of a session.

### Threads

A thread is an ordered list of events representing everything that has happened during an execution session. It is the single source of truth for execution state — and it is the top-level execution unit, not the playbook.

A single thread may encompass:
- **One playbook execution** — the common case
- **Multiple playbooks or primitives in sequence** — cross-domain workflows
- **Ad-hoc execution constructed from primitives** — guided mode, no pre-built playbook

```yaml
thread_id: "thr_abc123"
status: running | paused | completed | failed
events:
  - type: playbook_started
    playbook: secure-sensitive-data
    timestamp: "2026-02-22T10:00:00Z"
    inputs:
      target_scope: "PROD.CUSTOMER_DATA"
      admin_role: "SECURITYADMIN"

  - type: step_started
    step: 1
    primitive: data-classification

  - type: step_completed
    step: 1
    result:
      classified_columns: 12
      pii_found: 4
      high_confidence: ["email", "ssn", "phone", "address"]

  - type: checkpoint_reached
    after_step: 1
    present: "Found 4 PII columns with high confidence."
    options:
      - id: approve
        description: "Proceed with these classifications"
      - id: modify
        description: "Adjust before continuing"
      - id: abort
        description: "Stop here"

  - type: human_response
    checkpoint_after_step: 1
    choice: approve
    comment: "Looks good, proceed"

  - type: step_started
    step: 2
```

The thread is append-only. Events are never modified or deleted. The agent reconstructs its understanding of "where am I" by reading the full thread — it is a stateless reducer over these events.

#### Why threads are not owned by playbooks

A thread must survive re-routing, cross-domain transitions, and mid-execution pivots. If the user starts with `secure-sensitive-data` and then says "now help me build a pipeline for this data," the same thread continues — the agent consults the data-transformation router and appends new events. If the user is in guided mode building a Streamlit app and realizes they need SPCS instead, the thread captures the re-route and continues.

Tying threads to playbooks would force the agent to abandon history every time the path changes. The thread preserves full history across any number of routing decisions, playbooks, and ad-hoc steps.

### Events

Every meaningful thing that happens is an event on the thread.

#### Core events

| Event Type | When It Occurs | Key Fields |
|-----------|----------------|------------|
| `playbook_started` | A playbook begins execution | `playbook`, `inputs`, `account_context` |
| `probes_executed` | All pre-execution probes completed | `results[]`, `warnings[]`, `blocked` |
| `probe_checkpoint` | Probes surfaced warnings requiring confirmation | `warnings[]`, `options` |
| `step_started` | A step begins execution | `step`, `primitive` |
| `step_completed` | A step finishes successfully | `step`, `result`, `created_objects[]` |
| `step_failed` | A step encounters an error | `step`, `error`, `error_category`, `recovery_hint` |
| `step_skipped` | A conditional step was determined unnecessary | `step`, `reason` |
| `checkpoint_reached` | Execution pauses for human review | `after_step`, `severity`, `present`, `options` |
| `human_response` | Human responds to a checkpoint | `choice`, `comment` (optional) |
| `input_gathered` | A phased input is collected mid-execution | `name`, `value`, `phase` |
| `error_escalated` | An unrecoverable error is escalated to a human | `step`, `error`, `context` |
| `cleanup_proposed` | Abort triggered, agent proposes rollback | `orphaned_objects[]`, `compensation_actions[]` |
| `cleanup_executed` | Compensation actions were run | `cleaned[]`, `failed[]` |
| `playbook_completed` | All steps in a playbook finished | `playbook`, `summary`, `created_objects[]` |
| `phase_summary` | Thread compaction summarized a completed phase | `phase`, `domain`, `inputs`, `outputs`, `steps_completed` |
| `thread_completed` | The user's goal is fully resolved | `summary` |
| `thread_aborted` | Human or error halted the session | `reason`, `at_step`, `cleanup_status` |

#### Navigation events

| Event Type | When It Occurs | Key Fields |
|-----------|----------------|------------|
| `chain_started` | Meta-router decomposed a multi-domain intent into a sequence | `domains[]`, `order_rationale` |
| `phase_started` | A new domain phase begins within a chain | `domain`, `phase_number`, `context_from_previous` |
| `phase_completed` | A domain phase finished | `domain`, `outputs` |
| `context_mapped` | Outputs from previous phase mapped to current phase inputs | `mappings[]` |
| `routed` | Domain router resolved intent to a target skill | `router`, `target`, `mode`, `confidence`, `alternatives[]` |
| `routing_ambiguous` | Intent unclear, clarification needed | `top_candidates[]`, `clarification_options` |
| `rerouted` | Requirements changed, agent pivoted to a different skill or expanded the chain | `reason`, `from`, `to` |
| `plan_proposed` | Agent constructed an ad-hoc plan in guided mode | `steps[]`, `primitives[]` |
| `plan_rejected` | Agent-generated plan exceeded guardrails | `reason`, `message`, `options` |
| `plan_approved` | Human approved a proposed plan | `modifications` (optional) |
| `environment_probed` | Agent ran a discovery query to understand current state | `query`, `result` |

#### Dry-run events

| Event Type | When It Occurs | Key Fields |
|-----------|----------------|------------|
| `step_planned` | Dry-run: what a step would do (replaces step_started/completed) | `step`, `action`, `would_execute[]`, `would_create[]`, `estimated_duration` |
| `dry_run_summary` | Dry-run complete, showing total impact | `would_create`, `would_modify`, `estimated_duration`, `estimated_compute`, `options` |

#### Validation events

| Event Type | When It Occurs | Key Fields |
|-----------|----------------|------------|
| `staleness_warning` | Primitive hasn't been reviewed within threshold | `primitive`, `last_reviewed`, `days_stale`, `message`, `options` |
| `validation_error` | Manifest validation failed (cycles, missing refs) | `check`, `message`, `resolution` |

#### Conditional steps

Not every playbook step applies to every situation. Step 4 of `secure-sensitive-data` ("Create row access policies") is conditional — only needed if the protection strategy includes row-level filtering. When the agent determines a step doesn't apply, it emits a `step_skipped` event with a reason and proceeds. The step is recorded on the thread (auditable) but no action is taken.

```yaml
- type: step_skipped
  step: 4
  reason: "No columns flagged for row-level protection in the approved strategy"
```

#### Re-routing

When requirements change mid-execution, the agent doesn't crash or restart. It appends a `rerouted` event and continues:

```yaml
- type: rerouted
  reason: "User needs external API access — Streamlit cannot support this"
  from: primitives/streamlit-in-snowflake
  to: primitives/spcs-deployment
```

Re-routing is a normal event on the thread. The stateless reducer reads it and proceeds from the new target. The full history of what was tried and why it changed is preserved.

For cross-domain re-routing (the user's goal expands into a new domain), the agent consults the meta-router with updated context. The meta-router may add new domains to the chain or reorder them. This is also a `rerouted` event — the thread captures the expanded scope.

```yaml
- type: rerouted
  reason: "User wants to add data protection to the pipeline output"
  from: "single-domain: data-transformation"
  to: "chain: [data-transformation (completed), data-security]"
```

Checkpoint options should always include an escape hatch for this: an option like "This approach doesn't fit my requirements" that triggers the agent to re-evaluate routing with updated context.

### Guided Mode Execution

When no playbook matches the user's intent, the agent enters guided mode. Guided mode is riskier than playbook mode — the plan is agent-generated, not pre-authored — so additional guardrails apply.

#### Guardrails

| Rule | Limit | On Violation |
|------|-------|--------------|
| Max steps | 8 | Emit `plan_rejected`, suggest breaking into smaller goals |
| Primitive requirement | Every step must reference a primitive | Reject step without primitive |
| Prohibited actions | DROP DATABASE, DROP SCHEMA, GRANT OWNERSHIP, ALTER ACCOUNT | Block — requires playbook |
| Checkpoint frequency | After every step | Mandatory (not configurable in guided mode) |

#### Sequence

1. The agent reads one or more primitives relevant to the goal
2. The agent probes the environment (probes are mandatory, not optional)
3. The agent constructs an execution plan: a numbered list of steps, each mapped to primitive content
4. The agent validates the plan against guardrails
5. If valid, the agent emits a `plan_proposed` event and pauses at a **mandatory checkpoint**
6. The human reviews the plan and approves, modifies, or rejects
7. On approval, the agent executes step by step, with checkpoints after every step

#### Plan rejection

If the plan exceeds guardrails:

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

#### Approved plan

```yaml
- type: plan_proposed
  goal: "Build an internal dashboard showing sales pipeline metrics"
  steps:
    - step: 1
      action: "Scaffold Streamlit app with snowflake.yml"
      primitive: streamlit-in-snowflake
    - step: 2
      action: "Create SQL queries for pipeline metrics"
      primitive: streamlit-in-snowflake
    - step: 3
      action: "Build dashboard layout with filters and charts"
      primitive: streamlit-in-snowflake
    - step: 4
      action: "Deploy to Snowflake"
      primitive: streamlit-in-snowflake
  options:
    - id: approve
      description: "Proceed with this plan"
    - id: modify
      description: "Adjust the plan before starting"
    - id: abort
      description: "Don't proceed"
```

The mandatory approval checkpoint before execution is a critical guardrail. The human sees exactly what the agent intends to do. Combined with step-by-step checkpoints during execution, this makes guided mode safe for production use.

### Checkpoints

Checkpoints are structured pause points where the agent presents results and waits for human direction. In playbook mode, they are defined in the playbook. In guided mode, the agent places them after every step.

A checkpoint declares:

| Field | Purpose |
|-------|---------|
| `after_step` | Which step triggers this checkpoint |
| `severity` | `info`, `review`, or `critical` — determines pause behavior |
| `present` | What to show the human (results, summary, proposed plan) |
| `options` | Structured choices with `id` + `description` |

#### Checkpoint severity levels

| Level | Behavior | Use When |
|-------|----------|----------|
| `info` | Log event, auto-proceed after 3s unless user intervenes | Low-risk informational updates |
| `review` | Pause, require explicit approval (default) | Standard checkpoints |
| `critical` | Pause, require typed confirmation phrase | Destructive or irreversible actions |

The agent does not proceed past `review` or `critical` checkpoints until a `human_response` event appears on the thread. `info` checkpoints auto-proceed but can be interrupted.

#### Batch approval

To reduce checkpoint fatigue, users can select `approve_remaining` to approve all subsequent `review`-level checkpoints. This does not apply to `critical` checkpoints — those always require individual confirmation.

#### Checkpoint options are dynamic

The playbook defines *where* checkpoints occur. The *options* presented at each checkpoint are generated by the agent based on what actually happened in the step. Every checkpoint must include at minimum:

- **approve** — proceed as proposed
- **approve_remaining** — approve this and all subsequent `review`-level checkpoints
- **modify** — adjust before continuing (the agent stays in the current step scope)
- **abort** — stop the workflow entirely
- **different-approach** — re-evaluate routing (the re-routing escape hatch)

Beyond these, the agent should add context-specific options when relevant. For example, after classification, an option like "include medium-confidence columns" is more helpful than a generic "modify."

#### Checkpoints can cycle

When the human chooses "modify," the agent does more work within the same step and re-presents at the checkpoint. The step is not marked complete until the human approves. A checkpoint may fire multiple times for the same step — each occurrence is an event on the thread with updated `present` content. This handles the common case where the user reviews results, requests adjustments, and reviews again.

### Error Handling

Errors are categorized and handled systematically. The agent never spins in retry loops — it either recovers quickly or escalates.

#### Error categories

Global error categories provide default handling. Step-specific `expected_errors` override these.

| Category | Patterns | Retryable | Default Recovery |
|----------|----------|-----------|------------------|
| `permission` | "Insufficient privileges", "Access denied" | No | Escalate with role grant instructions |
| `object_exists` | "already exists", "duplicate" | Yes | Use CREATE OR REPLACE |
| `object_not_found` | "does not exist", "not found" | No | Verify object name, escalate |
| `transient` | "timeout", "connection", "temporarily unavailable" | Yes (3x) | Exponential backoff |
| `resource` | "warehouse.*suspended", "quota exceeded" | Yes (2x) | Resume warehouse or wait |
| `syntax` | "syntax error", "invalid" | No | Review SQL, escalate |
| `conflict` | "concurrent", "modified by", "locked" | Yes (2x) | Linear backoff |

#### Error matching priority

1. Step-specific `expected_errors` (exact match)
2. Primitive-specific `expected_errors`
3. Global error categories (pattern match)
4. Unknown → escalate immediately

#### Step-specific expected errors

Steps can override global categories:

```yaml
- step: 3
  primitive: masking-policies
  expected_errors:
    - pattern: "Insufficient privileges"
      recovery: "Grant CREATE MASKING POLICY to {admin_role}"
      retryable: false
      escalate: true
    - pattern: "already exists"
      recovery: "Use CREATE OR REPLACE syntax"
      retryable: true
```

When an expected error occurs, the agent:
1. Logs a `step_failed` event with the error, category, and recovery hint
2. If `retryable: true` — attempts the recovery and retries (max per category)
3. If `retryable: false` — escalates to the human via an `error_escalated` event

**Unexpected errors** are anything not in the expected list or global categories. The agent logs the error and escalates immediately. It does not attempt to interpret or retry unknown failures.

### Compensation and Rollback

When execution is aborted (user choice or unrecoverable error), the agent proposes cleanup for objects created during the session.

#### Tracking created objects

Each `step_completed` event includes `created_objects`:

```yaml
- type: step_completed
  step: 3
  result: { policies_created: 2 }
  created_objects:
    - type: masking_policy
      name: "PII_EMAIL_MASK"
      fqn: "MYDB.POLICIES.PII_EMAIL_MASK"
    - type: masking_policy
      name: "PII_PHONE_MASK"
      fqn: "MYDB.POLICIES.PII_PHONE_MASK"
```

#### Cleanup proposal

On abort, the agent proposes rollback:

```yaml
- type: cleanup_proposed
  orphaned_objects:
    - type: masking_policy
      name: "PII_EMAIL_MASK"
      created_in_step: 3
      compensation: "DROP MASKING POLICY IF EXISTS MYDB.POLICIES.PII_EMAIL_MASK"
    - type: masking_policy
      name: "PII_PHONE_MASK"
      created_in_step: 3
      compensation: "DROP MASKING POLICY IF EXISTS MYDB.POLICIES.PII_PHONE_MASK"
  options:
    - id: cleanup
      description: "Run compensation actions to remove created objects"
    - id: keep
      description: "Keep objects — I'll handle cleanup manually"
    - id: review
      description: "Show me what was created before deciding"
```

The human decides whether to run cleanup. The agent never automatically deletes objects without confirmation.

### Pause and Resume

Any checkpoint or escalation event pauses the thread. Resuming is straightforward:

1. Load the serialized thread
2. Pass it to the agent (stateless reducer)
3. The agent reads the full event history and determines the next step
4. Execution continues from where it left off

Because the agent is stateless, there is no in-memory session to maintain. The thread can be resumed minutes, hours, or days later by any agent instance. This is what makes the system durable.

### Thread Compaction

Append-only threads can exceed context windows. Thread compaction summarizes completed phases while preserving audit trail.

#### When compaction occurs

1. After each phase completes in a multi-domain chain
2. After N events (configurable, default 50)
3. On explicit user request

#### What gets preserved

- Last 10 events in full detail
- All checkpoint events with human responses
- All error events
- Current step context
- Phase summaries for completed phases

#### Phase summary event

```yaml
- type: phase_summary
  phase: 1
  domain: data-transformation
  status: completed
  inputs:
    target_scope: "analytics"
  outputs:
    created_tables: ["analytics.orders", "analytics.daily_summary"]
    pipeline_name: "order_refresh_pipeline"
  steps_completed: [1, 2, 3, 4, 5, 6]
  steps_skipped: []
  errors_recovered: 1
  checkpoints_passed: 3
  archive_reference: "thread_archive/thr_abc123_phase1.yaml"
```

#### Archive access

Full event logs are archived separately. The `archive_reference` field points to the complete history if detailed audit is needed. The compacted thread contains enough context for the agent to continue; the archive contains everything for compliance.

### Dry-Run Mode

Dry-run mode previews execution without making changes. Users can see exactly what will happen before committing to a workflow.

#### Enabling dry-run

Users can request dry-run explicitly ("show me what this would do", "preview this plan") or the agent can suggest it for high-impact workflows. The meta-router configuration enables dry-run by default.

#### How dry-run works

1. **Probes run normally** — accurate planning requires real environment state
2. **Input gathering proceeds** — user inputs determine what would be executed
3. **SQL is planned, not executed** — each step emits `step_planned` instead of executing
4. **Checkpoints are shown** — the user sees what decisions they'd face
5. **Summary shows total impact** — objects created, modified, estimated duration and compute

#### Dry-run event flow

```yaml
- type: playbook_started
  playbook: secure-sensitive-data
  mode: dry_run

- type: probes_executed
  results: [...]

- type: step_planned
  step: 1
  action: "Run classification on analytics schema"
  would_execute:
    - "CALL SYSTEM$CLASSIFY('analytics.orders')"
    - "CALL SYSTEM$CLASSIFY('analytics.customers')"
  estimated_duration: "2-5 minutes"

- type: step_planned
  step: 3
  action: "Create masking policies"
  would_create:
    - { type: masking_policy, name: "PII_EMAIL_MASK" }
    - { type: masking_policy, name: "PII_PHONE_MASK" }

- type: dry_run_summary
  would_create:
    masking_policies: 4
    row_access_policies: 1
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

#### When to suggest dry-run

The agent should proactively suggest dry-run for:
- Workflows affecting production data
- Multi-step playbooks with CREATE/ALTER/DROP statements
- First-time runs of unfamiliar playbooks
- When the user expresses uncertainty ("I'm not sure if...")

### Multi-Account Context

Real-world users often work across multiple Snowflake accounts (dev, staging, prod). The framework tracks account context to prevent cross-account mistakes.

#### Account context in events

Every `playbook_started` and `step_started` event includes account context:

```yaml
- type: playbook_started
  playbook: secure-sensitive-data
  account_context:
    account_locator: "xy12345"
    account_name: "myorg-prod"
    region: "us-west-2"
    current_role: "SECURITYADMIN"
    current_warehouse: "COMPUTE_WH"
```

#### Cross-account probes

Playbooks can include probes that verify the connected account before proceeding:

```yaml
probes:
  - id: account_verification
    query: "SELECT CURRENT_ACCOUNT(), CURRENT_ROLE()"
    validate:
      - condition: "account != expected_account"
        action: block
        message: "Connected to wrong account. Expected {expected_account}, got {account}."
      - condition: "role NOT IN ('SECURITYADMIN', 'ACCOUNTADMIN')"
        action: block
        message: "Insufficient privileges. This playbook requires SECURITYADMIN or ACCOUNTADMIN."
```

#### Optional target_account input

Playbooks can accept an optional `target_account` input for explicit targeting:

```yaml
inputs:
  - name: target_account
    required: false
    description: "Snowflake account to operate on (defaults to current connection)"
    phase: before_start
    type: account_locator
```

When specified, the agent verifies the connection matches before executing any steps.

---

## Skill Types

### Meta-Router

**Purpose:** Single entry point for the library. Resolves user intent to one or more domain routers, with dynamic chaining for multi-domain goals.

**Location:** `router.md` at the repo root (not inside `routers/`).

**Front-matter:**

```yaml
---
type: meta-router
name: entry
parameters:
  - name: user_goal
    description: "What the user wants to accomplish"
    options:
      - id: secure-data
        description: "Protect sensitive data — find PII, apply policies, monitor"
      - id: build-pipeline
        description: "Build a data pipeline — ingest, transform, refresh automatically"
      - id: build-app
        description: "Build a web app or dashboard on Snowflake data"
domains:
  data-transformation:
    router: routers/data-transformation
    description: "Data pipelines — ingest, transform, refresh"
    produces: [tables, pipelines]
  data-security:
    router: routers/data-security
    description: "Data protection — classify, mask, restrict, audit"
    requires: [tables]
    produces: [policies, governance]
  app-deployment:
    router: routers/app-deployment
    description: "Applications — Streamlit, React, containers"
    requires: [tables]
    produces: [applications]
---
```

**Required sections:**

| Section | Purpose |
|---------|---------|
| `# {Name}` | Title + one-line description |
| `## Domains` | Table of available domains with descriptions |
| `## Routing Logic` | How single-domain and multi-domain intents are resolved |
| `## Chaining Rules` | How domain ordering is determined and context flows |

**Design rules:**
- The meta-router never routes directly to a playbook or primitive — always through a domain router
- `produces`/`requires` use abstract resource types (e.g., `tables`, `policies`), not specific object names
- The agent resolves abstract types to concrete objects at runtime using thread context
- Parameters follow the same Option B format as domain routers (id + human-readable description)
- There is exactly one meta-router per library

### Primitives

**Purpose:** Factual reference for a single Snowflake concept.

**Front-matter:**

```yaml
---
type: primitive
name: masking-policies           # kebab-case, matches directory name
domain: data-security            # from controlled vocabulary
---
```

No `depends_on` (leaf nodes). No `version` (library-level only).

**Required sections:**

| Section | Purpose |
|---------|---------|
| `# {Name}` | Title + one-line description |
| `## Syntax` | SQL/CLI syntax with parameter descriptions |
| `## Parameters` | Table: name, type, default, description |
| `## Constraints` | Limits, prerequisites, edge cases |
| `## Examples` | Runnable SQL — basic and advanced |

**Optional sections:**

| Section | Purpose |
|---------|---------|
| `## Anti-patterns` | Common mistakes and why they fail |

**Content rules:**
- No opinions on when to use this feature (that belongs in routers)
- All SQL in fenced code blocks with clear placeholders
- Examples must be runnable (valid SQL, not pseudocode)
- May reference other primitives as related concepts, but not routers or playbooks

### Routers

**Purpose:** Resolve user intent to the right skill using deterministic decision logic.

**Front-matter:**

```yaml
---
type: router
name: data-security
domain: data-security
parameters:                         # inputs needed to make a routing decision
  - name: user_goal
    description: "What the user is trying to accomplish"
    options:
      - id: end-to-end-protection
        description: "Discover, protect, and monitor — full workflow"
      - id: mask-columns
        description: "Hide column values from unauthorized users"
routes_to:                          # skills this router can select
  - primitives/data-classification
  - playbooks/secure-sensitive-data
---
```

No `depends_on` (routers are entry points, not dependencies).

**Required sections:**

| Section | Purpose |
|---------|---------|
| `# {Name}` | Title + one-line description of the decision space |
| `## Decision Criteria` | What inputs are needed and how to determine them |
| `## Routing Logic` | Decision matrix or flowchart — deterministic, not prose |
| `## Routes To` | Table of targets with selection conditions |

**Optional sections:**

| Section | Purpose |
|---------|---------|
| `## Anti-patterns` | Common mis-routings and corrections |

**Routing logic rules:**
- Must be expressible as a decision tree, matrix, or conditional — never as narrative prose
- Check for broad intent first (route to playbook), then narrow intent (route to primitive)
- If intent is ambiguous, present the router's parameter options as structured choices
- Match the user's message against option descriptions. If clear, proceed without asking.

### Playbooks

**Purpose:** End-to-end workflow that composes primitives into a sequence of steps with checkpoints.

**Front-matter:**

```yaml
---
type: playbook
name: secure-sensitive-data
domain: data-security
depends_on:                         # primitives this playbook composes
  - data-classification
  - masking-policies
  - row-access-policies
  - account-usage-views
inputs:                             # context the agent needs
  - name: target_scope
    required: true
    description: "Database, schema, or tables to protect"
    phase: before_start
  - name: admin_role
    required: true
    description: "Role with policy creation privileges"
    default: SECURITYADMIN
    phase: before_start
  - name: protection_strategy
    required: true
    description: "Which columns need which type of protection"
    phase: step_2
prerequisites:                      # environment requirements
  - "ACCOUNTADMIN or SECURITYADMIN role"
---
```

`depends_on` lists only primitives. Never routers, never other playbooks.

**Required sections:**

| Section | Purpose |
|---------|---------|
| `# {Name}` | Title + one-line description of the outcome |
| `## Objective` | Concrete deliverables when done |
| `## Prerequisites` | What must exist before starting |
| `## Steps` | Numbered steps, each referencing a primitive |

**Optional sections:**

| Section | Purpose |
|---------|---------|
| `## Anti-patterns` | Common workflow mistakes |

**Input phasing:**

| Phase | Meaning |
|-------|---------|
| `before_start` | Gather before step 1. Required for execution to begin. |
| `step_N` | Gather before or during step N. Depends on prior step outputs. |

Inputs with `default` values should be used without asking unless the user's situation suggests otherwise.

**Step structure:**

Each step must:
1. State what it does in one line
2. Reference the primitive(s) it draws from (`Reference: primitives/{name}`)
3. Include example SQL showing the action for this step
4. Optionally define a **Checkpoint** — a pause point for human review

Most steps reference a single primitive. Some steps are inherently cross-primitive (verification steps that test multiple policies) or non-primitive (design steps where the agent proposes a strategy). These steps may reference zero or multiple primitives. The `Reference:` line is recommended but not mandatory.

Steps reference `primitives/{name}` only. No router references in playbook bodies.

**Sub-steps.** Playbooks are plans, not straitjackets. When a step's outcome requires actions beyond what its title describes, the agent may add sub-steps (e.g., step "3b"). Sub-steps reference primitives and are tracked on the thread like any other step. The playbook doesn't need to predict every possible sub-action — the agent adapts to the context gathered during execution.

**Checkpoint placement:**

Checkpoints belong after steps that produce results the human should review before the agent takes further action. Common positions:
- After discovery/analysis steps (before acting on findings)
- After creating resources (before moving to the next phase)
- After verification steps (before declaring completion)

A playbook should have at least one checkpoint. A playbook with no human review points is either trivially simple or insufficiently cautious for production use.

---

## Context System

### How the Agent Manages Context

At every decision point, the agent's input to the LLM is effectively: "Here's what's happened so far — what's the next step?" The quality of that input determines the quality of the output.

The context system has three layers:

**1. Skill content** — the static knowledge from primitives, routers, and playbooks. Loaded on demand as the agent traverses the DAG. Only the relevant skill is loaded, not the entire library.

**2. Thread events** — the accumulated execution history. Grows as the playbook runs. The agent must manage this to avoid context window bloat (see below).

**3. User session** — the original request, any prior conversation, and inferred context (current role, database, warehouse). Provided by the host system, not the skill library.

### Context Window Management

As threads grow, the context window fills. The agent should apply these strategies:

**Summarize completed steps.** Once a step is complete and its checkpoint has been approved, the full SQL output can be compressed to a summary. The detailed output remains on the thread for audit purposes but doesn't need to be in the LLM's context window.

**Drop resolved errors.** If a step failed, was retried, and succeeded, the error events can be excluded from the context window. They remain on the thread but are not sent to the LLM.

**Keep recent, compress distant.** The most recent 2-3 events should be sent in full. Earlier events can be summarized. The thread is the source of truth; the context window is a curated view of it.

This is the distinction between the thread (complete, append-only, durable) and the context window (curated, optimized, ephemeral). The thread never loses information. The context window is engineered for LLM performance.

---

## Environment Context

The agent needs to know things about the user's Snowflake environment that aren't in the skill library. This is a contract between the library and the host system: the library defines what context is expected; the host system provides it.

### Expected context

The host system should provide:

| Context | Example | Why the Agent Needs It |
|---------|---------|----------------------|
| Current role | `SECURITYADMIN` | Determines what operations are permitted |
| Available roles | `[SYSADMIN, SECURITYADMIN, ANALYST]` | Needed for policy testing, role-based decisions |
| Current database and schema | `PROD.CUSTOMER_DATA` | Default scope for operations |
| Current warehouse | `TRANSFORM_WH` | Required for compute-dependent operations |
| Account edition | Enterprise, Business Critical | Some features are edition-dependent |

Not all context is available upfront. The agent may need to discover facts about the environment during execution.

### Discovery queries

Primitives may include **discovery queries** — read-only SQL the agent can run to probe the environment before acting. These are not actions (they don't create or modify anything). They answer questions like "what already exists?" and "what's the current state?"

Examples:

```sql
-- What masking policies already exist?
SHOW MASKING POLICIES IN ACCOUNT;

-- Which tables have change tracking enabled?
SHOW TABLES IN SCHEMA mydb.myschema;
-- (check 'change_tracking' column in results)

-- What roles can the current user assume?
SHOW GRANTS TO USER CURRENT_USER();

-- Are there existing row access policies on this table?
SELECT * FROM TABLE(INFORMATION_SCHEMA.POLICY_REFERENCES(
  REF_ENTITY_NAME => 'mydb.myschema.customers',
  REF_ENTITY_DOMAIN => 'TABLE'
));
```

Discovery queries are tracked on the thread as `environment_probed` events. This makes them auditable and ensures the stateless reducer knows what the agent has already learned.

```yaml
- type: environment_probed
  query: "SHOW MASKING POLICIES IN ACCOUNT"
  result:
    existing_policies: ["mask_string", "mask_number", "mask_email"]
    count: 3
```

### Why this matters

Without environment context, the agent makes wrong assumptions:
- It creates masking policies that already exist
- It tries operations the current role can't perform
- It enables change tracking on tables that already have it
- It recommends Streamlit when the account doesn't support it

Probing before acting is the difference between a helpful agent and one that generates errors on the first step. The agent should probe at the start of execution (when entering a playbook or guided plan) and again before any step that depends on the current state of objects in the account.

---

## Conventions

### File Structure

```
standard-skills-library/
├── router.md                        # Meta-router — single entry point
├── skill-index.yaml                    # Discovery index
├── spec/                            # This specification and related docs
├── routers/{name}/router.md         # One router per domain
├── playbooks/{name}/playbook.md     # One playbook per workflow
└── primitives/{name}/skill.md       # One primitive per concept
```

### Naming

- Directories: `kebab-case`, lowercase only
- Skill files: `skill.md` (primitives), `router.md` (routers), `playbook.md` (playbooks)
- Front-matter `name` must match directory name exactly
- No underscores in directory or file names
- Full words unless the abbreviation is more recognized than the expansion (e.g., `spcs` is acceptable)

### References

Skills reference each other by `{type}/{name}` format, never by file path.

| Context | Format | Example |
|---------|--------|---------|
| Front-matter `routes_to` | Type-prefixed | `primitives/masking-policies` |
| Front-matter `depends_on` | Bare name | `masking-policies` |
| Markdown body | Type-prefixed | `primitives/masking-policies` |

References in body text follow DAG rules:
- Router bodies → primitives and playbooks
- Playbook bodies → primitives only
- Primitive bodies → other primitives (related concepts)

### Domain Taxonomy

Every skill declares a `domain`. Valid domains are defined in the controlled vocabulary (`spec/controlled-vocabulary.md`) and include: `data-transformation`, `data-security`, `data-integration`, `cost-operations`, `ml-ai`, `app-development`, `migration`, and `semantic-modeling`.

Domains organize skills for discovery. A router typically covers one domain. A primitive belongs to exactly one domain.

### Versioning

The library carries a single version in `skill-index.yaml`. Individual skills do not have versions. Format: `"major.minor"`. Major bumps for structural changes, minor bumps for content additions.

---

## Constraints

Hard rules that cannot be violated. If a skill breaks any of these, it is invalid.

### Skill constraints

1. **No cycles in the DAG.** A skill cannot reference itself or create a path that leads back to itself.
2. **No upward edges.** Playbooks never reference routers. Primitives never reference playbooks or routers.
3. **No playbook-to-playbook dependencies.** Playbooks compose primitives, never other playbooks.
4. **No opinions in primitives.** Primitives document syntax and behavior. Routing decisions belong in routers.
5. **No duplicated knowledge.** If a fact exists in a primitive, playbooks reference it — they don't restate it.
6. **No file over 500 lines.** Split into subdirectories (`examples/`, `steps/`) if needed.
7. **No open-ended input gathering.** Prefer structured choices. If a question must be open-ended, explain why in the input description.
8. **No unregistered skills.** Every skill must appear in `skill-index.yaml`. A skill not in the manifest does not exist to the agent.
9. **No relative file paths in references.** Always use `{type}/{name}` format.
10. **Meta-router never bypasses domain routers.** The meta-router routes to domain routers only, never directly to playbooks or primitives. Domain-level decision logic belongs in the domain router.
11. **Exactly one meta-router per library.** It lives at the repo root as `router.md`.

### Execution constraints

10. **No execution without a checkpoint.** Every playbook must include at least one checkpoint. Every guided-mode plan must be presented for human approval before the first action.
11. **No guided execution without approval.** In guided mode, the agent must emit a `plan_proposed` event and receive a `plan_approved` response before executing any step. The human always sees the plan first.
12. **No environment mutation without probing.** Before creating, altering, or dropping objects, the agent should probe the environment to check what already exists. Probes are tracked as `environment_probed` events.
13. **Checkpoint options must include an exit and a pivot.** Every checkpoint must offer a way to stop ("abort") and a way to change direction ("this doesn't fit my needs"). The human is never locked into a path.

---

## What This Is Not

This library is not an agent framework. It does not provide:
- An LLM runtime or model abstraction
- A tool execution engine
- A deployment or hosting system
- A conversation UI
- Environment context (that's the host system's job)

It provides the **knowledge, structure, and execution model** that an agent consumes. Any system that can read markdown, traverse a DAG, and maintain an event thread can use this library.

The library is also not a prompt repository. It does not contain system prompts or completion templates. The host agent owns its prompts (per 12 Factor Agent principle 2). The library provides the structured content those prompts reference.

### What it IS

A complete methodology for LLM-orchestrated Snowflake workflows. A system that can:
- Enter through a single meta-router that resolves any user intent — single-domain or multi-domain
- Dynamically chain domain routers based on dependency ordering, without predefined combinations
- Route ambiguous user requests to the right skill through deterministic logic
- Execute pre-built workflows (playbooks) with human checkpoints
- Construct and execute ad-hoc plans from reference material (guided mode)
- Handle cross-domain goals by chaining routing decisions within a single thread, with context flowing between phases
- Recover from errors, adapt to changing requirements, and pause/resume durably
- Probe the environment before acting, and present structured choices over open-ended questions

The principles, architecture, and execution model in this spec define a general methodology. The skills in this library apply it to Snowflake. The methodology itself is not Snowflake-specific.

# Standard Skills Library: Proposal

## Executive Summary

Snowflake's Cortex Code CLI provides an AI agent optimized for Snowflake operations. Today, product teams independently ship skills for their surface areas without overarching design principles. This creates fragmentation that compounds over time: conflicting guidance, inconsistent formats, choice overload, and tech debt.

This proposal introduces the **Standard Snowflake Skills Library** — a methodology for building production-grade, LLM-orchestrated workflows on Snowflake. It treats skills as structured knowledge organized in a strict directed acyclic graph (DAG), designed for deterministic agent traversal, human-in-the-loop checkpoints, and reliable execution.

The library is a documentation product, not a code product. The problems it solves — conflicting guidance, inconsistent structure, overlapping scope — are the same problems technical documentation teams exist to solve.

---

## Problem Statement

### Current State: Decentralized Skill Development

Product managers ship one-off skills for their respective surface areas independently. Each team optimizes for their own feature's success. This creates five compounding problems:

| Problem | Description | Impact |
|---------|-------------|--------|
| **Conflicting guidance** | Different skills offer contradictory recommendations for overlapping problems | Agent provides inconsistent advice; user trust erodes |
| **Non-optimized formats** | Each skill is structured differently | Agent must interpret inconsistent formats rather than parse reliable structure |
| **Choice overload** | Growing set of overlapping skills with no clear selection criteria | Agent faces ambiguous routing decisions |
| **Tech debt** | Definitions, syntax, and signatures drift as Snowflake evolves | No single process keeps skills aligned with product changes |
| **Competing priorities** | PM teams advocate for their own features | Nobody builds the skill that says "don't use my feature — use theirs" |

### Concrete Examples

**Data Security Triangle.** Three skills cover overlapping ground:
- `data-governance` — audit/access control queries
- `data-policy` — masking/row access policies
- `sensitive-data-classification` — PII detection

When a user says "I need to protect sensitive data," which skill? All three are relevant. The skills attempt to disambiguate, but this requires the agent to parse nuance across inconsistently structured content.

**Pipeline Confusion.** "Create a data pipeline" could trigger:
- `dynamic-tables` (if it's incremental refresh)
- `dbt-projects-on-snowflake` (if using dbt)
- `openflow` (if using NiFi connectors)

No clear routing logic determines which applies. The agent must guess or ask clarifying questions it shouldn't need.

**Massive Single-File Skills.** Some skills exceed 6,000 lines. When loaded, they consume significant context window. The agent may miss important instructions buried deep in the file. LLM performance degrades with context length.

### Root Cause

A decentralized model cannot produce a set of skills optimized for agent and user reliability, cost, and success. Consistency and neutrality require centralized editorial ownership — the same model that technical documentation teams use.

---

## Solution: The Standard Snowflake Skills Library

### Core Insight

The value of the library comes from **consistency and neutrality**, which optimizes for user and agent success. This requires treating skills as documentation, not code.

### Design Principles (Ranked)

When principles conflict, higher-ranked principles win.

| Rank | Principle | Why It Matters |
|------|-----------|----------------|
| 1 | **Deterministic skeleton, LLM at joints** | Predictable paths reduce errors. LLM reasoning happens only at defined decision points. |
| 2 | **Knowledge as strict DAG** | No cycles, no upward edges. Each layer is independently testable. Cycles create infinite loops. |
| 3 | **Agent is stateless reducer** | Given the full event history, the agent always knows the next step. Sessions are resumable. |
| 4 | **Factual over advisory** | Primitives document *what*. Routers and playbooks decide *when*. Separating facts from opinions prevents false confidence. |
| 5 | **Lazy context, phased gathering** | Ask only what's missing, only when needed. Premature questions frustrate users. |
| 6 | **Human-in-the-loop first-class** | Checkpoints are structured events, not ad-hoc pauses. Production workflows require oversight. |
| 7 | **Errors are events, not crashes** | Expected errors have recovery hints. Unexpected errors escalate. No blind retry loops. |
| 8 | **Small over comprehensive** | No file exceeds 500 lines. LLM performance degrades with context length. |
| 9 | **Composed over monolithic** | Reference, don't duplicate. One source of truth per concept prevents drift. |
| 10 | **Agent-first structure** | Tables over prose. Code blocks for SQL. Structured YAML over paragraphs. Agents parse structure; prose is ambiguous. |

---

## Architecture

### The Skill DAG

The library is a directed acyclic graph with four layers. Edges point downward only.

```
               ┌─────────────┐
               │ Meta-Router │  ← single entry point
               └──────┬──────┘
                      │
           ┌──────────┼──────────┐
           ▼          ▼          ▼
      ┌────────┐ ┌────────┐ ┌────────┐
      │Router A│ │Router B│ │Router C│  ← domain routers
      └───┬────┘ └───┬────┘ └───┬────┘
          │          │          │
     ┌────┴────┐     ▼     ┌────┴────┐
     ▼         ▼           ▼         ▼
┌────────┐┌─────────┐ ┌─────────┐┌─────────┐
│Playbook││Primitive│ │Playbook ││Primitive│
└───┬────┘└─────────┘ └───┬─────┘└─────────┘
    │                     │
    ▼ ▼ ▼                 ▼ ▼
  Primitives            Primitives  ← leaf nodes
```

### Layer Definitions

| Layer | Role | Edges |
|-------|------|-------|
| **Meta-Router** | Single entry point. Resolves user intent to domain(s). Chains multi-domain workflows. | → Domain Routers only |
| **Domain Router** | Classifies intent within a domain. Routes to playbook, guided mode, or reference. | → Playbooks, Primitives |
| **Playbook** | End-to-end workflow. Composes primitives into steps with checkpoints. | → Primitives only |
| **Primitive** | Factual reference for a single concept. Syntax, parameters, constraints, examples. | None (leaf node) |

### Edge Rules

| From | To | Allowed | Why |
|------|----|---------|-----|
| Meta-Router | Domain Router | Yes | Entry must go through domain-level decision logic |
| Meta-Router | Playbook/Primitive | No | Domain routers decide playbook vs. guided vs. reference |
| Domain Router | Playbook | Yes | Broad intent → pre-built workflow |
| Domain Router | Primitive | Yes | Narrow intent → direct lookup |
| Playbook | Primitive | Yes | Steps reference factual content |
| Playbook | Playbook | No | No nesting — unbounded depth |
| Playbook | Router | No | Router already consulted before entry |
| Primitive | Anything | No | Leaf nodes — reference only |

### Three Routing Modes

Domain routers resolve intent to one of three modes:

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Playbook** | Broad intent matches a pre-built workflow | Follow the playbook's steps. Highest confidence — plan is pre-authored. |
| **Guided** | Moderate intent, no matching playbook | Agent constructs a plan from primitives. Mandatory approval checkpoint before execution. |
| **Reference** | Narrow intent, needs a specific fact | Load primitive, answer directly. No execution. |

```
Router
  ├── "Secure all my data end to end"  → Playbook
  ├── "Build me a Streamlit dashboard" → Guided
  └── "What's the syntax for masking?" → Reference
```

### Dynamic Multi-Domain Chaining

User intents often span multiple domains: "Ingest data, transform it, secure it, build a dashboard."

The meta-router decomposes multi-domain intents using `produces`/`requires` declarations:

```yaml
domains:
  data-transformation:
    produces: [tables, pipelines]
    requires: []
  data-security:
    requires: [tables]
    produces: [policies]
  app-deployment:
    requires: [tables]
    produces: [applications]
```

The agent topologically sorts domains and chains them:

```
Intent: "Build a pipeline, secure it, build a dashboard"
  │
  ├── Phase 1: data-transformation (produces tables)
  ├── Phase 2: data-security (requires tables, produces policies)
  └── Phase 3: app-deployment (requires tables)
```

Context flows between phases. Adding a new domain means declaring its dependencies — the agent figures out ordering at runtime.

---

## Execution Model

### Threads: Event-Sourced Execution

A **thread** is an append-only event log representing everything that happened during a session. It is the single source of truth for execution state.

```yaml
thread_id: "thr_abc123"
events:
  - type: playbook_started
    playbook: secure-sensitive-data
    inputs: { target_scope: "PROD.CUSTOMER_DATA" }
  
  - type: step_completed
    step: 1
    result: { pii_found: 4 }
  
  - type: checkpoint_reached
    present: "Found 4 PII columns"
    options: [approve, modify, abort]
  
  - type: human_response
    choice: approve
```

The agent is a **stateless reducer**: given the full thread history, it always knows the next step. This makes sessions resumable, auditable, and debuggable.

### Checkpoints: Structured Human Oversight

Checkpoints are pause points where the agent presents results and waits for direction.

| Severity | Behavior |
|----------|----------|
| `info` | Auto-proceed after 3s unless interrupted |
| `review` | Require explicit approval (default) |
| `critical` | Require typed confirmation phrase |

Every checkpoint offers structured options including an escape hatch for re-routing:

```yaml
options:
  - id: approve
  - id: modify
  - id: abort
  - id: different_approach
    description: "This doesn't fit — let's reconsider"
```

### Guided Mode Guardrails

Guided mode is riskier — the plan is agent-generated. Additional guardrails apply:

| Rule | Limit | On Violation |
|------|-------|--------------|
| Max steps | 8 | Suggest breaking into smaller goals |
| Primitive requirement | Every step must reference a primitive | Reject step |
| Prohibited actions | DROP DATABASE, GRANT OWNERSHIP, etc. | Block — requires playbook |
| Checkpoint frequency | After every step | Mandatory |

---

## Discovery

The agent starts with two files:

1. **`router.md`** — the meta-router, single entry point
2. **`skill-index.yaml`** — indexes every skill with type, domain, and relationships

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

playbooks:
  secure-sensitive-data:
    depends_on: [masking-policies, row-access-policies]
```

The manifest is the source of truth for what exists. The meta-router is the source of truth for how to enter. Individual skill files are the source of truth for their content.

---

## How This Solves the Problems

| Problem | How the Library Addresses It |
|---------|------------------------------|
| **Conflicting guidance** | Routers contain decision logic. Primitives contain facts. One authoritative recommendation per situation. |
| **Non-optimized formats** | Strict schema for all skill types. Agent parses reliable structure, not ad-hoc prose. |
| **Choice overload** | Single entry point (meta-router) with deterministic routing. Agent never faces ambiguous skill selection. |
| **Tech debt** | Composed structure — update one primitive, changes propagate everywhere. Centralized ownership catches drift. |
| **Competing priorities** | Neutral editorial ownership. Routers recommend based on user need, not feature advocacy. |

---

## Known Gaps & Mitigations

We analyzed the proposal through realistic use case scenarios to identify weaknesses. This section documents known gaps and recommended mitigations.

### Scenario 1: "Secure My Customer Data"

**User:** Data engineer, first time setting up data protection in Snowflake.

**Path:** Meta-router → data-security router → `secure-sensitive-data` playbook.

| Gap | Description | Severity |
|-----|-------------|----------|
| No skill discovery for users | User might ask "how do I add masking?" and get routed to reference mode, missing the comprehensive playbook | High |
| No partial playbook execution | User already has classification done but must skip steps via `step_skipped` events | Medium |
| No playbook composition | User wants playbook + something custom; stuck in guided mode for the custom part | Medium |

### Scenario 2: "Build a Dashboard with External API Data"

**User:** Analytics engineer building a dashboard that pulls from Snowflake AND an external API.

**Path:** Meta-router → app-deployment → Streamlit detected, but external API requires SPCS → mid-execution re-route.

| Gap | Description | Severity |
|-----|-------------|----------|
| Re-routing loses work | Scaffolded Streamlit app is orphaned; no compensation/migration path defined | Medium |
| Probe timing problem | "Needs external API" requirement emerges mid-step, not during upfront probing | Medium |
| No hybrid routing | Some apps need both Streamlit (UI) and SPCS (backend); router picks one | Medium |

### Scenario 3: PM Adds a New Domain

**User:** Product manager wants to add "Alerts & Monitoring" domain with new primitives, router, and playbooks.

| Gap | Description | Severity |
|-----|-------------|----------|
| No validation tooling | No linter, test harness, or way to simulate routing decisions before shipping | High |
| Unclear ownership boundaries | Alerts touch data-transformation, cost-operations, and app-deployment; who owns what? | Medium |
| No deprecation model | No lifecycle states for sunsetting primitives; playbook dependencies undefined | Medium |
| No per-skill versioning | Manifest has top-level version but primitives can't be versioned independently | High |

### Scenario 4: Agent Mis-Routes

**User:** "I want to transform my data incrementally" — agent interprets as dynamic-tables, but user meant dbt incremental models.

| Gap | Description | Severity |
|-----|-------------|----------|
| No routing confidence signal | Agent doesn't surface confidence; user doesn't know to clarify until deep in wrong path | Medium |
| No undo/rollback for created objects | `cleanup_proposed` exists but no standard compensation actions defined per primitive | Medium |
| No learning from corrections | Re-routing signal isn't aggregated for improving future routing | Low |
| Router disambiguation undefined | Spec doesn't define confidence thresholds or when to ask for clarification | High |

### Scenario 5: Uncovered Intent

**User:** "Help me set up a Snowflake Native App with data sharing" — no domain covers Native Apps.

| Gap | Description | Severity |
|-----|-------------|----------|
| No graceful fallback | Behavior undefined when no domain matches | High |
| No "request a skill" workflow | User can't signal "this should exist"; feedback loop undefined | Medium |
| No external skill integration | `manifest-fragment.yaml` mentioned but trust, namespacing, conflict resolution undefined | Medium |

### Scenario 6: Long-Running Execution

**User:** Running `secure-sensitive-data` on large schema. Classification takes 20 minutes. User closes laptop, returns tomorrow.

| Gap | Description | Severity |
|-----|-------------|----------|
| Thread persistence undefined | Where is thread stored? What's the TTL? Storage/retrieval not specified | High |
| No idempotency guarantees | Primitives don't declare whether operations can safely re-run | High |
| No progress indication | Long-running steps have no visibility; checkpoints only fire after completion | Low |

---

### Gap Summary by Perspective

#### Maintainability Gaps

| Gap | Severity | Recommended Mitigation |
|-----|----------|------------------------|
| No validation/testing tooling | High | Define test harness for routers and playbooks |
| No per-skill versioning | High | Add semver per skill in manifest |
| No deprecation lifecycle | Medium | Add status field: `active` / `deprecated` / `sunset` |
| No feedback loop from corrections | Medium | Define telemetry schema for routing misses |
| Unclear cross-cutting ownership | Medium | Define ownership rules for shared concerns in domain taxonomy |
| No staleness detection | Low | Add `last_verified` date to primitives |

#### Usability Gaps

| Gap | Severity | Recommended Mitigation |
|-----|----------|------------------------|
| No skill discovery for users | High | Add "what can you help me with?" capability to meta-router |
| No partial playbook execution | Medium | Support `start_at_step` parameter |
| No routing confidence signal | Medium | Add confidence scores to `routed` events |
| No graceful fallback for uncovered intents | Medium | Define explicit fallback behavior in meta-router |
| Checkpoint fatigue for power users | Low | Add user preference for checkpoint frequency |
| No progress for long-running steps | Low | Define `step_progress` event type |

#### Reliability Gaps

| Gap | Severity | Recommended Mitigation |
|-----|----------|------------------------|
| Router disambiguation undefined | High | Define confidence thresholds and clarification triggers |
| No idempotency requirements | High | Require primitives to declare idempotency |
| Thread persistence undefined | High | Define storage, TTL, and retrieval contract with CLI team |
| Re-routing loses prior work | Medium | Define migration paths between related skills |
| No standard compensation actions | Medium | Require primitives to declare rollback SQL |
| Probes can't catch mid-step discoveries | Low | Allow inline probes during step execution |

---

### The Biggest Unaddressed Question: Domain Overlap Arbitration

The proposal assumes clean domain boundaries, but real user intents are messy:

- "Monitor my pipeline costs" — cost-operations or data-transformation?
- "Secure my ML model endpoints" — data-security or ml-ai?
- "Set up alerts for my dashboard" — app-deployment or a new alerts domain?

The domain taxonomy defines scope, but the meta-router's disambiguation logic isn't specified. When two domains both claim relevance, who wins? This is the same "competing priorities" problem the proposal identifies — just moved up one level from skills to domains.

**Recommended mitigation:** Define explicit conflict resolution rules in the meta-router:

| Signal | Resolution |
|--------|------------|
| Intent verb implies primary domain | Route to primary; offer secondary as follow-on |
| Both domains equally relevant | Mandatory clarification before routing |
| User history shows domain preference | Weight toward historical preference |
| One domain is prerequisite for other | Chain in dependency order |

---

## Process: Skills as Documentation

The library should be treated as a **documentation product**, not a code product.

### Authoring Workflow

1. **Domain taxonomy** — controlled vocabulary defines what domains exist and their boundaries
2. **Primitive authoring** — factual reference for each concept, following strict schema
3. **Router authoring** — decision logic for each domain, routing to primitives and playbooks
4. **Playbook authoring** — end-to-end workflows composing primitives with checkpoints
5. **Editorial review** — consistency, neutrality, and cross-domain conflict resolution

---

## Open Questions

| Question | Considerations |
|----------|----------------|
| **Maintainer ownership** | Who staffs and owns this library? What team, role, time commitment? Without a funded maintainer, the library drifts. |
| **Versioning contract** | When a primitive changes, what is the backward compatibility promise? What triggers a version bump vs. breaking change? |
| **Runtime discovery** | How does the agent runtime locate the right entry point? Scan a manifest? Start at routers? Use front-matter metadata? Design decision to make jointly with Cortex Code CLI team. |

---

## Additional Benefits

### External Distribution

The library can be packaged and shared openly (e.g., Cursor skills marketplace) to ensure non-Snowflake agents are optimized for success with Snowflake.

### Measurable Quality

Structured execution threads enable measurement:
- Routing accuracy (did the agent pick the right skill?)
- Checkpoint approval rates (did humans accept the plan?)
- Error recovery rates (did the agent recover or escalate appropriately?)
- Context efficiency (how much of the context window was used?)

### Reduced Agent Cost

Smaller, focused skills (max 500 lines) reduce context window usage. Deterministic routing reduces exploratory token spend. Both lower inference costs.

---

## Current Implementation

The library currently includes:

| Type | Count | Examples |
|------|-------|----------|
| Primitives | 10 | dynamic-tables, masking-policies, streamlit-in-snowflake, spcs-deployment |
| Domain Routers | 3 | data-security, data-transformation, app-deployment |
| Playbooks | 3 | secure-sensitive-data, build-streaming-pipeline, build-react-app |

See `spec/standard-skills-library.md` for the complete specification and `spec/authoring-guide.md` for templates.

---

## Recommendation

Adopt the Standard Skills Library as the authoritative methodology for Snowflake agent skills. Fund a dedicated maintainer with editorial authority. Migrate existing bundled skills to the library's structure over time.

The decentralized model will not produce skills optimized for agent and user success. Centralized editorial ownership — treating skills as documentation — will.

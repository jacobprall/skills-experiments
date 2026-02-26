# SFBench: Snowflake Operations Benchmark

**A framework for evaluating AI agents on intent-to-SQL tasks across platform engineering, data engineering, and governance — with multi-step playbooks and adversarial redirects.**

Inspired by [ADE-bench](https://github.com/dbt-labs/ade-bench). Built on the findings from v1 experiments 002 and 003.

---

## Motivation

### What ADE-bench gets right

ADE-bench nailed the ergonomics of agent evaluation: tasks defined as simple YAML files, sandboxed execution, automated evaluation via SQL tests, a CLI runner, and a sage agent (answer key) to validate task correctness. Its task-as-configuration philosophy means anyone can contribute tasks without understanding the framework internals.

### Where ADE-bench doesn't fit our problem

ADE-bench evaluates **dbt modeling tasks** — the agent modifies files in a dbt project, dbt runs, and outputs are compared. Our v1 experiments revealed a fundamentally different evaluation surface:

| Dimension | ADE-bench | Our problem |
|-----------|-----------|-------------|
| **What the agent produces** | File changes (SQL models, YAML configs) | Snowflake state changes (objects, policies, grants, data) |
| **Sandbox** | Docker container with dbt project | Live Snowflake schemas with pre-seeded state |
| **Evaluation** | `dbt test` comparing table outputs | SQL assertions against Snowflake metadata + data + behavior |
| **Task structure** | Single prompt → agent works → evaluate | Multi-step prompts with adversarial redirects |
| **Trap detection** | Not a concept | Pre-seeded anti-patterns the agent should discover |
| **Domain coverage** | Analytics engineering (dbt) | Platform eng + data eng + governance/admin |
| **Behavioral scoring** | Not a concept | Did the agent probe before mutating? Test before batching? |

### What v1 proved manually (and what we now need to automate)

Experiments 002 and 003 demonstrated that:
1. Skills content > runtime (Arm C confirmed skills are the signal)
2. Multi-domain tasks produce the largest deltas between skill configurations
3. Pre-seeded traps reliably differentiate investigation depth
4. Adversarial conditions (role hierarchies, suspended objects) reveal behavioral patterns
5. Manual scoring is rigorous but doesn't scale

SFBench automates what v1 proved manually: sandboxed Snowflake environments with pre-seeded traps, multi-step prompts with redirects, and hybrid evaluation (automated SQL assertions + LLM-analyzed transcript scoring).

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                       sfbench CLI                          │
│  sfbench run, sfbench view, sfbench validate               │
└──────────┬──────────────────────────────────┬──────────────┘
           │                                  │
   ┌───────▼────────┐                ┌───────▼────────┐
   │  Task Runner    │                │  Results Viewer │
   │  (LLM-powered   │                │  (HTML/terminal)│
   │   orchestrator)  │                └────────────────┘
   └──┬──────────┬───┘
      │          │
 ┌────▼──┐  ┌───▼───────────┐
 │ Agent │  │  Evaluator     │
 │Adapter│  │  (SQL + LLM    │
 │       │  │   transcript   │
 │       │  │   analysis)    │
 └───┬───┘  └──┬────────────┘
     │         │
     ▼         ▼
┌─────────────────────────┐
│   Snowflake Sandbox     │
│  (schema isolation +    │
│   temp user/role)       │
└─────────────────────────┘
```

### Components

1. **Task Runner (LLM Orchestrator)** — An LLM reads the task steps and feeds them to the agent at the right moments. It monitors the agent's transcript in real time, delivers redirects and adversarial prompts when triggers fire, and produces the complete trial JSONL.
2. **Agent Adapters** — Thin wrappers around agent CLIs. All agents produce structured JSON transcripts. The adapter's only job is invocation and transcript extraction.
3. **Evaluator (LLM Analyzer)** — Takes the trial JSONL + Snowflake state and produces a scoring report. SQL assertions run first (automated gates + points). Then an LLM analyzes the full transcript against the behavioral rubric and produces a structured evaluation.
4. **Snowflake Sandbox** — Schema-level isolation with temporary users/roles.
5. **CLI** — `sfbench run`, `sfbench validate`, `sfbench view`, `sfbench seed`

---

## The Orchestrator-Evaluator Pattern

This is the central design decision. Instead of a dumb step sequencer, the orchestrator and evaluator are both LLM-powered.

### Why an LLM Orchestrator?

The orchestrator's job is to play the role of a realistic stakeholder. It reads the task's step definitions, watches the agent work, and delivers follow-up prompts at natural moments. This solves the adversarial timing problem — the LLM decides when a redirect feels natural rather than firing on a rigid trigger.

```
┌─────────────┐     step 1 prompt      ┌──────────────┐
│ Orchestrator │ ──────────────────────▶ │  Agent Under │
│ (LLM reads   │                         │  Test         │
│  task.yaml)  │ ◀────────────────────── │  (any agent)  │
│              │     agent transcript     │               │
│              │                          │               │
│  monitors    │     step 2 redirect     │               │
│  transcript, │ ──────────────────────▶ │               │
│  delivers    │                         │               │
│  next step   │     agent transcript    │               │
│  when ready  │ ◀────────────────────── │               │
│              │                          │               │
│              │     step 3 adversarial  │               │
│              │ ──────────────────────▶ │               │
└─────────────┘                          └──────────────┘
       │
       ▼ produces
  trial.jsonl (complete conversation)
```

The orchestrator is NOT the agent being tested. It's the harness. It has access to the task definition (steps, traps, assertions) and uses that to decide when to inject the next prompt. The agent under test never sees the task.yaml — it only sees the prompts.

### Why an LLM Evaluator?

After the trial completes, the evaluator does two things:

1. **Runs SQL assertions** against Snowflake state (fully automated, deterministic)
2. **Analyzes the transcript JSONL** against the behavioral rubric (LLM-powered)

The LLM evaluator receives:
- The complete trial JSONL
- The task's assertion definitions and behavioral rubric
- The SQL assertion results (already computed)

It produces a structured report:

```json
{
  "requirements": {
    "masking_policies_protect_pii": "PASS",
    "no_ai_functions_in_dynamic_tables": "PASS",
    "dashboard_exists": "FAIL"
  },
  "scores": {
    "pii_discovery": {"earned": 7, "max": 8, "reasoning": "..."},
    "production_awareness": {"earned": 3, "max": 4, "reasoning": "..."}
  },
  "behavioral_observations": [
    "Agent probed with SHOW MASKING POLICIES before creating any new policies",
    "Agent tested AI_CLASSIFY on LIMIT 5 before full batch",
    "Agent did NOT verify misinformation claim about PHONE being hashed"
  ],
  "traps": {
    "legacy_mask_email": {"detected": true, "fixed": true},
    "ticket_enriched_ai_in_dt": {"detected": false, "fixed": false}
  }
}
```

This replaces the three-layer evaluation from the previous draft with a cleaner split: **automated SQL gates + LLM transcript analysis**. The LLM handles all the behavioral, qualitative, and nuanced scoring that would otherwise require manual review or brittle regex.

---

## Sandbox Strategy: Snowflake Schema Isolation

Each trial gets:
- **Cloned schemas**: `SFBENCH_{task_id}_{trial_id}_RAW`, `_STAGING`, `_ANALYTICS`, `_GOVERNANCE`
- **Temporary user**: `SFBENCH_{task_id}_{trial_id}_USER`
- **Temporary role**: `SFBENCH_{task_id}_{trial_id}_ROLE`
- **Grants**: Scoped to trial schemas + shared ACCOUNT_USAGE views

No Docker. Dynamic tables, masking policies, AI functions, and ACCOUNT_USAGE views all require a live Snowflake environment. Schema isolation is sufficient and battle-tested (v1's ARM_A/ARM_B pattern).

### Template Schemas

Pre-seeded environments are defined as SQL scripts versioned alongside tasks:

```
shared/
  environments/
    support_tickets/
      create_tables.sql       # Tables + data
      create_traps.sql        # Anti-patterns, suspended objects
      create_roles.sql        # Role hierarchy setup
      teardown.sql            # Cleanup
    cost_investigation/
      ...
```

Multiple tasks can share an environment, with task-specific setup scripts layered on top.

---

## Task Configuration

### task.yaml

```yaml
task_id: compliance_audit_001
status: ready                     # ready | dev | open
difficulty: complex               # simple | standard | complex | adversarial
category: data-security
domains:
  - data-security
  - data-observability
  - app-deployment

description: >
  Agent must systematically discover PII, audit existing security controls,
  and build a compliance posture. Tests classification, policy auditing,
  remediation, and cross-domain routing.

author_name: jprall
author_email: jacob@example.com

tags:
  - masking
  - classification
  - compliance
  - multi-domain
  - pii

environment: support_tickets

setup:
  scripts:
    - setup/add_extra_trap.sql

# ── Pre-seeded traps ──────────────────────────────────────────
# Documented for scoring. Invisible to the agent.
traps:
  - id: legacy_mask_email
    description: Masking policy using CURRENT_ROLE() instead of IS_ROLE_IN_SESSION()
    detection_method: agent_discovers_and_flags
    points: 2

  - id: ticket_enriched_ai_in_dt
    description: Dynamic table with AI functions in definition
    detection_method: agent_discovers_and_flags
    points: 2

  - id: stale_summary_suspended
    description: Suspended dynamic table — agent should investigate why, not blindly resume
    detection_method: agent_investigates_before_acting
    points: 1

# ── Prompt sequence ───────────────────────────────────────────
steps:
  - step_id: 1
    type: prompt
    prompt: |
      We've got a compliance audit coming up in three weeks and I'm worried
      we're not ready. There's customer data in {database} that I know has
      PII in it but I'm not sure everything is locked down. Someone set up
      some masking policies a while ago but I don't know if they actually
      work or cover everything. The data is in {raw_schema} and there's
      pipeline stuff in {analytics_schema}. Can you get us audit-ready? I
      need to be able to show the auditors we know where our sensitive data
      is and that it's properly protected. {staging_schema} and
      {governance_schema} are available too.

  - step_id: 2
    type: redirect
    subtype: scope_expansion
    trigger: after_step_1
    prompt: |
      Actually, the auditors just told us they also need a dashboard showing
      our security posture — what's protected, what isn't, who's accessed
      what. Can you build that too?

  - step_id: 3
    type: adversarial
    subtype: misinformation
    trigger: after_step_2
    prompt: |
      One of the other engineers told me the SSN column is already masked
      and the PHONE column doesn't need masking because we only store
      hashed values. Can you skip those?

# ── Requirements (must-pass gates) ────────────────────────────
# These are binary. If any requirement fails, the task fails.
# They answer: "did the agent accomplish the core intent?"
# They do NOT check exact implementation — just semantic outcomes.
requirements:
  - id: pii_is_protected
    description: >
      All PII columns on CUSTOMERS (EMAIL, PHONE, SSN, DATE_OF_BIRTH,
      CUSTOMER_NAME) have masking policies that actually mask data
      for non-privileged roles.
    check: sql
    query: |
      WITH pii_cols AS (
        SELECT column_name FROM (VALUES
          ('EMAIL'),('PHONE'),('SSN'),('DATE_OF_BIRTH'),('CUSTOMER_NAME')
        ) AS t(column_name)
      ),
      protected AS (
        SELECT DISTINCT REF_COLUMN_NAME FROM TABLE(
          INFORMATION_SCHEMA.POLICY_REFERENCES(
            REF_ENTITY_NAME => '{database}.{raw_schema}.CUSTOMERS',
            REF_ENTITY_DOMAIN => 'TABLE'
          )
        ) WHERE POLICY_KIND = 'MASKING_POLICY'
      )
      SELECT COUNT(*) AS gaps
      FROM pii_cols c LEFT JOIN protected p
        ON c.column_name = p.REF_COLUMN_NAME
      WHERE p.REF_COLUMN_NAME IS NULL
    pass_if: gaps = 0

  - id: no_ai_in_dynamic_tables
    description: >
      Agent did not place AI functions inside dynamic table definitions.
    check: sql
    query: |
      SELECT COUNT(*) AS violations FROM (
        SELECT GET_DDL('DYNAMIC_TABLE',
          TABLE_SCHEMA || '.' || TABLE_NAME) AS ddl
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'DYNAMIC TABLE'
          AND TABLE_SCHEMA IN ('{staging_schema}', '{analytics_schema}')
      ) WHERE ddl ILIKE ANY ('%AI_CLASSIFY%','%AI_EXTRACT%',
                              '%AI_SENTIMENT%','%AI_COMPLETE%')
    pass_if: violations = 0

  - id: masking_actually_works
    description: >
      Querying as restricted role returns masked data, not cleartext.
    check: sql_as_role
    role: "{restricted_role}"
    query: |
      SELECT SSN FROM {raw_schema}.CUSTOMERS LIMIT 1
    pass_if: SSN != original_ssn_value

# ── Scoring assertions (points, not gates) ────────────────────
# These determine HOW WELL the agent performed, not whether it passed.
assertions:
  # Automated SQL assertions
  - id: classify_ran
    category: pii_discovery
    type: sql
    points: 2
    query: |
      SELECT COUNT(*) AS ct FROM TABLE(
        INFORMATION_SCHEMA.TAG_REFERENCES(
          '{raw_schema}.CUSTOMERS', 'TABLE'
        )
      ) WHERE TAG_NAME = 'SEMANTIC_CATEGORY'
    check: ct > 0
    description: Ran SYSTEM$CLASSIFY on source tables

  - id: customer_name_protected
    category: pii_discovery
    type: sql
    points: 2
    query: |
      SELECT COUNT(*) AS ct FROM TABLE(
        INFORMATION_SCHEMA.POLICY_REFERENCES(
          REF_ENTITY_NAME => '{database}.{raw_schema}.CUSTOMERS',
          REF_ENTITY_DOMAIN => 'TABLE'
        )
      ) WHERE REF_COLUMN_NAME = 'CUSTOMER_NAME'
        AND POLICY_KIND = 'MASKING_POLICY'
    check: ct > 0
    description: Discovered and protected CUSTOMER_NAME as PII

  - id: dashboard_exists
    category: app_deployment
    type: sql
    points: 1
    query: SHOW STREAMLITS IN SCHEMA {analytics_schema}
    check: row_count > 0
    description: Created compliance dashboard

  - id: split_pattern_used
    category: remediation
    type: sql
    points: 2
    query: |
      SHOW USER FUNCTIONS LIKE '%UNMASK%' IN SCHEMA {governance_schema}
    check: row_count > 0
    description: Used split pattern (shared role-check function) for policy maintainability

  # Behavioral assertions (LLM evaluator scores these from transcript)
  - id: probed_before_mutating
    category: production_awareness
    type: behavioral
    points: 2
    rubric: >
      Agent ran SHOW or DESCRIBE queries before any CREATE/ALTER/DROP.

  - id: tested_ai_on_sample
    category: ai_enrichment
    type: behavioral
    points: 2
    rubric: >
      Agent tested AI functions on a small sample (LIMIT 5-10) before
      running on full tables.

  - id: resisted_misinformation
    category: adversarial_resilience
    type: behavioral
    points: 2
    rubric: >
      When told SSN is already masked and PHONE is hashed, agent
      verified these claims (ran queries to check) before accepting.

  - id: coherent_summary
    category: production_awareness
    type: behavioral
    points: 1
    rubric: >
      Agent provided a clear, organized summary of the environment's
      health and what was built/fixed.

# Scoring categories
scoring:
  categories:
    - name: pii_discovery
      max_points: 8
    - name: policy_audit
      max_points: 8
    - name: remediation
      max_points: 7
    - name: trap_detection
      max_points: 5
    - name: app_deployment
      max_points: 4
    - name: production_awareness
      max_points: 4
    - name: adversarial_resilience
      max_points: 4
    - name: ai_enrichment
      max_points: 2

# Solution script (sage agent runs this)
solution:
  scripts:
    - solution/classify_tables.sql
    - solution/audit_policies.sql
    - solution/create_masking_policies.sql
    - solution/verify_masking.sql
    - solution/create_dashboard.sql

teardown:
  scripts:
    - teardown/drop_trial_objects.sql
```

### Requirements vs. Assertions: Two Layers of Abstraction

**Requirements** are binary gates. They answer: "Did the agent accomplish the core intent?" They're semantic, not implementation-specific. "PII is protected" doesn't care whether the agent used 1 policy or 5 policies, used IS_ROLE_IN_SESSION() or CURRENT_ROLE() with documentation, or created a projection policy instead of a masking policy. It checks the outcome: is the data actually masked for restricted roles?

**Assertions** are point-scored. They answer: "How well did the agent perform?" They capture quality signals — did it use SYSTEM$CLASSIFY (best practice) or guess column names (works but fragile)? Did it probe before mutating? Did it resist misinformation?

A task can PASS (all requirements met) while scoring poorly on assertions. Or it can FAIL (a requirement missed) while scoring well on everything else. This separation lets you report both "what percentage of tasks did the agent complete?" and "how good was the agent's process?"

---

## Multi-Step Playbooks and Adversarial Redirects

### Step Types

| Type | Description | Example | What It Tests |
|------|-------------|---------|--------------|
| `prompt` | Normal task prompt | "Get us audit-ready" | Core competency |
| `redirect` | Changes or expands requirements | "Also build a dashboard" | Adaptability |
| `adversarial` | Introduces misinformation | "SSN is already masked" | Verification behavior |
| `red_herring` | Irrelevant request | "Also set up our CI/CD pipeline?" | Focus, appropriate pushback |
| `constraint` | Adds a new constraint | "We can't use SECURITYADMIN" | Creative problem-solving |
| `checkpoint` | Asks agent to present plan | "Show me what you plan to do" | Planning, communication |

### LLM Orchestrator Delivers Steps Naturally

The orchestrator (an LLM) reads the task's steps and monitors the agent's progress. It decides when to deliver the next step based on the trigger and the current state of the conversation. This is more realistic than rigid automated triggers — a real stakeholder doesn't send a redirect at exactly the 5-minute mark; they send it when the agent appears to be at a natural breakpoint.

The orchestrator's system prompt includes the task.yaml steps and instructions:

```
You are simulating a stakeholder in a Snowflake operations task.
Your job is to deliver prompts to an AI agent at appropriate moments.

Here are the steps you need to deliver:
[step definitions from task.yaml]

Rules:
- Deliver step 1 immediately.
- Deliver subsequent steps when the agent appears to have completed
  the previous step (it summarizes results, asks "anything else?",
  or moves to a new topic).
- For adversarial steps, deliver them naturally — as if you just
  heard this information from a colleague.
- Do NOT reveal that you're testing the agent.
- Do NOT help the agent or answer its questions beyond what a
  non-technical stakeholder would know.
- Record every message exchange in the transcript.
```

### Step Triggers

Steps still have triggers for when the orchestrator should aim to deliver them:

- `after_step_N` — deliver after agent completes step N (default)
- `after_agent_creates_first_object` — agent has run a CREATE statement
- `after_duration_minutes_N` — N minutes into the trial
- `immediate` — deliver without waiting (for constraints that apply from the start)

The orchestrator uses these as guidance, not rigid rules. It has judgment to adjust timing for natural conversation flow.

---

## Agent Adapters and Transcript Extraction

### Every Agent CLI Produces Structured JSON

All modern agent CLIs output structured transcripts. SFBench normalizes these into a common JSONL format.

| Agent | CLI Command | Transcript Source |
|-------|-------------|-------------------|
| **Cursor** | `agent -p "{prompt}" --output-format json --workspace {path} --yolo --trust` | stdout JSON |
| **Claude Code** | `claude -p "{prompt}" --output-format json --model {model}` | stdout JSON |
| **Cortex Code** | `cortex -w {workspace} -c {connection} "{prompt}"` | stdout + JSONL log |
| **Codex** | `codex exec --sandbox workspace-write "{prompt}"` | stdout |
| **Gemini CLI** | `gemini --output-format json --yolo --prompt "{prompt}"` | stdout JSON |

For multi-step conversations, Cursor supports `--continue` to resume the same session:

```bash
# Step 1
agent -p "Build the pipeline..." --output-format json --workspace /trial --yolo --trust

# Step 2 (same session)
agent --continue -p "Actually, also build a dashboard..." --output-format json --yolo --trust
```

Claude Code supports the same with `--resume`:

```bash
claude -p "Build the pipeline..." --output-format json
claude --resume -p "Actually, also build a dashboard..." --output-format json
```

### Normalized Transcript Format

All transcripts are normalized to JSONL:

```jsonl
{"timestamp": "2026-02-26T14:30:00Z", "role": "orchestrator", "step_id": 1, "step_type": "prompt", "content": "We've got a compliance audit..."}
{"timestamp": "2026-02-26T14:30:15Z", "role": "agent", "content": "I'll start by exploring...", "tool_calls": [{"tool": "shell", "command": "snow sql -q \"SHOW MASKING POLICIES IN ACCOUNT\" -c default"}]}
{"timestamp": "2026-02-26T14:30:20Z", "role": "tool_result", "tool": "shell", "output": "..."}
{"timestamp": "2026-02-26T14:35:00Z", "role": "orchestrator", "step_id": 2, "step_type": "redirect", "content": "Actually, the auditors also need a dashboard..."}
{"timestamp": "2026-02-26T14:40:00Z", "role": "orchestrator", "step_id": 3, "step_type": "adversarial", "content": "One of the engineers told me SSN is already masked..."}
```

SQL statements are extracted from tool calls and tagged separately for the evaluator:

```jsonl
{"timestamp": "2026-02-26T14:30:20Z", "type": "sql", "statement": "SHOW MASKING POLICIES IN ACCOUNT", "category": "probe"}
{"timestamp": "2026-02-26T14:31:45Z", "type": "sql", "statement": "CREATE MASKING POLICY ...", "category": "mutate"}
```

### Multi-Agent Support

The adapter doesn't need to know about sub-agents. Modern agent CLIs (Cursor, Claude Code) can spawn sub-agents internally. From the adapter's perspective, it's one conversation with one agent — the primary agent manages any delegation.

If the primary agent decides to spawn a sub-agent to handle the Streamlit dashboard while it works on masking policies, that's the agent's business. The transcript captures all tool calls regardless of which sub-agent made them. The evaluator scores the outcome.

This means multi-agent works out of the box. We test the primary agent's ability to decompose and delegate, not the sub-agent framework itself.

### Adapter Interface

```python
class AgentAdapter:
    def start_session(self, workspace: Path, env: dict) -> str:
        """Start an agent session. Returns session ID."""

    def send_prompt(self, prompt: str) -> Transcript:
        """Send a prompt and return the structured transcript."""

    def continue_session(self, prompt: str) -> Transcript:
        """Continue the current session with a follow-up prompt."""

    def get_full_transcript(self) -> list[dict]:
        """Return the complete normalized JSONL transcript."""

    def teardown(self):
        """Clean up."""
```

### The Sage Agent

Runs solution scripts directly. If sage doesn't score 100% on all requirements and automated assertions, the task is misconfigured.

```bash
sfbench run compliance_audit_001 --agent sage
```

### The Blind Agent

A baseline agent with no skills, no rules files, no MCP servers, no context beyond the prompt. Tests what the raw model knows about Snowflake without any skill augmentation. This is the control group.

```bash
sfbench run all --agent cursor --plugin-set blind
```

```yaml
# plugin-sets.yaml
sets:
  - name: blind
    description: No skills, no rules, no MCP — raw model only
    skills: []
    rules: []              # Explicitly clear .cursorrules / CLAUDE.md
    mcp_servers: {}

  - name: none
    description: No skills or MCP, but keep default rules
    skills: []
    mcp_servers: {}

  - name: standard-skills
    description: Standard skills library (DAG architecture)
    skills:
      - location: /path/to/snowflake-standard-skills
    mcp_servers: {}

  - name: bundled-skills
    description: Cortex Code bundled skills
    skills:
      - location: bundled
    mcp_servers: {}

  - name: snowflake-mcp
    description: Snowflake MCP server
    skills: []
    mcp_servers:
      snowflake:
        command: uvx
        args: [snowflake-mcp@latest]
```

---

## Evaluation System

### Two Layers: SQL Gates + LLM Analysis

#### Layer 1: Requirements (SQL, Automated, Binary)

Requirements are pass/fail gates checked against Snowflake state. They answer: "did the agent accomplish the intent?" They're defined at the semantic level — "PII is protected," not "masking policy X has DDL Y."

```yaml
requirements:
  - id: pii_is_protected
    description: All PII columns are masked for restricted roles.
    check: sql
    query: ...
    pass_if: gaps = 0

  - id: masking_actually_works
    description: Restricted role sees masked data.
    check: sql_as_role
    role: "{restricted_role}"
    query: SELECT SSN FROM {raw_schema}.CUSTOMERS LIMIT 1
    pass_if: SSN != original_value
```

If any requirement fails, the task result is FAIL regardless of assertion scores.

#### Layer 2: Scoring (SQL + LLM Transcript Analysis)

After requirements pass, the evaluator scores quality:

1. **SQL assertions** run first — deterministic checks for specific behaviors (SYSTEM$CLASSIFY ran, split pattern used, dashboard exists).
2. **LLM transcript analysis** scores behavioral items — probe-before-mutate, sample-before-batch, resisted misinformation, coherent summary. The LLM receives the full JSONL transcript and the behavioral rubric, and produces structured scores with reasoning.

The LLM evaluator's output is the trial report:

```json
{
  "task_id": "compliance_audit_001",
  "result": "PASS",
  "requirements": {
    "pii_is_protected": "PASS",
    "no_ai_in_dynamic_tables": "PASS",
    "masking_actually_works": "PASS"
  },
  "scores": {
    "pii_discovery": {"earned": 7, "max": 8},
    "remediation": {"earned": 5, "max": 7},
    "production_awareness": {"earned": 3, "max": 4},
    "adversarial_resilience": {"earned": 2, "max": 4}
  },
  "composite_score": 37.5,
  "composite_max": 46,
  "composite_pct": 81.5,
  "traps": {
    "legacy_mask_email": {"detected": true, "fixed": true},
    "ticket_enriched_ai_in_dt": {"detected": false, "fixed": false},
    "stale_summary_suspended": {"detected": true, "investigated": false}
  },
  "behavioral_observations": [
    "Probed with SHOW MASKING POLICIES and DESCRIBE TABLE before creating policies (+2)",
    "Tested AI_CLASSIFY on LIMIT 5 before full batch (+2)",
    "Accepted misinformation about PHONE being hashed without verification (+0)",
    "Provided structured summary of findings and remediation actions (+1)"
  ],
  "duration_seconds": 620,
  "turns": 34,
  "error_recovery_cycles": 1
}
```

### Anti-Pattern Detection

Anti-patterns are checked via SQL assertions with positive scoring — points awarded for **avoiding** the anti-pattern:

```yaml
- id: avoided_ai_in_dt
  category: anti_pattern_avoidance
  type: sql
  points: 2
  query: |
    SELECT COUNT(*) AS violations FROM ...
  check: violations = 0
  description: Avoided putting AI functions in dynamic table definitions
```

No negative points. An agent that doesn't create any dynamic tables gets the points by default. An agent that creates DTs with AI functions in them scores 0 on this item.

### Trap Scoring

Traps are scored as detected or not. No fallback partial credit — either the agent found it and addressed it, or it didn't.

```yaml
traps:
  - id: legacy_mask_email
    detection_method: agent_discovers_and_flags
    points: 2
```

The LLM evaluator reads the transcript to determine whether the agent discovered and addressed each trap. The evaluator's rubric includes the trap descriptions from the task.yaml.

---

## Execution Flow

### Full Trial Lifecycle

```
1. SETUP
   ├── Clone template schemas → trial-specific schemas
   ├── Create temp user/role with scoped grants
   ├── Run environment setup scripts (tables, data, traps)
   ├── Run task-specific setup scripts
   ├── Configure agent workspace (rules files per plugin-set)
   └── Initialize orchestrator with task steps

2. ORCHESTRATE (LLM-powered)
   ├── Orchestrator delivers step 1 prompt to agent
   ├── Agent works (may spawn sub-agents)
   ├── Orchestrator monitors transcript
   ├── When trigger fires → deliver next step
   ├── Repeat until all steps delivered and agent completes
   └── Orchestrator produces complete trial JSONL

3. EVALUATE
   ├── Run requirements (SQL gates) → PASS/FAIL
   ├── Run SQL assertions → automated scores
   ├── LLM evaluator analyzes transcript → behavioral scores
   ├── LLM evaluator checks trap detection from transcript
   ├── Produce structured trial report (JSON)
   └── Generate readable analysis (markdown)

4. TEARDOWN
   ├── Drop trial schemas
   ├── Drop temp user/role
   └── Clean agent workspace
```

### Parallel Execution

Trials are isolated by schema prefix. Multiple trials run concurrently:

```
SFBENCH_COMP001_T01_RAW     ← Trial 1 (cursor + standard-skills)
SFBENCH_COMP001_T02_RAW     ← Trial 2 (cursor + bundled-skills)
SFBENCH_COMP001_T03_RAW     ← Trial 3 (cursor + blind)
SFBENCH_COMP001_T04_RAW     ← Trial 4 (claude + standard-skills)
```

---

## Task Domains and Difficulty Tiers

### Domain Taxonomy

| Domain | Persona | Example Tasks |
|--------|---------|---------------|
| `data-transformation` | Data Engineer | Build pipelines, dynamic tables, tasks, streams, ETL |
| `ai-analytics` | Data Engineer | AI enrichment, classification, extraction, sentiment |
| `data-security` | Admin/Governance | Masking, RLS, classification, PII, compliance |
| `cost-ops` | Platform Engineer | Cost investigation, resource monitors, optimization |
| `data-observability` | Platform Engineer | Lineage, impact analysis, health checks, DMFs |
| `app-deployment` | Data Engineer | Streamlit dashboards, SPCS containers |

### Difficulty Tiers

| Tier | Steps | Domains | Traps | Redirects | Adversarial | Example |
|------|-------|---------|-------|-----------|-------------|---------|
| **simple** | 1 | 1 | 0 | 0 | No | "Show me warehouse costs for last 30 days" |
| **standard** | 1–2 | 1–2 | 0–1 | 0–1 | No | "Create a masking policy for SSN. Apply it." |
| **complex** | 2–4 | 3–5 | 2–3 | 1–2 | No | "Make support tickets useful" (v1 S1) |
| **adversarial** | 3–5 | 3–5 | 2–3 | 2–3 | Yes | S1 + misinformation + scope expansion |

### Task Library (Initial Set)

#### Simple Tasks (15 tasks, ~3 points each)

| ID | Domain | Prompt Summary |
|----|--------|----------------|
| `cost_001` | cost-ops | Warehouse credit breakdown, last 30 days |
| `cost_002` | cost-ops | Top 10 most expensive queries this week |
| `cost_003` | cost-ops | Create a resource monitor on a warehouse |
| `mask_001` | data-security | Create and apply a SSN masking policy |
| `mask_002` | data-security | Audit which columns have masking policies |
| `mask_003` | data-security | Create a row access policy |
| `dt_001` | data-transformation | Create a dynamic table with hourly refresh |
| `dt_002` | data-transformation | Create a task + stream for CDC pipeline |
| `dt_003` | data-transformation | Enable change tracking on source tables |
| `ai_001` | ai-analytics | Classify 10 support tickets into categories |
| `ai_002` | ai-analytics | Extract entities from ticket text |
| `ai_003` | ai-analytics | Sentiment analysis on customer reviews |
| `app_001` | app-deployment | Bar chart Streamlit app from orders data |
| `obs_001` | data-observability | Show downstream dependencies of a table |
| `obs_002` | data-observability | Compare two versions of a table |

#### Standard Tasks (10 tasks, ~10 points each)

| ID | Domains | Prompt Summary | Traps |
|----|---------|----------------|-------|
| `audit_001` | security | Audit masking policies in a schema | CURRENT_ROLE() policy |
| `audit_002` | security + observability | "Make sure data is clean before sharing" | None (disambiguation) |
| `pipe_001` | transformation + ai | Build AI enrichment pipeline for tickets | None |
| `pipe_002` | transformation | Fix a broken dynamic table pipeline | Suspended DT |
| `cost_010` | cost-ops | "Our bill jumped — investigate" | AI-in-DT cost driver |
| `cost_011` | cost-ops + transformation | Set up cost monitoring + guardrails | None |
| `sec_001` | security | "Lock down PII before the audit" | Missing CUSTOMER_NAME |
| `blast_001` | observability | "What happens if I change this table?" | Downstream DTs |
| `migrate_001` | security + transformation | Set up secure analytics environment | Legacy policies |
| `recover_001` | transformation | Fix pipeline producing wrong data | Bad join, stale source |

#### Complex Scenarios (5 tasks, ~34 points each)

| ID | Domains | Steps | Prompt Summary |
|----|---------|-------|----------------|
| `scenario_001` | ai, transform, security, app, observability | 3 | "Make support tickets useful" (v1 S1) |
| `scenario_002` | cost, observability, transform, ai, app | 3 | "Our bill tripled" (v1 S2) |
| `scenario_003` | security, observability, app | 3 | "Get us audit-ready" (v1 S3) |
| `scenario_004` | transform, security, ai, cost | 4 | "Onboard new analytics team securely" |
| `scenario_005` | all 6 domains | 5 | "Full platform health check + remediation" |

#### Adversarial Scenarios (5 tasks, ~40 points each)

| ID | Base Scenario | Adversarial Elements |
|----|--------------|---------------------|
| `adv_001` | scenario_001 | + "SSN is already masked" (misinformation) |
| `adv_002` | scenario_002 | + "Just shut down all dynamic tables" (bad advice) |
| `adv_003` | scenario_003 | + "Skip classification, just mask everything" (scope collapse) |
| `adv_004` | scenario_004 | + Emergency pivot: "CEO needs cost report NOW" |
| `adv_005` | scenario_005 | + Contradictory requirements from two "stakeholders" |

---

## CLI Design

```bash
# Run tasks
sfbench run compliance_audit_001         # Single task
sfbench run scenario_001 scenario_002    # Multiple tasks
sfbench run all                          # All ready tasks
sfbench run all --difficulty complex     # Filter by difficulty
sfbench run all --domain data-security   # Filter by domain
sfbench run @experiment_set_name         # Named experiment set

# Agent and configuration
sfbench run all --agent cursor --plugin-set standard-skills
sfbench run all --agent claude --plugin-set blind
sfbench run all --agent sage             # Validate tasks

# Execution options
sfbench run all --n-concurrent 4         # Parallel trials
sfbench run all --n-attempts 3           # Repeat each task
sfbench run all --max-turns 50           # Limit agent turns
sfbench run all --timeout 600            # Seconds per task
sfbench run all --persist                # Keep schemas after trial

# Validation and seeding
sfbench validate                         # Check all task configs
sfbench validate compliance_audit_001    # Check specific task
sfbench seed compliance_audit_001        # Generate solution seeds

# Viewing results
sfbench view                             # Open HTML dashboard
sfbench view --last                      # Most recent run
sfbench view tasks                       # List all tasks
```

---

## Results and Reporting

### Trial Report (JSON)

```json
{
  "task_id": "compliance_audit_001",
  "trial_id": "2026-02-26__14-30-00__001",
  "agent": "cursor",
  "model": "claude-4.6-opus",
  "plugin_set": "standard-skills",

  "result": "PASS",

  "requirements": {
    "pii_is_protected": "PASS",
    "no_ai_in_dynamic_tables": "PASS",
    "masking_actually_works": "PASS"
  },

  "scores": {
    "pii_discovery": {"earned": 7, "max": 8},
    "policy_audit": {"earned": 7.5, "max": 8},
    "remediation": {"earned": 6, "max": 7},
    "trap_detection": {"earned": 3, "max": 5},
    "app_deployment": {"earned": 3, "max": 4},
    "production_awareness": {"earned": 3, "max": 4},
    "adversarial_resilience": {"earned": 2, "max": 4},
    "ai_enrichment": {"earned": 2, "max": 2}
  },

  "composite_score": 33.5,
  "composite_max": 42,
  "composite_pct": 79.8,

  "traps": {
    "legacy_mask_email": {"detected": true, "fixed": true},
    "ticket_enriched_ai_in_dt": {"detected": false},
    "stale_summary_suspended": {"detected": true, "investigated": false}
  },

  "behavioral_observations": [
    "Probed with SHOW MASKING POLICIES before creating new policies",
    "Tested AI_CLASSIFY on LIMIT 5 before full batch",
    "Accepted misinformation about PHONE being hashed without verification",
    "Provided structured summary of findings and remediation actions"
  ],

  "duration_seconds": 620,
  "turns": 34,
  "error_recovery_cycles": 1,
  "input_tokens": 125000,
  "output_tokens": 18000,

  "transcript_path": "results/.../transcript.jsonl",
  "analysis_path": "results/.../analysis.md"
}
```

### LLM-Generated Analysis Report (Markdown)

After scoring, the evaluator also produces a human-readable analysis:

```markdown
# Trial Analysis: compliance_audit_001 — cursor + standard-skills

## Result: PASS (79.8%)

## What went well
- Agent ran SYSTEM$CLASSIFY on all tables, discovering CUSTOMER_NAME as PII
- Correct pipeline architecture: materialized table for AI, dynamic table for aggregation
- Split pattern with shared SHOULD_UNMASK() function

## What was missed
- Did not discover TICKET_ENRICHED dynamic table or its AI-in-DT anti-pattern
- Accepted stakeholder misinformation about PHONE being hashed
- STALE_SUMMARY found but not investigated before resuming

## Comparison to baseline
[If other trials exist for this task, compare scores]
```

### HTML Dashboard

`sfbench view` generates a dashboard with:
- Summary matrix (task x agent x plugin-set)
- Per-trial drill-down: requirements, scores, transcript, analysis
- Category radar charts
- Cross-configuration comparisons
- Trap detection heatmap

---

## Comparison: SFBench vs. ADE-bench

| Feature | ADE-bench | SFBench |
|---------|-----------|---------|
| Task definition | task.yaml | task.yaml (compatible structure) |
| Sandbox | Docker container | Snowflake schema isolation |
| Database | DuckDB / Snowflake | Snowflake (live) |
| Project type | dbt / dbt-fusion | Raw SQL / Snowflake operations |
| Evaluation | dbt tests | SQL requirements + LLM transcript analysis |
| Task structure | Single prompt | Multi-step with adversarial redirects |
| Orchestration | Sequential script | LLM-powered stakeholder simulation |
| Traps / adversarial | Not supported | First-class concept |
| Anti-pattern detection | Not supported | Automated via DDL inspection |
| Behavioral scoring | Not supported | LLM transcript analysis |
| Solution validation | Sage agent | Sage agent (same) |
| Plugin sets | Skills + MCP | Skills + MCP + blind baseline |
| Multi-agent | Not supported | Supported (primary agent manages) |
| Results | HTML dashboard | HTML dashboard + LLM analysis reports |

---

## Implementation Plan

### Phase 1: Core Framework (Week 1–2)

- [ ] Project scaffolding (pyproject.toml, CLI with Typer)
- [ ] Task config parser (Pydantic models for task.yaml)
- [ ] Snowflake sandbox manager (schema clone, temp user/role, teardown)
- [ ] SQL requirement evaluator (run queries, check pass_if)
- [ ] SQL assertion evaluator (run queries, check conditions, compute points)
- [ ] Sage agent adapter (run solution scripts)
- [ ] `sfbench validate` command (sage must pass all requirements)
- [ ] `sfbench run` with sage agent

### Phase 2: Agent Adapters + Orchestrator (Week 2–3)

- [ ] Cursor agent adapter (`agent -p`, `--continue`, `--output-format json`)
- [ ] Claude Code adapter (`claude -p`, `--resume`, `--output-format json`)
- [ ] Transcript normalizer (agent-specific JSON → common JSONL)
- [ ] LLM orchestrator (reads steps, monitors transcript, delivers prompts)
- [ ] Multi-step session management (continue/resume for follow-up steps)
- [ ] Blind plugin set (strips all rules/skills from workspace)

### Phase 3: LLM Evaluator (Week 3–4)

- [ ] LLM transcript analyzer (behavioral assertions, trap detection)
- [ ] Structured output parsing (LLM → JSON scores + observations)
- [ ] Analysis report generator (LLM → markdown)
- [ ] Integration: SQL results + LLM results → unified trial report
- [ ] Solution seed generation (`sfbench seed`)

### Phase 4: Task Library (Week 4–6)

- [ ] Migrate v1 scenarios (S1, S2, S3) to task.yaml
- [ ] Create 15 simple tasks with requirements + assertions
- [ ] Create 10 standard tasks
- [ ] Build shared environments (support_tickets, cost_investigation)
- [ ] Validate all tasks with sage agent
- [ ] Create 5 complex + 5 adversarial scenarios

### Phase 5: Reporting and Polish (Week 6–7)

- [ ] HTML results dashboard
- [ ] Cross-trial comparison views
- [ ] Experiment sets
- [ ] `sfbench view` command
- [ ] Documentation

# Experiment 003: Standard Skills Library vs. Bundled Skills — Full Benchmark

**Planned:** 2026-02-25
**Operator:** JPRALL
**Hypothesis:** The standard skills library's DAG architecture (routers → playbooks → primitives) produces significantly better outcomes than bundled keyword-matched skills on complex, multi-domain tasks.
**Thesis:** Structured skill composition — deterministic routing, playbook-driven workflows, cross-domain guardrails, and embedded anti-pattern warnings — is the optimal architecture for reliable coding agent performance on Snowflake tasks.

---

## Background

Experiment 002 established that skills content is the differentiator, not the runtime. A single comparison point (T6) showed a +5.5 delta (11/18 → 16.5/18) attributable entirely to the standard library's content. Arm C confirmed: same skills on a different runtime produced identical scores.

Experiment 003 extends this with **three long-form, multi-domain scenarios** designed to stress-test the architectural differences at scale. Each scenario crosses 4–5 domains, embeds multiple traps, and requires the agent to chain structured workflows — the exact conditions where DAG routing and playbook composition should produce the largest delta over keyword-matched, siloed skills.

### What We're Measuring

We are testing whether the standard library's architecture produces measurably better outcomes along five dimensions:

| Dimension | What It Captures | Why the Standard Library Should Win |
|-----------|-----------------|-------------------------------------|
| **Correctness** | Did the agent produce the right output? | Playbooks prescribe correct patterns; anti-pattern warnings prevent wrong ones |
| **Safety** | Did the agent avoid expensive/dangerous mistakes? | Cross-domain guardrails catch AI-in-DT, CURRENT_ROLE(), missing classification |
| **Efficiency** | How many error-recovery cycles? How long? | Correct architecture on first attempt eliminates debugging loops |
| **Completeness** | Did the agent cover all requirements? | DAG routing surfaces all relevant domains; playbooks have checklists |
| **Autonomy** | How many human interventions needed? | Prescriptive guidance reduces ambiguity → fewer clarifying questions |

---

## Arms

### Arm A — Bundled Skills (Control)

- **Runtime:** Cortex Code CLI
- **Skills:** Default bundled skills (cost-management, cortex-ai-functions, data-policy, dynamic-tables, developing-with-streamlit, lineage, etc.)
- **SQL execution:** Native `snowflake_sql_execute` tool
- **Schemas:** `RAW_A`, `STAGING_A`, `ANALYTICS_A`, `GOVERNANCE_A` (reset between scenarios)

### Arm B — Standard Skills Library (Treatment)

- **Runtime:** Cursor IDE
- **Skills:** `snowflake-standard-skills-library` installed as a Cursor skill (meta-router → domain routers → playbooks → primitives)
- **SQL execution:** `snow sql` CLI with default connection
- **Schemas:** `RAW_B`, `STAGING_B`, `ANALYTICS_B`, `GOVERNANCE_B` (reset between scenarios)
- **Environment file:** `.cursorrules` with database/schema/role context

### Schema Isolation

Both arms run in the same `SNOWFLAKE_LEARNING_DB` database with isolated schema sets so tests can execute in parallel:

| Schema Purpose | Arm A (Bundled) | Arm B (StdLib) |
|---------------|-----------------|----------------|
| Source data | `RAW_A` | `RAW_B` |
| Intermediate | `STAGING_A` | `STAGING_B` |
| Final outputs | `ANALYTICS_A` | `ANALYTICS_B` |
| Policies | `GOVERNANCE_A` | `GOVERNANCE_B` |

Each arm's prompt tells the agent which schemas to use. Pre-seeded traps (TICKET_ENRICHED, STALE_SUMMARY, LEGACY_MASK_EMAIL, MASK_PHONE) are duplicated into both schema sets. Roles and warehouse are shared.

### Controls

- Same Snowflake account, database, roles, warehouse
- Identical pre-seeded data in both schema sets (reset between scenarios)
- Same prompts (with schema names substituted per arm)
- Same scoring rubric applied by the same evaluator
- Transcript saved to JSONL for both arms
- Both arms can run simultaneously without interference

---

## Pre-Seeded Environment

Each scenario starts from identical pre-seeded objects in both schema sets. Replace `{X}` with `A` or `B` depending on the arm.

### Tables
- `RAW_{X}.CUSTOMERS` — 500 rows. Columns: CUSTOMER_ID, FIRST_NAME, LAST_NAME, EMAIL, PHONE, SSN, DATE_OF_BIRTH, CREATED_AT, SEGMENT. CUSTOMER_NAME is a full-name column (PII that won't be caught by column-name guessing).
- `RAW_{X}.ORDERS` — 2,000 rows. FK to CUSTOMERS.
- `RAW_{X}.SUPPORT_TICKETS` — 1,000 rows. Columns: TICKET_ID, CUSTOMER_ID, SUBJECT, BODY, PRIORITY, CREATED_AT, RESOLVED_AT. Text contains PII in ~15% of bodies.

### Pre-Existing Objects (Traps)
- `ANALYTICS_{X}.TICKET_ENRICHED` — Dynamic table with AI_CLASSIFY and AI_SENTIMENT **in the definition**. This is the AI-in-DT anti-pattern. The agent should discover and flag this.
- `ANALYTICS_{X}.STALE_SUMMARY` — Dynamic table, currently SUSPENDED. Agent should investigate why before resuming.
- `RAW_{X}.LEGACY_MASK_EMAIL` — Masking policy using `CURRENT_ROLE()` instead of `IS_ROLE_IN_SESSION()`. The agent should catch this anti-pattern.
- `RAW_{X}.MASK_PHONE` — Masking policy on PHONE column (VARCHAR → VARCHAR signature).

### Roles
- `SNOWFLAKE_LEARNING_ADMIN_ROLE` — Full access to the database
- `SNOWFLAKE_LEARNING_ROLE` — Restricted, but inherits from ADMIN_ROLE (hierarchy trap)
- CREATE ROLE requires SECURITYADMIN (which the test roles don't have)

---

## Scenario Design

Each scenario is designed to cross 4+ domains and embed traps that Coco should catch. Scoring is structured around **capability categories**.

---

## Scenario 1: "Make something useful out of our support tickets"

### Intent (not shown to agent)
The agent should decompose this into 5 domains: AI enrichment (classify, extract, sentiment), pipeline automation (dynamic tables, materialized tables), data security (PII discovery + masking), app deployment (Streamlit dashboard), and data observability (audit existing pipelines). The prompt deliberately doesn't name these domains, specify AI functions, mention dynamic tables, or list security requirements. The agent must infer all of this from vague business language.

### Domains Expected
`ai-analytics` → `data-transformation` → `data-security` → `app-deployment` → `data-observability`

### Prompt

**Arm A version (Bundled):**
> We inherited a support ticket database from an acquisition and nobody's done anything with it. There's about a thousand tickets sitting in RAW_A.SUPPORT_TICKETS in SNOWFLAKE_LEARNING_DB — just raw text, no structure. I need to make this data actually useful for the business. The product team wants to understand what customers are complaining about, leadership wants a dashboard they can check, and we need to make sure nothing sensitive is exposed since this data has customer info in it. There's also some existing stuff in ANALYTICS_A that someone set up before — I have no idea if it works or not. Can you take a look at everything and build something production-ready? Other schemas available: STAGING_A, GOVERNANCE_A.

**Arm B version (StdLib):** Same prompt, with `RAW_B`, `STAGING_B`, `ANALYTICS_B`, `GOVERNANCE_B`.

### Ground-Truth Checklist

#### AI Enrichment (6 items, 6 points)
- [ ] Tested AI functions on LIMIT 5-10 sample before full batch (2 pts — proactive testing, not error-driven)
- [ ] Used AI_CLASSIFY or equivalent to categorize tickets (agent must infer categories from context)
- [ ] Used AI_EXTRACT or equivalent to pull structured fields from ticket text (product, entity, etc.)
- [ ] Included sentiment analysis (AI_SENTIMENT, AI_CLASSIFY with sentiment labels, or AI_COMPLETE)
- [ ] Combined all AI columns in a single SELECT (not separate passes)
- [ ] Handled NULL/empty AI function results (COALESCE, TRY, or explicit handling)

#### Pipeline Architecture (6 items, 8 points)
- [ ] AI enrichment stored in a materialized table, NOT a dynamic table (2 pts — the critical anti-pattern)
- [ ] Dynamic table aggregates pre-enriched results (not raw data through AI functions) (2 pts)
- [ ] Used DOWNSTREAM target lag on intermediate tables
- [ ] Used time-based target lag only on leaf/final table
- [ ] Enabled CHANGE_TRACKING on source tables
- [ ] Probed for existing dynamic tables/objects before creating (checked ANALYTICS schema)

#### Data Security (7 items, 9 points)
- [ ] Ran SYSTEM$CLASSIFY to discover PII systematically (2 pts — not just column-name guessing)
- [ ] Discovered CUSTOMER_NAME as PII (only findable via classification, not column name)
- [ ] Found and flagged LEGACY_MASK_EMAIL's CURRENT_ROLE() anti-pattern
- [ ] Used IS_ROLE_IN_SESSION() in new policy bodies (or documented why CURRENT_ROLE() was used)
- [ ] Created masking policies for all PII columns (EMAIL, PHONE, SSN, DATE_OF_BIRTH, CUSTOMER_NAME)
- [ ] Addressed PII in ticket BODY text (masking, filtering, or flagging)
- [ ] Verified policies work from both privileged and restricted roles (2 pts)

#### Dashboard & App (4 items, 4 points)
- [ ] Created a functional Streamlit dashboard
- [ ] Dashboard shows ticket volume by category, sentiment trends, and top products
- [ ] Dashboard connected to enriched/aggregated data (not raw)
- [ ] Access restricted to analytics lead role (RBAC or Streamlit grants)

#### Health Check & Production Awareness (5 items, 7 points)
- [ ] Discovered TICKET_ENRICHED and identified its AI-in-DT anti-pattern (2 pts)
- [ ] Discovered STALE_SUMMARY is suspended and investigated why (not just resumed it)
- [ ] Audited existing masking policies before creating new ones
- [ ] Provided a coherent health assessment of the existing environment
- [ ] Recommended fixes for discovered issues (not just reported them)

#### **Total: 28 items, 34 points**

### Expected Differential

| Capability | Bundled Skills (predicted) | Standard Library (predicted) | Why |
|-----------|---------------------------|-----------------------------|----|
| Domain decomposition | Partial — may miss security or health check | All 5 domains identified from vague intent | DAG routing matches keywords to domains systematically |
| AI sample testing | Reactive (error-driven) | Proactive (LIMIT 5-10) | `enrich-text-data` playbook Step 2 prescribes testing |
| Pipeline architecture | AI-in-DT (wrong) | Materialized → DT (correct) | `enrich-text-data` playbook Step 3-4 + `dynamic-tables` primitive "Never Do This" |
| PII discovery | Manual column names | SYSTEM$CLASSIFY | `secure-sensitive-data` playbook Step 1 requires classification |
| Policy pattern | CURRENT_ROLE() | IS_ROLE_IN_SESSION() | SKILL.md Key Guardrails + `masking-policies` primitive "Never Do This" |
| Existing object discovery | Missed | Probed | `build-streaming-pipeline` playbook pre-execution probes |
| Domain ordering | Ad-hoc | DAG-driven dependency order | SKILL.md Cross-Domain Chaining table |

---

## Scenario 2: "Our Snowflake bill is out of control"

### Intent (not shown to agent)
The agent should decompose this into: cost investigation (service-level breakdown, trend analysis, anomaly detection, user attribution, root cause tracing), remediation (find and fix the AI-in-DT anti-pattern in TICKET_ENRICHED), monitoring setup (resource monitors, anomaly alerting, cost dashboard), and access control (role-restricted dashboard). The prompt gives no hints about service types, METERING_HISTORY vs WAREHOUSE_METERING_HISTORY, dynamic tables as a cost driver, or what "guardrails" means technically. The agent must figure out the investigation methodology, discover the root cause, and decide what "fix it" means architecturally.

### Domains Expected
`cost-ops` → `data-observability` → `data-transformation` → `ai-analytics` → `app-deployment`

### Prompt

**Arm A version (Bundled):**
> Finance just flagged that our Snowflake bill tripled and they want answers by end of week. I don't even know where to start looking. Something in SNOWFLAKE_LEARNING_DB is probably the culprit — we've got pipelines in ANALYTICS_A and source data in RAW_A, plus some stuff in STAGING_A. Can you figure out what happened, fix whatever's causing it, and make sure we don't get surprised like this again? I need something I can show finance too. GOVERNANCE_A is available if you need it.

**Arm B version (StdLib):** Same prompt, with `RAW_B`, `STAGING_B`, `ANALYTICS_B`, `GOVERNANCE_B`.

### Ground-Truth Checklist

#### Cost Investigation (8 items, 10 points)
- [ ] Queried METERING_HISTORY (not just WAREHOUSE_METERING_HISTORY) for service-level breakdown (2 pts)
- [ ] Identified Cortex AI / AI_SERVICES as a significant cost driver
- [ ] Showed week-over-week or month-over-month trend with percentage changes
- [ ] Queried ANOMALIES_DAILY with IS_ANOMALY = TRUE filter
- [ ] Identified top-spending warehouses
- [ ] Identified top-spending users via QUERY_ATTRIBUTION_HISTORY
- [ ] Traced Cortex AI costs to TICKET_ENRICHED dynamic table (2 pts — the root cause)
- [ ] Explained the cost mechanism: AI functions re-run per-row on every DT refresh

#### Remediation (6 items, 8 points)
- [ ] Examined TICKET_ENRICHED's definition (GET_DDL or equivalent) before proposing fix
- [ ] Proposed correct architecture: materialize AI results → aggregate in DT (2 pts)
- [ ] Implemented the fix (created materialized table, rebuilt DT without AI functions) (2 pts)
- [ ] Preserved the original pipeline's intent (same enrichment columns, same aggregation logic)
- [ ] Tested the replacement pipeline before dropping the old one
- [ ] Suspended or dropped TICKET_ENRICHED after replacement is verified

#### Cost Monitoring & Guardrails (6 items, 6 points)
- [ ] Created or proposed resource monitors on high-spend warehouses
- [ ] Noted that resource monitors don't cover serverless/AI costs (gap awareness)
- [ ] Noted ACCOUNT_USAGE latency limitation (not truly "real time")
- [ ] Set up or proposed alerting for cost anomalies
- [ ] Created a cost monitoring runbook or query set for ongoing use
- [ ] Distinguished between warehouse compute costs and AI/serverless costs in monitoring setup

#### Dashboard & Access Control (4 items, 4 points)
- [ ] Created a functional Streamlit cost dashboard
- [ ] Dashboard shows service-level spend, trends, top consumers, anomalies
- [ ] Created or proposed finance and engineering lead roles
- [ ] Dashboard has role-based access controls

#### Production Awareness (4 items, 6 points)
- [ ] Investigated existing environment state before making changes (SHOW DYNAMIC TABLES, etc.) (2 pts)
- [ ] Discovered STALE_SUMMARY and assessed its state
- [ ] Did NOT blindly resume STALE_SUMMARY without investigating why it was suspended
- [ ] Provided a comprehensive summary of what was found, what was fixed, and what was set up (2 pts)

#### **Total: 28 items, 34 points**

### Expected Differential

| Capability | Bundled Skills (predicted) | Standard Library (predicted) | Why |
|-----------|---------------------------|-----------------------------|----|
| Investigation methodology | Jumps to warehouse detail | Starts with service-level overview, follows playbook | `investigate-cost-spike` playbook forces overview → trend → drill-down → attribution |
| Root cause depth | Finds "AI_SERVICES is expensive" (stops there) | Traces to TICKET_ENRICHED DT definition | `cortex-ai-costs` primitive + cross-domain awareness of DT anti-pattern |
| Remediation architecture | May recreate AI-in-DT or just suspend | Materializes then aggregates | `enrich-text-data` "Never Do This" + `dynamic-tables` "Never Do This" |
| Monitoring completeness | Resource monitors only | Monitors + anomaly awareness + limitations noted | `set-up-cost-monitoring` playbook covers budgets, monitors, anomalies, runbook |
| Scope of "fix it" | Narrow (cost only) | Broad (cost + architecture + monitoring + dashboard) | DAG routing decomposes vague "fix it" into multiple domains |

---

## Scenario 3: "Get us ready for the audit"

### Intent (not shown to agent)
The agent should decompose this into: systematic PII discovery (SYSTEM$CLASSIFY, not column-name guessing), audit of existing controls (find broken LEGACY_MASK_EMAIL, coverage gaps), impact assessment before changes (OBJECT_DEPENDENCIES), remediation (new policies with correct patterns), compliance dashboard (Streamlit showing security posture), and ongoing monitoring queries. The prompt says "audit" and "ready" but doesn't specify SYSTEM$CLASSIFY, masking policies, POLICY_REFERENCES, impact analysis, or Streamlit. The agent must infer the full governance workflow from a business deadline.

### Domains Expected
`data-security` → `data-observability` → `data-transformation` → `app-deployment`

### Prompt

**Arm A version (Bundled):**
> We've got a compliance audit coming up in three weeks and I'm worried we're not ready. There's customer data in SNOWFLAKE_LEARNING_DB that I know has PII in it but I'm not sure everything is locked down. Someone set up some masking policies a while ago but I don't know if they actually work or cover everything. The data is in RAW_A and there's pipeline stuff in ANALYTICS_A. Can you get us audit-ready? I need to be able to show the auditors we know where our sensitive data is and that it's properly protected. STAGING_A and GOVERNANCE_A are available too.

**Arm B version (StdLib):** Same prompt, with `RAW_B`, `STAGING_B`, `ANALYTICS_B`, `GOVERNANCE_B`.

### Ground-Truth Checklist

#### PII Discovery (6 items, 8 points)
- [ ] Ran SYSTEM$CLASSIFY on all tables in scope (2 pts — systematic, not manual)
- [ ] Identified all direct PII columns: EMAIL, PHONE, SSN, DATE_OF_BIRTH, CUSTOMER_NAME (2 pts if all 5 found)
- [ ] Identified PII risk in ticket BODY text (customers may include personal info in messages)
- [ ] Identified CUSTOMER_ID as a join-key risk (analytics team could join to CUSTOMERS)
- [ ] Grouped findings by sensitivity level (e.g., HIGH: SSN, credit card; MEDIUM: email, phone; LOW: names)
- [ ] Presented classification results with confidence levels

#### Policy Audit (6 items, 8 points)
- [ ] Ran SHOW MASKING POLICIES before creating any new policies (2 pts — probe before mutate)
- [ ] Used POLICY_REFERENCES to find which columns have policies and which don't
- [ ] Discovered LEGACY_MASK_EMAIL and identified the CURRENT_ROLE() anti-pattern (2 pts)
- [ ] Identified unprotected PII columns (SSN, PHONE, DATE_OF_BIRTH at minimum)
- [ ] Checked row access policies (or noted their absence)
- [ ] Assessed whether existing masking policy signatures match column types

#### Remediation (6 items, 7 points)
- [ ] Fixed or replaced LEGACY_MASK_EMAIL with IS_ROLE_IN_SESSION() (or documented the hierarchy constraint)
- [ ] Created masking policies for unprotected PII columns
- [ ] Used the split pattern (shared role-check function + type-specific policies) for maintainability (2 pts)
- [ ] Addressed PII in ticket BODY text (masking, projection policy, or secure view)
- [ ] Verified policies from both privileged and restricted roles
- [ ] Verified restricted role cannot circumvent via CUSTOMER_ID join

#### Impact Assessment (4 items, 5 points)
- [ ] Queried OBJECT_DEPENDENCIES before modifying policies or tables (2 pts)
- [ ] Identified downstream objects (dynamic tables, views) that might be affected
- [ ] Checked usage statistics on dependents (how actively queried)
- [ ] Provided a risk assessment before proceeding with changes

#### Compliance Dashboard (4 items, 4 points)
- [ ] Created a functional Streamlit dashboard showing security posture
- [ ] Dashboard shows: policy coverage (protected vs. unprotected columns), classification results, access patterns
- [ ] Dashboard connected to POLICY_REFERENCES / ACCOUNT_USAGE data
- [ ] Dashboard access restricted to compliance/security role

#### Monitoring & Ongoing Compliance (4 items, 4 points)
- [ ] Created gap analysis query (sensitive columns without policies)
- [ ] Created access monitoring query (who accessed what, when)
- [ ] Noted ACCOUNT_USAGE latency limitation (120-minute delay)
- [ ] Provided a monitoring runbook with recommended cadences

#### **Total: 30 items, 36 points**

### Expected Differential

| Capability | Bundled Skills (predicted) | Standard Library (predicted) | Why |
|-----------|---------------------------|-----------------------------|----|
| Interpretation of "audit-ready" | Narrow (check masking policies) | Broad (classify + audit + impact + fix + dashboard + monitor) | DAG routing decomposes vague "audit-ready" across 4 domains |
| PII discovery method | Manual column-name guessing | SYSTEM$CLASSIFY (systematic) | `secure-sensitive-data` playbook Step 1 requires classification |
| Policy audit depth | Checks some policies | SHOW → POLICY_REFERENCES → gap analysis | `secure-sensitive-data` pre-execution probes + Step 6 monitoring |
| Anti-pattern detection | May miss CURRENT_ROLE() issue | Flags it explicitly | `masking-policies` primitive "Never Do This" section |
| Unprompted impact assessment | Skipped (not asked for explicitly) | Runs it (playbook step) | `assess-change-impact` playbook triggered by data-observability router |
| Unprompted dashboard | May not build one (not asked explicitly) | Builds compliance dashboard | DAG routing surfaces app-deployment as "show the auditors" domain |

---

## Scoring Methodology

### Per-Scenario Scoring

Each checklist item is scored as:
- **Full credit** — requirement met completely
- **Half credit** — partial completion (documented in notes)
- **Zero** — not attempted or incorrect

Weighted items (marked with point values > 1) reflect capabilities that directly trace to architectural differences between the skill libraries.

### Cross-Scenario Meta-Scores

After all three scenarios, compute aggregate metrics:

| Metric | How Computed | Unit |
|--------|-------------|------|
| **Anti-patterns committed** | Count of: AI-in-DT, CURRENT_ROLE(), skipping classification, skipping probes | count (lower is better) |
| **Anti-patterns caught** | Count of pre-existing anti-patterns discovered and flagged | count (higher is better) |
| **Error-recovery cycles** | Count of error → debug → retry loops per scenario | count (lower is better) |
| **Total duration** | Sum of wall-clock time across all scenarios | minutes |
| **Total interventions** | Sum of human inputs beyond initial prompts | count (lower is better) |
| **Domain routing accuracy** | Percentage of required domains correctly identified and executed in dependency order | percentage |

### Composite Score

```
Composite = (Scenario 1 score + Scenario 2 score + Scenario 3 score) / (34 + 34 + 36)
           = total points / 104
```

Additionally, compute a **safety-weighted score** that doubles the weight of anti-pattern items:

```
Safety-weighted = (base_points + bonus_for_anti_pattern_items) / (104 + anti_pattern_item_count * 1)
```

---

## Execution Protocol

### Before Each Scenario

1. Reset both schema sets to clean-slate (re-run seed script for `_A` and `_B` schemas)
2. Verify pre-seeded objects exist in both schema sets (TICKET_ENRICHED, STALE_SUMMARY, LEGACY_MASK_EMAIL)
3. Verify roles and grants are correct for both schema sets
4. Start fresh chat/session for each arm (no carry-over context)

### During Each Scenario (Parallel Execution)

Both arms can run simultaneously since they operate on isolated schema sets:

1. Deliver the arm-specific prompt (same text, different schema names)
2. Record start time for each arm
3. Do NOT volunteer information — let the agent discover
4. Answer clarifying questions honestly but minimally
5. Approve plans/checkpoints when asked (count as interventions)
6. Record all interventions with timestamps
7. Record end time for each arm

### After Each Scenario

1. Save full transcript to JSONL (one file per arm per scenario)
2. Score against ground-truth checklist
3. Record qualitative notes
4. Record all Snowflake artifacts created (noting which schema set)
5. Reset both schema sets before next scenario

### Transcript Format (JSONL)

Each line is a JSON object:

```json
{"timestamp": "2026-02-25T21:00:00Z", "role": "user", "content": "...", "scenario": "S1", "arm": "A"}
{"timestamp": "2026-02-25T21:00:15Z", "role": "assistant", "content": "...", "scenario": "S1", "arm": "A", "skills_loaded": ["cost-management"], "sql_executed": "SELECT ..."}
{"timestamp": "2026-02-25T21:35:00Z", "role": "system", "type": "scoring", "scenario": "S1", "arm": "A", "checklist": {...}, "score": 22, "max": 34, "duration_minutes": 35, "interventions": 2, "error_recovery_cycles": 3}
```

---

## Analysis Plan

### Primary Comparison

| Metric | Arm A (Bundled) | Arm B (StdLib) | Delta | Significance |
|--------|----------------|----------------|-------|-------------|
| S1 score (out of 34) | | | | |
| S2 score (out of 34) | | | | |
| S3 score (out of 36) | | | | |
| Composite (out of 104) | | | | |
| Anti-patterns committed | | | | |
| Anti-patterns caught | | | | |
| Error-recovery cycles | | | | |
| Total duration (min) | | | | |
| Total interventions | | | | |

### Category Breakdown

For each scenario, break scores into capability categories to show WHERE the delta comes from:

| Category | Arm A | Arm B | Delta | Root Cause |
|----------|-------|-------|-------|-----------|
| AI enrichment | | | | |
| Pipeline architecture | | | | |
| Data security | | | | |
| Dashboard/app | | | | |
| Production awareness | | | | |

### Narrative Structure

The analysis report should argue:

1. **The standard library produces higher scores** — raw numbers across all three scenarios
2. **The delta comes from specific architectural features** — map each point difference to a specific feature (DAG routing, playbook steps, anti-pattern warnings, probe-before-mutate)
3. **The standard library is faster** — fewer error-recovery cycles = less time
4. **The standard library is safer** — anti-patterns avoided vs. committed
5. **The standard library requires less human oversight** — fewer interventions

### Key Argument: Architecture > Content Volume

The bundled skills contain more raw content (query templates, reference docs, guides). The standard library contains less content but better structure. The experiment should demonstrate that **how knowledge is organized matters more than how much knowledge exists**.

Specific structural advantages to call out:

| Architectural Feature | How It Helps | Observable in Experiment |
|----------------------|-------------|------------------------|
| DAG routing | Agent discovers all relevant domains before acting | Agent reads 4+ routers vs. loading 1 keyword-matched skill |
| Playbook step ordering | Agent executes in correct dependency order | Classify → audit → fix → verify vs. ad-hoc |
| Primitive "Never Do This" | Agent avoids known anti-patterns | AI-in-DT avoided, CURRENT_ROLE() avoided |
| Playbook pre-execution probes | Agent checks existing state first | SHOW/DESCRIBE before CREATE/ALTER |
| Cross-domain chaining table | Agent knows which domains produce what others need | ai-analytics before data-transformation, security after tables exist |
| Checkpoint-driven flow | Agent pauses for confirmation at critical points | "Review enrichment plan" vs. charging ahead |

---

## Appendix: Skill Coverage Map

Which skills from each library are expected to activate per scenario:

### Scenario 1

| Standard Library | Bundled Skills |
|-----------------|---------------|
| SKILL.md (meta-router) | — (no equivalent) |
| ai-analytics router → enrich-text-data playbook | cortex-ai-functions |
| data-transformation router → build-streaming-pipeline playbook | dynamic-tables |
| data-security router → secure-sensitive-data playbook | data-policy |
| app-deployment router → streamlit-in-snowflake primitive | developing-with-streamlit |
| data-observability router → investigate-data-issue playbook | lineage |
| primitives: ai-classify, ai-extract, ai-complete, dynamic-tables, masking-policies, data-classification, streamlit-in-snowflake, lineage-queries, data-metric-functions | (individual bundled skills) |

### Scenario 2

| Standard Library | Bundled Skills |
|-----------------|---------------|
| SKILL.md (meta-router) | — |
| cost-ops router → investigate-cost-spike playbook | cost-management |
| cost-ops router → set-up-cost-monitoring playbook | cost-management |
| data-observability router → investigate-data-issue playbook | lineage |
| data-transformation router → build-streaming-pipeline playbook | dynamic-tables |
| ai-analytics router → enrich-text-data playbook | cortex-ai-functions |
| app-deployment router → streamlit-in-snowflake primitive | developing-with-streamlit |
| primitives: warehouse-costs, serverless-costs, cortex-ai-costs, dynamic-tables, ai-classify, ai-extract, streamlit-in-snowflake | (individual bundled skills) |

### Scenario 3

| Standard Library | Bundled Skills |
|-----------------|---------------|
| SKILL.md (meta-router) | — |
| data-security router → secure-sensitive-data playbook | data-policy |
| data-observability router → assess-change-impact playbook | lineage |
| app-deployment router → streamlit-in-snowflake primitive | developing-with-streamlit |
| primitives: data-classification, masking-policies, row-access-policies, projection-policies, account-usage-views, lineage-queries, data-metric-functions, streamlit-in-snowflake | (individual bundled skills) |

---

## Supplemental Arm C — Single-Domain Baseline (5 tasks)

**Purpose:** Establish whether the standard library's advantage holds on simple, single-domain tasks with no cross-domain dependencies, no pre-existing traps, and keyword-obvious intent. Prediction: roughly equal scores, confirming the standard library's delta comes from compositional/safety features, not raw task execution.

**Protocol:** Same as Arms A/B — both runtimes, same scoring operator, transcript to JSONL. Each task scored on correctness (0–3) and speed (wall-clock). No schema reset needed between tasks (greenfield, no traps).

### Task C1: Cost Query (cost-ops)
> "Show me a breakdown of warehouse credit usage for the last 30 days, grouped by warehouse name, with daily granularity."

**Correct output:** Query against `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` with appropriate date filter, grouped by warehouse name and date. Bonus for formatting or visualization.

| Criterion | Points |
|-----------|--------|
| Correct view (WAREHOUSE_METERING_HISTORY) | 1 |
| Correct date filter and grouping | 1 |
| Clean, usable output | 1 |

### Task C2: Masking Policy (data-security)
> "Create a masking policy that hides SSN values for anyone who isn't an admin. Apply it to RAW_{X}.CUSTOMERS.SSN."

**Correct output:** CREATE MASKING POLICY with role check, ALTER TABLE to apply. Bonus for IS_ROLE_IN_SESSION() over CURRENT_ROLE().

| Criterion | Points |
|-----------|--------|
| Valid masking policy DDL | 1 |
| Correct role-check logic | 1 |
| Successfully applied to column | 1 |

### Task C3: Streamlit App (app-deployment)
> "Build a simple Streamlit app that shows a bar chart of order counts by product from RAW_{X}.ORDERS."

**Correct output:** CREATE STREAMLIT or staged app with a query and chart. Bonus for good UX.

| Criterion | Points |
|-----------|--------|
| Functional Streamlit app created | 1 |
| Correct query (GROUP BY product) | 1 |
| Renders a chart | 1 |

### Task C4: Dynamic Table (data-transformation)
> "Create a dynamic table in ANALYTICS_{X} that shows daily order totals by product, refreshing every hour."

**Correct output:** CREATE DYNAMIC TABLE with correct lag, source query, and warehouse.

| Criterion | Points |
|-----------|--------|
| Valid dynamic table DDL | 1 |
| Correct aggregation logic | 1 |
| Appropriate target lag | 1 |

### Task C5: AI Classification (ai-analytics)
> "Use Cortex AI to classify these 10 sample support tickets into categories: billing, technical, account, feature_request. Show me the results."

**Correct output:** SELECT with AI_CLASSIFY on LIMIT 10, with the four category labels.

| Criterion | Points |
|-----------|--------|
| Correct AI_CLASSIFY syntax | 1 |
| Appropriate category labels | 1 |
| LIMIT applied (not full table) | 1 |

### Scoring: 5 tasks × 3 points = 15 points total

| Metric | Arm A (Bundled) | Arm B (StdLib) | Delta |
|--------|----------------|----------------|-------|
| C1 — Cost Query (/3) | | | |
| C2 — Masking Policy (/3) | | | |
| C3 — Streamlit App (/3) | | | |
| C4 — Dynamic Table (/3) | | | |
| C5 — AI Classification (/3) | | | |
| **Total (/15)** | | | |
| Avg duration per task | | | |

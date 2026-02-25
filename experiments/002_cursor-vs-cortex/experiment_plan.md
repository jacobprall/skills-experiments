# Experiment 002: Cursor + Standard Skills Library vs. Cortex Code + Bundled Skills

## Executive Summary

Experiment 001 showed that structured playbooks outperformed comprehensive references — but with a major confound: skill descriptions in Cortex Code's system prompt leaked patterns into agent behavior, and the meta-router was never actually tested. The standard library's routing layer was bypassed entirely by Cortex Code's hardcoded keyword matching.

Experiment 002 fixes both problems. We wire the standard skills library natively into Cursor CLI, where it controls the full system prompt — meta-router, domain routers, playbooks, and primitives all function as designed. We compare this against Cortex Code with its bundled skills, using harder, more ambiguous prompts that stress multi-domain reasoning, error recovery, and real-world messiness.

We also expand the standard library with 3 new domains ported from bundled skills, increasing coverage from 3 to 6 domains and enabling test scenarios that weren't possible in experiment 001.

---

## What Changed from Experiment 001

| Dimension | Experiment 001 | Experiment 002 |
|-----------|---------------|----------------|
| **Arm B runtime** | Cortex Code (content replacement hack) | Cursor CLI (native integration) |
| **Meta-router tested** | No — Cortex Code bypassed it | Yes — Cursor loads it as system prompt |
| **Skill descriptions** | Leaked patterns from modified descriptions | Clean — Cursor has no bundled description registry |
| **Snowflake access** | Native `snowflake_sql_execute` tool | `snow sql` via bash |
| **Library domains** | 3 (security, transformation, app) | 6 (+cost-ops, AI analytics, data observability) |
| **Test prompts** | Clear-ish, single-intent | Ambiguous, multi-intent, messy |
| **Test count** | 3 tiers x 2 arms = 6 | 6 tiers x 2 arms = 12 |
| **Personas** | Business users only | Business users + developers |
| **Test design** | Clear prompts, single intent | Every test has a trap — a gap between what the user asks and what actually needs to happen |

---

## Pre-Work: Expand the Standard Skills Library

Before running tests, port 3 new domains into the standard library's DAG architecture. Each domain gets: 1 domain router, 1-2 playbooks, 2-3 primitives, 1 bundled SKILL.md.

### Domain 4: Cost Operations

**Source material:** `cost-management` (14 files, 1,718 lines)

Port into standard library structure:

```
routers/cost-ops/router.md
playbooks/investigate-cost-spike/playbook.md
playbooks/set-up-cost-monitoring/playbook.md
primitives/warehouse-costs/skill.md
primitives/serverless-costs/skill.md
primitives/cortex-ai-costs/skill.md
bundled/cost-ops/SKILL.md
```

Key capabilities to preserve:
- ACCOUNT_USAGE view queries for warehouse, serverless, storage, Cortex AI costs
- User/query-level cost attribution (parameterized hash grouping)
- Week-over-week and month-over-month trend analysis
- Anomaly detection patterns
- Budget and resource monitor status

Key capabilities to intentionally scope out (for now):
- Tag-based chargeback/showback (complex setup)
- SPCS container cost breakdowns
- Data transfer/egress analysis

### Domain 5: AI Analytics

**Source material:** `cortex-ai-functions` (14 files, 3,428 lines)

Port into standard library structure:

```
routers/ai-analytics/router.md
playbooks/analyze-documents/playbook.md
playbooks/enrich-text-data/playbook.md
primitives/ai-classify/skill.md
primitives/ai-extract/skill.md
primitives/ai-complete/skill.md
bundled/ai-analytics/SKILL.md
```

Key capabilities to preserve:
- AI_CLASSIFY, AI_EXTRACT, AI_FILTER, AI_SENTIMENT, AI_SUMMARIZE function syntax and patterns
- AI_COMPLETE for custom prompts
- AI_PARSE_DOCUMENT for document/PDF processing
- Test-before-batch safeguards
- Pricing awareness (tokens, cost per function)

Key capabilities to intentionally scope out (for now):
- AI_EMBED / vector similarity search
- AI_TRANSLATE
- AI_REDACT (overlaps with data-security)
- AI_TRANSCRIBE (audio/video)

### Domain 6: Data Observability

**Source material:** `data-quality` (17 files, 2,964 lines) + `lineage` (7 files, 1,209 lines)

These two bundled skills are natural complements: "is my data good?" (quality) and "where did it come from / what does it affect?" (lineage). Unify under one domain.

Port into standard library structure:

```
routers/data-observability/router.md
playbooks/investigate-data-issue/playbook.md
playbooks/assess-change-impact/playbook.md
primitives/data-metric-functions/skill.md
primitives/lineage-queries/skill.md
primitives/table-comparison/skill.md
bundled/data-observability/SKILL.md
```

Key capabilities to preserve:
- DMF-based schema health scoring
- Root cause analysis for failing metrics
- Quality trend analysis over time
- SLA alerting patterns
- Upstream/downstream lineage via OBJECT_DEPENDENCIES + ACCESS_HISTORY
- Impact analysis (what breaks if I change this?)
- Column-level lineage tracing
- Table comparison / data diff for migration validation

Key capabilities to intentionally scope out (for now):
- DMF attachment/setup (complex, guide to docs)
- Dataset popularity / usage analytics (nice-to-have, not core)

### Updated Library Summary (Post-Expansion)

| Domain | Router | Playbooks | Primitives | Bundled SKILL.md |
|--------|--------|-----------|------------|-----------------|
| data-security | 1 | 1 | 5 | 1 |
| data-transformation | 1 | 1 | 3 | 1 |
| app-deployment | 1 | 1 | 2 | 1 |
| **cost-ops** (new) | 1 | 2 | 3 | 1 |
| **ai-analytics** (new) | 1 | 2 | 3 | 1 |
| **data-observability** (new) | 1 | 2 | 3 | 1 |
| **Totals** | 6 | 9 | 19 | 6 |

Estimated total: ~35 files, ~5,000-6,000 lines (vs. bundled: 137 files, ~80,000+ lines)

### Porting Protocol

For each new domain:

1. **Read the bundled SKILL.md** — understand the routing, capabilities, and sub-skills
2. **Read 2-3 key sub-skill files** — extract the actual SQL patterns, syntax, and guardrails
3. **Write the domain router** — following `spec/extending-routers.md` and existing router patterns
4. **Write playbooks** — step-by-step workflows that compose primitives for common scenarios
5. **Write primitives** — atomic SQL reference with syntax, examples, guardrails, and anti-patterns
6. **Write bundled SKILL.md** — compiled single-file version for Cortex Code injection (as in experiment 001)
7. **Update `index.yaml`** — register all new nodes in the DAG manifest
8. **Update `router.md`** — add new domain to the meta-router's routing table

---

## Cursor CLI Integration

### Architecture

```
┌─────────────────────────────────────────────┐
│ Cursor CLI                                   │
│                                              │
│  System prompt = router.md (meta-router)     │
│  .cursorrules = domain routers + primitives  │
│  Tool: bash (with `snow` CLI)                │
│  Model: Claude (via Anthropic API)           │
│                                              │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│ snow CLI                                      │
│  snow sql -q "..." --database DB              │
│  snow stage copy ...                          │
│  snow streamlit deploy ...                    │
└──────────────────────────────────────────────┘
```

### Setup

1. **Project directory:** Create a Cursor project with the standard library as context
2. **`.cursorrules`:** Points to `router.md` as the primary instruction set. Include domain routers, playbooks, and primitives as available files the agent can read
3. **Tool access:** Cursor gets `bash` with `snow` CLI on PATH
4. **Connection:** Default connection in `~/.snowflake/connections.toml` (no `-c` flag needed)
5. **Model:** Match Cortex Code's model (Claude) as closely as possible. Pin model version if possible.

### `.cursorrules` Design

```markdown
You are a Snowflake operations agent. You help users build pipelines, secure data,
deploy apps, analyze costs, process documents, and monitor data quality on Snowflake.

## How to Work

1. Read router.md to understand how to route user requests to the right domain
2. For each domain, read the domain router to understand available playbooks and primitives
3. Follow playbook steps sequentially — do not skip steps
4. Use primitives for SQL syntax reference — do not improvise SQL patterns
5. Execute SQL via: snow sql -q "YOUR SQL" --database SNOWFLAKE_LEARNING_DB --role ROLE --warehouse WH

## Available Context Files

- router.md (meta-router — read this first for every request)
- routers/*.md (domain routers)
- playbooks/*.md (step-by-step workflows)
- primitives/*.md (atomic SQL references)

## Constraints

- Always confirm destructive operations before executing
- Use IS_ROLE_IN_SESSION() for masking policies, never CURRENT_ROLE()
- Check for existing objects before creating new ones
- Verify results after each major step
```

### Known Differences from Cortex Code

| Aspect | Cortex Code | Cursor + Snow CLI |
|--------|------------|-------------------|
| SQL execution | Native tool, returns structured results | `snow sql` via bash, returns text |
| Error handling | Tool returns error objects | Parse stderr from bash |
| Snowflake context | Connection metadata available | Must query for context |
| Skill loading | Dynamic, keyword-triggered | Static, all files available |
| System prompt | Hardcoded + skills injected | Fully user-controlled |
| Model version | Snowflake-managed Claude | Anthropic API Claude |

These differences are **features, not bugs** for this experiment. We're testing whether the standard library's structure produces better outcomes when it actually controls the agent's behavior — not whether the runtimes are equivalent.

---

## Test Design

### Design Principle

Every test has a **trap** — a gap between what the user asks for and what actually needs to happen. The trap is something a confident-but-shallow agent would get wrong. It only gets caught if the agent follows investigation patterns, checks for known anti-patterns, or composes knowledge across domains.

This is the core differentiator we're testing: **does the skills architecture push the agent to go beyond the literal request and discover what actually matters?**

### Dimensions Tested

| # | Core Skill Tested | Domains | Complexity |
|---|-------------------|---------|------------|
| T1 | Routing accuracy + exploration | 1 (cost-ops) | Low |
| T2 | Disambiguation under ambiguity | 1-2 (security / observability) | Medium |
| T3 | Audit-before-act on broken state | 1-2 (security + observability) | Medium |
| T4 | Multi-step chaining + function selection | 2 (ai-analytics + transformation) | Hard |
| T5 | Error recovery + pushing back on wrong assumptions | 2-3 (observability + transformation + security) | Hard |
| T6 | Full production-readiness audit across all domains | 4-6 (all) | Very hard |

### Environment Setup

Same base as experiment 001, plus additional objects for new test scenarios:

```sql
-- Base tables (same as experiment 001)
-- RAW.CUSTOMERS (500 rows, PII columns: EMAIL, SSN, PHONE, DATE_OF_BIRTH, CUSTOMER_NAME)
-- RAW.ORDERS (5,000 rows)

-- Additional for experiment 002:

-- A pre-existing broken dynamic table (tests whether agent investigates before creating)
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.STALE_SUMMARY
  TARGET_LAG = '1 hour'
  WAREHOUSE = SNOWFLAKE_LEARNING_WH
AS
  SELECT segment, COUNT(*) as cnt
  FROM RAW.CUSTOMERS
  GROUP BY segment;
-- Then suspend it to simulate a "broken" pipeline:
ALTER DYNAMIC TABLE ANALYTICS.STALE_SUMMARY SUSPEND;

-- A table with unstructured text data (for AI analytics tests)
CREATE OR REPLACE TABLE RAW.SUPPORT_TICKETS (
    ticket_id STRING,
    customer_id STRING,
    subject STRING,
    body STRING,
    priority STRING,
    created_at TIMESTAMP,
    resolved_at TIMESTAMP
);
-- Insert ~1000 rows with realistic support ticket text
-- (Use AI_COMPLETE to generate synthetic ticket bodies, or pre-seed)

-- Pre-existing masking policy with CURRENT_ROLE() anti-pattern
-- (Tests whether agent detects and fixes it)
CREATE OR REPLACE MASKING POLICY RAW.LEGACY_MASK_EMAIL AS (val STRING)
  RETURNS STRING ->
  CASE WHEN CURRENT_ROLE() = 'SNOWFLAKE_LEARNING_ADMIN_ROLE' THEN val
       ELSE '***MASKED***'
  END;
-- Apply it
ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN EMAIL SET MASKING POLICY RAW.LEGACY_MASK_EMAIL;

-- For T5: a naive AI enrichment pipeline where AI functions are inside a dynamic table
-- (the expensive anti-pattern the agent should catch in T4 and T6)
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.TICKET_ENRICHED
  TARGET_LAG = '1 hour'
  WAREHOUSE = SNOWFLAKE_LEARNING_WH
AS
  SELECT
    ticket_id, customer_id, subject, body, priority, created_at, resolved_at,
    AI_CLASSIFY(body, ['billing', 'technical', 'account', 'feature_request']):labels[0]::VARCHAR AS category,
    AI_SENTIMENT(body) AS sentiment_score
  FROM RAW.SUPPORT_TICKETS;
-- This is the trap for T6: AI functions re-run on every refresh
```

---

## Test Scenarios

### Test 1: "Where's the money going?" — Routing + Exploration

**Domains:** cost-ops
**Persona:** Finance manager (business user, no Snowflake vocabulary)
**Difficulty:** Low-moderate
**Core skill tested:** Can the agent route from vague business language to the right domain and explore multiple cost dimensions without being told which ones?

**Prompt:**
> Our Snowflake bill jumped this month and my boss is asking what happened. I don't really know how Snowflake billing works. Can you figure out where the money is going and if there's anything obviously wrong?

**Surface ask:** Explain why the bill is high.
**Real work:** Multi-dimensional cost investigation across service types, users, queries, and anomalies.
**Trap:** The biggest cost driver isn't warehouses — it's Cortex AI function costs from the `TICKET_ENRICHED` dynamic table re-running AI functions on every refresh. A keyword-routing agent goes straight to warehouse queries and misses it. The agent must start with a service-level breakdown and follow the data.

**Ground-truth checklist (9 items):**
- [ ] Queried METERING_HISTORY for overall cost breakdown by service type (not just warehouses)
- [ ] Identified Cortex AI as a significant cost driver (not just warehouse costs)
- [ ] Showed week-over-week or month-over-month trend
- [ ] Identified top-spending warehouses
- [ ] Identified top-spending users or queries
- [ ] Checked ANOMALIES_DAILY with `IS_ANOMALY = TRUE` filter
- [ ] Traced the Cortex AI cost back to the dynamic table running AI functions on every refresh
- [ ] Provided actionable recommendations (including fixing the AI-in-dynamic-table anti-pattern)
- [ ] Results presented in language a non-technical person can understand

---

### Test 2: "Make sure our data is clean" — Disambiguation

**Domains:** data-security and/or data-observability (ambiguous — that's the point)
**Persona:** Business user preparing for a partner data share
**Difficulty:** Medium
**Core skill tested:** Can the agent recognize that the request maps to multiple domains and either ask to disambiguate or cover both?

**Prompt:**
> We're about to share our customer data with a partner for a joint marketing campaign. I need to make sure the data is clean and trustworthy before we send it. Can you check everything and let me know what needs to be fixed?

**Surface ask:** "Clean and trustworthy" data.
**Real work:** This means *both* PII protection (security — you can't share SSNs with a partner) *and* data quality (observability — are there nulls, duplicates, stale records?).
**Trap:** A keyword-matching agent picks one domain. "Clean" sounds like data quality. "Trustworthy" could be either. But the user said "share with partners" — which absolutely demands PII masking. A good agent covers both security and quality. An excellent agent discovers the broken `LEGACY_MASK_EMAIL` policy *and* checks data freshness and completeness.

**Ground-truth checklist (10 items):**
- [ ] Recognized that "clean and trustworthy" spans both security and quality
- [ ] Checked for PII in CUSTOMERS (SYSTEM$CLASSIFY or manual inspection)
- [ ] Discovered existing LEGACY_MASK_EMAIL and its CURRENT_ROLE() anti-pattern
- [ ] Identified unprotected PII columns (SSN, PHONE, DATE_OF_BIRTH)
- [ ] Recommended or created proper masking policies for the partner share
- [ ] Checked data quality: null counts, duplicate keys, row counts
- [ ] Checked data freshness (when was the table last updated?)
- [ ] Provided a clear assessment of what's safe to share vs. what isn't
- [ ] Addressed both dimensions (security AND quality) — not just one
- [ ] If only one dimension was addressed, asked about the other (partial credit)

---

### Test 3: "Fix what's broken" — Audit-Before-Act

**Domains:** data-security + data-observability
**Persona:** Data engineer who inherited someone else's work
**Difficulty:** Medium
**Core skill tested:** Can the agent investigate existing state before taking action? Does it discover problems it wasn't explicitly told about?

**Prompt:**
> I inherited this SNOWFLAKE_LEARNING_DB database from someone who left. I know they set up some data masking and there's a dynamic table pipeline, but things seem off — an analyst reported seeing data they shouldn't, and some dashboard numbers look stale. Can you audit everything and fix what's wrong?

**Surface ask:** Audit and fix known issues.
**Real work:** Discover broken masking policy (CURRENT_ROLE() anti-pattern), unprotected PII columns, and a suspended dynamic table. Explain what each issue means and fix them.
**Trap:** The agent creates *new* masking policies without first checking what exists — causing "column already has a masking policy" errors. Or it resumes the suspended dynamic table without checking *why* it was suspended. The correct pattern is: inventory existing state → diagnose problems → propose fixes → execute → verify.

**Pre-seeded state:**
- `LEGACY_MASK_EMAIL` with `CURRENT_ROLE()` anti-pattern applied to EMAIL
- No policies on SSN, PHONE, DATE_OF_BIRTH (the "incident" — unprotected PII)
- `ANALYTICS.STALE_SUMMARY` dynamic table in SUSPENDED state

**Ground-truth checklist (12 items):**
- [ ] Inventoried existing masking policies (SHOW MASKING POLICIES) before creating new ones
- [ ] Discovered policy assignments (POLICY_REFERENCES)
- [ ] Identified the CURRENT_ROLE() anti-pattern in LEGACY_MASK_EMAIL
- [ ] Identified unprotected PII columns (SSN, PHONE, DATE_OF_BIRTH, CUSTOMER_NAME)
- [ ] Ran SYSTEM$CLASSIFY to systematically find PII (not just manual column-name guessing)
- [ ] Fixed or replaced LEGACY_MASK_EMAIL with IS_ROLE_IN_SESSION()
- [ ] Created and applied masking policies for unprotected PII columns
- [ ] Verified masking works (queried as restricted role)
- [ ] Discovered STALE_SUMMARY is suspended
- [ ] Investigated *why* it was suspended before blindly resuming
- [ ] Either fixed/replaced or dropped the stale table with explanation
- [ ] Provided a coherent audit summary of what was found and what was fixed

---

### Test 4: "Build me an AI pipeline" — Multi-Step Chaining + Function Selection

**Domains:** ai-analytics, data-transformation
**Persona:** Data engineer building a new pipeline
**Difficulty:** Hard
**Core skill tested:** Can the agent select the right AI function for each task, chain operations in the correct order, and avoid the expensive anti-pattern of putting AI functions inside dynamic tables?

**Prompt:**
> I've got about a thousand support tickets in RAW.SUPPORT_TICKETS. I need to classify them by category (billing, technical, account, feature request), extract the product mentioned in each ticket, run sentiment analysis, and build a summary table that shows ticket volume and average sentiment by category and product over time. The summary should stay up to date automatically.

**Surface ask:** Build an AI enrichment pipeline with auto-updating summary.
**Real work:** Select correct AI functions, test on sample first, batch enrich into a materialized table, build dynamic table for aggregation only.
**Trap:** Putting AI_CLASSIFY / AI_EXTRACT / AI_SENTIMENT *inside* the dynamic table definition. This is the most expensive mistake possible — the dynamic table re-runs AI functions on every refresh on every row, burning credits continuously. The correct architecture is: materialize AI results into a regular table, then aggregate in a dynamic table. A naive agent that doesn't know this guardrail builds a pipeline that works but costs 100x what it should.

**Ground-truth checklist (12 items):**
- [ ] Tested AI functions on a sample (LIMIT 5-10) before full batch
- [ ] Used AI_CLASSIFY for category classification (not AI_COMPLETE)
- [ ] Classification categories match the 4 requested
- [ ] Used AI_EXTRACT for product extraction
- [ ] Used AI_SENTIMENT or AI_CLASSIFY with sentiment labels
- [ ] Enriched results stored in a materialized table (not a dynamic table with AI functions)
- [ ] Dynamic table aggregates pre-enriched results (not raw data through AI functions)
- [ ] Appropriate TARGET_LAG for the summary
- [ ] Pipeline is end-to-end functional (raw → enriched → summary)
- [ ] Handled null/empty AI function results
- [ ] Combined AI columns in a single SELECT (not separate passes)
- [ ] Verified results with sample data

---

### Test 5: "I want to change this table — what happens?" — Error Recovery + Pushing Back

**Domains:** data-observability, data-transformation, data-security
**Persona:** Data engineer with wrong assumptions
**Difficulty:** Hard
**Core skill tested:** Can the agent detect that the user's plan is partially wrong, push back with an explanation, and propose a correct alternative?

**Prompt:**
> I need to add a column to RAW.CUSTOMERS and change the type of the PHONE column from STRING to NUMBER. What's the blast radius, and can you help me do it safely?

**Surface ask:** Impact analysis + execute a schema change.
**Real work:** Run downstream dependency analysis, discover that PHONE has a masking policy attached (STRING-typed), and explain that changing the column type would break the policy and all downstream objects.
**Trap:** The user's plan is partially wrong — you *cannot* ALTER COLUMN type on a column with a masking policy attached without first unsetting the policy. The agent needs to push back: "You'll need to unset the masking policy first, alter the column, create a new NUMBER-typed masking policy, and re-apply it. These downstream objects will also be affected." A naive agent either executes the ALTER and hits an error it can't recover from, or does the impact analysis but misses the masking policy conflict entirely.

**Pre-seeded state (from T3 or fresh):**
- Masking policy applied to PHONE column (STRING type)
- Downstream dynamic table(s) referencing CUSTOMERS
- LEGACY_MASK_EMAIL applied to EMAIL

**Ground-truth checklist (10 items):**
- [ ] Ran downstream impact analysis (OBJECT_DEPENDENCIES) on RAW.CUSTOMERS
- [ ] Identified dependent objects (dynamic tables, views, etc.)
- [ ] Assessed usage stats on dependents (how actively queried)
- [ ] Discovered that PHONE column has a masking policy attached
- [ ] Explained that ALTER COLUMN type will fail with a masking policy in place
- [ ] Proposed correct sequence: unset policy → alter column → create new policy → re-apply
- [ ] Identified that the new masking policy must be NUMBER → NUMBER (not STRING → STRING)
- [ ] Warned about downstream breakage from the type change
- [ ] Did NOT blindly execute the ALTER and hit an error
- [ ] Provided a complete, ordered change plan the user can review before execution

---

### Test 6: "Make it production-ready" — Capstone

**Domains:** All 6 (data-security, data-transformation, app-deployment, cost-ops, ai-analytics, data-observability)
**Persona:** Engineering manager preparing a prototype for production launch
**Difficulty:** Very hard
**Core skill tested:** Can the agent proactively audit across every dimension without being told exactly what to check? Does the skills architecture produce an agent that asks the right questions before declaring victory?

**Prompt:**
> We've been prototyping a support ticket analysis pipeline in SNOWFLAKE_LEARNING_DB — it categorizes tickets, runs sentiment, and there's a summary table. Leadership wants to go live with it next week. Can you make sure it's production-ready? I need to know it's secure, it won't break if upstream data changes, it's not going to blow up our bill, and we can actually trust the numbers.

**Surface ask:** "Make it production-ready."
**Real work:** Every domain contributes something the agent must proactively check:
- **Security:** PII in ticket text (customer_id links to CUSTOMERS with PII). Is the enriched data masked? Who can access it?
- **Observability:** No quality monitoring on the source table. No lineage documentation. What depends on what?
- **Cost:** The `TICKET_ENRICHED` dynamic table runs AI functions on every refresh — projected cost at production scale is enormous.
- **Transformation:** AI functions inside the dynamic table is the core anti-pattern. Must be refactored to materialize enrichment separately.
- **AI analytics:** Are the AI function outputs accurate? Were they tested? What happens on null/empty inputs?
- **App deployment:** If a dashboard exists, does it have proper access controls?
**Trap:** Declaring "looks good" after surface-level checks. The production-readiness *bar* requires the agent to investigate dimensions the user didn't explicitly spell out. A keyword-matching agent checks whatever the user mentioned; a playbook-driven agent runs through a systematic audit.

**Pre-seeded state:**
- `ANALYTICS.TICKET_ENRICHED` dynamic table with AI functions in the definition (the cost anti-pattern)
- `LEGACY_MASK_EMAIL` with CURRENT_ROLE() anti-pattern
- `ANALYTICS.STALE_SUMMARY` suspended
- No masking on SSN, PHONE, DATE_OF_BIRTH in CUSTOMERS

**Ground-truth checklist (16 items):**
- [ ] Discovered the AI-functions-in-dynamic-table anti-pattern in TICKET_ENRICHED
- [ ] Explained the cost implication (AI functions re-run on every refresh)
- [ ] Proposed refactoring: materialize enrichment → aggregate in dynamic table
- [ ] Estimated or flagged projected cost at production scale
- [ ] Identified PII exposure risk (customer_id in tickets links to CUSTOMERS PII)
- [ ] Audited existing masking policies (found LEGACY_MASK_EMAIL anti-pattern)
- [ ] Identified unprotected PII columns in CUSTOMERS
- [ ] Recommended or created proper masking
- [ ] Ran lineage/dependency analysis on the pipeline objects
- [ ] Checked source table quality (nulls, freshness, row count)
- [ ] Identified STALE_SUMMARY as a broken/orphaned object
- [ ] Tested AI function accuracy on sample data (or flagged that it should be tested)
- [ ] Checked or recommended access controls on any dashboard/app
- [ ] Provided a prioritized list (security + cost fixes before nice-to-haves)
- [ ] Presented findings as a production-readiness assessment, not just SQL output
- [ ] Identified at least one issue the user didn't explicitly ask about

---

## Metrics

| # | Metric | How to Capture |
|---|--------|----------------|
| 1 | **Time to done** | Stopwatch from first prompt to verified completion |
| 2 | **Steps to done** | Count of tool calls + SQL executions from session transcript |
| 3 | **Human interventions** | Count every correction, re-prompt, clarification |
| 4 | **Outcome correctness** | % of ground-truth checklist items passed |
| 5 | **Trap detection** (new) | Did the agent find the trap? (the gap between ask and reality) |
| 6 | **Investigation depth** (new) | Did the agent investigate before acting, or act on assumptions? |
| 7 | **Error recovery** | When the agent hit an error or discovered a problem, did it self-recover, ask for help, or ignore it? |

### Scoring Trap Detection (Metric 5)

Rate per test:
- **Caught:** Agent proactively discovered the trap without being told (e.g., found AI-in-dynamic-table cost issue, found masking policy conflict)
- **Partial:** Agent encountered the trap reactively (hit an error, then recovered) but didn't proactively investigate
- **Missed:** Agent never discovered the trap — declared success without catching it

### Scoring Investigation Depth (Metric 6)

Rate 1-3:
- **3 (Investigated first):** Audited existing state, checked for problems, then proposed a plan
- **2 (Mixed):** Some investigation, but also made assumptions or skipped checks
- **1 (Acted on assumptions):** Jumped straight to execution without checking existing state

### Scoring Error Recovery (Metric 7)

Rate per error encountered:
- **Self-recovered:** Agent detected the problem, diagnosed it, and fixed it without human help
- **Asked for help:** Agent detected the problem but needed human input to resolve
- **Ignored:** Agent missed the problem entirely or worked around it without fixing the root cause

---

## Execution Protocol

### Arm A: Cortex Code + Bundled Skills

Same as experiment 001. Use original bundled skills (restored from backup). Same default connection.

### Arm B: Cursor CLI + Standard Skills Library

1. Create a Cursor project directory with the expanded standard library
2. Configure `.cursorrules` as described above
3. Ensure `snow` CLI is on PATH with default connection configured
4. Launch Cursor in the project directory
5. Paste prompts exactly as written

### Environment Reset Between Tests

```sql
-- Drop all dynamic tables except pre-seeded ones (STALE_SUMMARY, TICKET_ENRICHED)
-- Drop all masking policies except LEGACY_MASK_EMAIL
-- Drop all Streamlit apps created during tests
-- Verify source data intact (500 customers, 5000 orders, ~1000 support tickets)
-- Re-apply LEGACY_MASK_EMAIL to EMAIL column if dropped
-- Re-suspend STALE_SUMMARY if dropped and re-created
-- Re-create TICKET_ENRICHED with AI functions in definition if dropped
```

Pre-seeded broken objects must be present at the start of each test that scores them:
- **LEGACY_MASK_EMAIL** (CURRENT_ROLE anti-pattern): scored in T2, T3, T5, T6
- **STALE_SUMMARY** (suspended dynamic table): scored in T3, T6
- **TICKET_ENRICHED** (AI functions in dynamic table): scored in T1 (as cost driver), T6 (as anti-pattern)

### Test Order

Run tests in order (T1 → T6) for each arm. Clean environment between each test. The broken objects are persistent fixtures, not per-test artifacts.

---

## Pre-Registration

### Hypotheses

**H1 (Trap detection):** Arm B will catch more traps across all tests because playbooks prescribe investigation-before-action patterns and primitives include anti-pattern warnings. Arm A's keyword-matched skills don't surface these proactively.

**H2 (Investigation depth):** Arm B will score higher on investigation depth (metric 6) for T2, T3, T5, and T6 because playbooks enforce audit → plan → execute → verify sequences.

**H3 (Speed tradeoff):** Arm A will be faster on T1 and T4 (lower-complexity tests) because Cortex Code's native SQL execution is lower-latency than `snow sql` via bash. But Arm A's speed advantage will disappear on T5 and T6 where investigation depth matters more than execution speed.

**H4 (Disambiguation):** Arm B will handle T2 better because the meta-router's ambiguity detection will recognize that "clean and trustworthy" spans two domains. Arm A will pick one skill via keyword match and miss the other.

**H5 (Pushback):** Arm B will catch the masking policy type conflict in T5 because the masking-policies primitive explicitly documents the type-matching constraint. Arm A may not surface this until it hits a runtime error.

**H6 (Capstone):** T6 will produce the largest delta between arms because it requires proactive investigation across all domains — exactly what playbooks prescribe and keyword-matching doesn't.

---

## Implementation Steps

### Phase 0: Expand the Standard Library
1. Port cost-ops domain (router + 2 playbooks + 3 primitives)
2. Port ai-analytics domain (router + 2 playbooks + 3 primitives)
3. Port data-observability domain (router + 2 playbooks + 3 primitives)
4. Update index.yaml and meta-router
5. Compile bundled SKILL.md files for each new domain
6. Validate: read through each file for consistency, correct DAG references

### Phase 1: Wire Up Cursor
1. Create Cursor project directory
2. Write `.cursorrules` pointing to standard library
3. Test `snow sql` access from Cursor session
4. Run a smoke test (simple query) to verify end-to-end

### Phase 2: Prepare Environment
1. Load base data (CUSTOMERS, ORDERS) — reuse from experiment 001
2. Create SUPPORT_TICKETS table with synthetic data
3. Create pre-seeded broken objects (LEGACY_MASK_EMAIL, STALE_SUMMARY)
4. Verify all fixtures are in place
5. Take a snapshot of the environment state for reset

### Phase 3: Run Tests
1. Arm A: T1 → T6 with clean-slate between each
2. Arm B: T1 → T6 with clean-slate between each
3. Record all sessions (screen recording + transcript export)

### Phase 4: Analysis
1. Score all tests against ground-truth checklists
2. Compare trap detection rates between arms
3. Compare investigation depth between arms
4. Analyze error recovery patterns
5. Write report.md with findings
6. Compare results to experiment 001 baseline

---

## Files

| File | Purpose |
|------|---------|
| `experiment_plan.md` | This document |
| `experiment_log.md` | Raw operator notes (created during testing) |
| `report.md` | Polished findings (created after testing) |
| `cursor_project/` | Cursor project directory with .cursorrules |
| `fixtures.sql` | SQL to create pre-seeded broken objects |
| `reset.sql` | SQL to reset environment between tests |

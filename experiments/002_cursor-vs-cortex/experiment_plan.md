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
| T6 | End-to-end cross-domain build from ambiguous brief | All 6 | Very hard |
| T7 | Cost investigation + guardrails + monitoring dashboard | cost-ops + observability + security + app | Very hard |
| T8 | Secure migration + pipeline health audit for new team | security + transformation + observability + AI | Very hard |

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
    AI_SENTIMENT(body):categories[0]:sentiment::VARCHAR AS sentiment
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

### Test 6: "Build me a security incident tracker" — End-to-End Cross-Domain Build

**Domains:** All 6 (data-security, ai-analytics, data-transformation, app-deployment, cost-ops, data-observability)
**Persona:** Security team lead who needs a tool built from scratch
**Difficulty:** Very hard
**Core skill tested:** Can the agent chain across all domains to build a complete, working solution from an ambiguous brief? This tests *construction* (not just audit) across every domain simultaneously, with deliberate ambiguity that forces the agent to make and justify architectural decisions.

**Prompt:**
> My team needs a way to track which support tickets are about security incidents. Build me a pipeline that identifies security-related tickets, flags any that mention customer PII, enriches them with severity scores, and gives us a live dashboard where the security team can monitor incoming issues. Only the security team should be able to see the dashboard and the underlying data.

**Surface ask:** Build an end-to-end security incident tracking system.
**Real work:** The agent must:
- **AI analytics:** Use AI functions to classify security vs non-security tickets, detect PII mentions in text, score severity
- **Transformation:** Build a pipeline: raw tickets → AI enrichment (materialized, not in a DT) → filtered/aggregated view
- **Security:** Create role-based access so only a security team role can see the enriched data and dashboard. Consider that ticket text may contain customer PII (names, emails, account numbers mentioned in the body)
- **App deployment:** Build a Streamlit dashboard with proper access controls
- **Cost:** Avoid the AI-in-dynamic-table anti-pattern for enrichment
- **Observability:** Set up monitoring or at least document the pipeline lineage

**Trap:** Multiple compounding ambiguities:
1. "Security-related" is vague — the agent must define classification criteria or ask
2. "Flags any that mention customer PII" — could mean regex, AI_EXTRACT, or joining to CUSTOMERS table. The agent needs to decide and justify
3. "Severity scores" is undefined — the agent must propose a scoring methodology
4. "Only the security team" — no security team role exists. The agent must create one or explain what RBAC is needed
5. "Live dashboard" — Streamlit is the natural choice but the agent needs to handle access controls, which requires role grants on the Streamlit app
6. The AI-in-DT anti-pattern from T4/T6 — will the agent repeat the mistake or have the skills prevent it?

**Pre-seeded state:**
- Same 3 base tables (CUSTOMERS 500, ORDERS 5000, SUPPORT_TICKETS 1000)
- `LEGACY_MASK_EMAIL` with CURRENT_ROLE() anti-pattern on EMAIL
- `ANALYTICS.STALE_SUMMARY` suspended
- `ANALYTICS.TICKET_ENRICHED` with AI functions in definition (cost bomb)
- No security team role exists

**Ground-truth checklist (18 items):**

*AI & Classification (4 items):*
- [ ] Used appropriate AI function(s) to classify security vs non-security tickets
- [ ] Defined clear classification criteria (not just "security-related")
- [ ] Implemented PII detection in ticket text (AI_EXTRACT, regex, or other method)
- [ ] Proposed and implemented a severity scoring methodology

*Pipeline Architecture (4 items):*
- [ ] AI enrichment stored in a materialized table (NOT a dynamic table with AI functions)
- [ ] Aggregation/summary layer uses dynamic table or view over materialized results
- [ ] Pipeline is end-to-end functional (raw → enriched → filtered → dashboard-ready)
- [ ] Tested AI outputs on sample data before full batch

*Security & Access Control (4 items):*
- [ ] Created or proposed a security team role (or explained why one is needed)
- [ ] Applied RBAC so only the security role can access enriched data
- [ ] Addressed PII in ticket text (masking, filtering, or access control)
- [ ] Dashboard has access controls (Streamlit grant or role-based)

*App Deployment (3 items):*
- [ ] Created a functional Streamlit dashboard (or detailed the code for one)
- [ ] Dashboard shows relevant metrics (security ticket volume, severity distribution, trends)
- [ ] Dashboard is connected to the enriched/summary data

*Production Awareness (3 items):*
- [ ] Avoided or flagged the AI-in-dynamic-table cost anti-pattern
- [ ] Noticed existing TICKET_ENRICHED and either reused, refactored, or explained why replacing
- [ ] Provided architectural documentation or summary of what was built and why

---

### Test 7: "Our bill tripled — fix it and make sure it doesn't happen again" — Cost Controls + Guardrails + Dashboard

**Domains:** cost-ops, data-observability, data-security, app-deployment
**Persona:** Engineering manager who just got an angry email from finance
**Difficulty:** Very hard
**Core skill tested:** Can the agent investigate a cost problem, identify root causes, set up preventive guardrails, and build a monitoring solution — all from a panicked, ambiguous prompt?

**Prompt:**
> Our Snowflake bill tripled last quarter and nobody noticed until finance flagged it. I need you to figure out what's driving the cost, set up guardrails so it can't happen again, and build me a dashboard where my team can monitor spend in real time. Make sure only finance and engineering leads can see it.

**Surface ask:** Investigate cost spike + set up monitoring + build dashboard.
**Real work:** The agent must:
- **Cost-ops:** Investigate what's driving cost — should discover TICKET_ENRICHED running AI functions on every refresh as the likely culprit, plus general warehouse usage patterns
- **Observability:** Set up resource monitors or alerting to catch future spikes early
- **Security:** Create roles for finance/engineering leads (they don't exist), apply access controls
- **App deployment:** Build a Streamlit cost dashboard with proper RBAC
- **Transformation:** If the agent finds TICKET_ENRICHED as a cost driver, should recommend the materialization refactor

**Trap:** Multiple compounding issues:
1. "Real time" is misleading — ACCOUNT_USAGE views have up to 45-minute latency, ORGANIZATION_USAGE up to 3 hours. The agent should note this limitation rather than promising real-time
2. "Finance and engineering leads" — no such roles exist. The agent must create them or explain what's needed
3. TICKET_ENRICHED is actively burning AI credits on every refresh — this is the biggest cost driver but requires inspecting DT definitions, not just warehouse usage
4. Resource monitors alone aren't enough — they can suspend warehouses but can't control serverless/AI costs
5. The agent needs to distinguish between warehouse compute costs and AI/serverless costs (different monitoring approaches)

**Pre-seeded state:**
- Same 3 base tables (CUSTOMERS 500, ORDERS 5000, SUPPORT_TICKETS 1000)
- `LEGACY_MASK_EMAIL` with CURRENT_ROLE() anti-pattern on EMAIL
- `ANALYTICS.STALE_SUMMARY` suspended
- `ANALYTICS.TICKET_ENRICHED` with AI functions in definition (active cost bomb)
- No finance or engineering lead roles exist

**Ground-truth checklist (16 items):**

*Cost Investigation (4 items):*
- [ ] Queried ACCOUNT_USAGE views to investigate cost drivers (warehouse, serverless, AI services)
- [ ] Identified TICKET_ENRICHED as a cost concern (AI functions in DT definition)
- [ ] Explained the cost mechanism (AI functions re-run per-row on every refresh)
- [ ] Distinguished between warehouse compute costs and AI/serverless costs

*Guardrails & Monitoring (4 items):*
- [ ] Created or proposed resource monitors on warehouses
- [ ] Addressed AI/serverless cost monitoring (resource monitors don't cover these)
- [ ] Noted ACCOUNT_USAGE latency limitation (not truly "real time")
- [ ] Set up or proposed alerting for cost anomalies

*Access Control (4 items):*
- [ ] Created or proposed finance and engineering lead roles
- [ ] Applied RBAC to cost data / dashboard
- [ ] Considered what cost data each role should see (finance = billing, eng leads = warehouse detail)
- [ ] Dashboard has access controls (Streamlit grant or role-based)

*Dashboard & Delivery (4 items):*
- [ ] Created a functional Streamlit cost dashboard (or detailed the code)
- [ ] Dashboard shows relevant cost metrics (warehouse spend, AI spend, trends, top consumers)
- [ ] Dashboard is connected to ACCOUNT_USAGE or equivalent data
- [ ] Provided a summary of what was built, what it monitors, and known limitations

---

### Test 8: "Set up a secure analytics environment for the new team" — Secure Migration + Pipeline Health

**Domains:** data-security, data-transformation, data-observability, ai-analytics
**Persona:** Data platform lead onboarding a new analytics team
**Difficulty:** Very hard
**Core skill tested:** Can the agent audit an existing pipeline for health issues, secure it for a new audience, and set up a clean access layer — all while handling the tension between "give them access" and "protect sensitive data"?

**Prompt:**
> We're onboarding a new analytics team that needs access to our support ticket data, but they shouldn't see any customer PII. Can you set up a clean, secure analytics environment for them — give them the enriched ticket data, a way to explore trends, and make sure nothing sensitive leaks? Also check if the current pipeline is healthy before we hand it off.

**Surface ask:** Set up secure access for a new team + health check.
**Real work:** The agent must:
- **Security:** PII exists in two places — CUSTOMERS table (SSN, PHONE, etc.) and potentially in ticket BODY text (customers may include names, emails, account numbers in their messages). Must address both vectors.
- **Transformation:** Create a clean view or table that strips/masks PII for the analytics team
- **Observability:** "Check if healthy" means auditing all 3 traps — STALE_SUMMARY suspended, TICKET_ENRICHED with AI cost bomb, LEGACY_MASK_EMAIL with CURRENT_ROLE() anti-pattern
- **AI analytics:** The enriched data from TICKET_ENRICHED uses AI functions — are the outputs trustworthy? Were they validated?

**Trap:** Multiple layers of PII exposure:
1. Direct PII in CUSTOMERS (SSN, PHONE, DATE_OF_BIRTH, CUSTOMER_NAME, EMAIL) — obvious
2. PII in ticket BODY text — customers write things like "my email is X" or "account #12345" in support tickets. The agent needs to recognize this as a PII vector, not just mask the CUSTOMERS table
3. CUSTOMER_ID in TICKET_ENRICHED is a join key to CUSTOMERS — even without direct PII columns, the analytics team could join to get PII unless access is controlled
4. "Clean environment" is ambiguous — new schema? Secure views? Role with grants? The agent must make an architectural decision
5. "Healthy" requires discovering all 3 traps, not just running a SELECT to check row counts
6. No analytics team role exists — must be created

**Pre-seeded state:**
- Same 3 base tables (CUSTOMERS 500, ORDERS 5000, SUPPORT_TICKETS 1000)
- `LEGACY_MASK_EMAIL` with CURRENT_ROLE() anti-pattern on EMAIL
- `ANALYTICS.STALE_SUMMARY` suspended
- `ANALYTICS.TICKET_ENRICHED` with AI functions in definition (cost bomb)
- No analytics team role exists

**Ground-truth checklist (16 items):**

*Security & PII (5 items):*
- [ ] Identified direct PII columns in CUSTOMERS (SSN, PHONE, DATE_OF_BIRTH, CUSTOMER_NAME, EMAIL)
- [ ] Recognized PII risk in ticket BODY text (customers may include personal info in messages)
- [ ] Addressed the CUSTOMER_ID join-key risk (analytics team could join to CUSTOMERS)
- [ ] Created or proposed an analytics team role with restricted access
- [ ] Applied masking policies or created secure views that strip PII

*Pipeline Health Audit (4 items):*
- [ ] Discovered STALE_SUMMARY is suspended and investigated why
- [ ] Discovered TICKET_ENRICHED has AI functions in its definition (cost anti-pattern)
- [ ] Audited LEGACY_MASK_EMAIL and found the CURRENT_ROLE() anti-pattern
- [ ] Provided a health assessment before granting access (not just "looks fine")

*Analytics Environment Setup (4 items):*
- [ ] Created a clean access layer (secure views, new schema, or filtered tables)
- [ ] Analytics team can query enriched ticket data without seeing PII
- [ ] Provided a way to explore trends (view, dashboard, or documented query patterns)
- [ ] Access is properly scoped (analytics role can only see what they need)

*Production Awareness (3 items):*
- [ ] Flagged the AI-in-DT cost issue as something to fix before onboarding
- [ ] Recommended or executed fixes for discovered health issues
- [ ] Provided documentation of what was set up and what access was granted

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

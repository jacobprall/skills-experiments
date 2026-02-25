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
| **Test count** | 3 tiers x 2 arms = 6 | 5 tiers x 2 arms = 10 |
| **Personas** | Business users only | Business users + developers |

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
│  snow sql -q "..." --connection snowhouse     │
│  snow stage copy ...                          │
│  snow streamlit deploy ...                    │
└──────────────────────────────────────────────┘
```

### Setup

1. **Project directory:** Create a Cursor project with the standard library as context
2. **`.cursorrules`:** Points to `router.md` as the primary instruction set. Include domain routers, playbooks, and primitives as available files the agent can read
3. **Tool access:** Cursor gets `bash` with `snow` CLI on PATH
4. **Connection:** Same `snowhouse` connection in `~/.snowflake/connections.toml`
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
5. Execute SQL via: snow sql -q "YOUR SQL" --connection snowhouse --role ROLE --warehouse WH

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

### Principles for Experiment 002

1. **Ambiguity over specificity.** Real users don't know Snowflake terminology. Prompts should be vague, use business language, and sometimes contradict themselves.
2. **Multi-domain by default.** Most real tasks span 2-4 domains. Single-domain tests are warm-ups, not the point.
3. **Error-prone setups.** Pre-seed the environment with gotchas: wrong permissions, existing objects, stale data. See if the agent investigates before acting.
4. **Both personas.** Business users (no technical vocabulary) and developers (technical but wrong assumptions about Snowflake).

### Environment Setup

Same base as experiment 001, plus additional objects for new test scenarios:

```sql
-- Base tables (same as experiment 001)
-- RAW.CUSTOMERS (500 rows, PII columns)
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

-- A stage with sample PDF documents (for document processing tests)
-- CREATE STAGE RAW.DOCUMENTS;
-- Upload 3-5 sample invoices/contracts

-- Pre-existing masking policy with CURRENT_ROLE() anti-pattern
-- (Tests whether agent detects and fixes it)
CREATE OR REPLACE MASKING POLICY RAW.LEGACY_MASK_EMAIL AS (val STRING)
  RETURNS STRING ->
  CASE WHEN CURRENT_ROLE() = 'SNOWFLAKE_LEARNING_ADMIN_ROLE' THEN val
       ELSE '***MASKED***'
  END;
-- Apply it
ALTER TABLE RAW.CUSTOMERS MODIFY COLUMN EMAIL SET MASKING POLICY RAW.LEGACY_MASK_EMAIL;
```

---

## Test Scenarios

### Test 1: Warm-Up — Cost Investigation (Single Domain, Business User)

**Domains:** cost-ops
**Persona:** Finance manager
**Difficulty:** Low-moderate (single domain, but vague)

**Prompt:**
> Our Snowflake bill jumped this month and my boss is asking what happened. I don't really know how Snowflake billing works. Can you figure out where the money is going and if there's anything obviously wrong?

**Ground-truth checklist (8 items):**
- [ ] Queried ACCOUNT_USAGE for overall cost breakdown by service type
- [ ] Identified warehouse costs vs. serverless vs. storage vs. Cortex AI
- [ ] Showed week-over-week or month-over-month trend
- [ ] Identified top-spending warehouses
- [ ] Identified top-spending users or queries
- [ ] Checked for anomalous spikes
- [ ] Provided actionable recommendations (resize, auto-suspend, etc.)
- [ ] Results presented in a format a non-technical person can understand

**What makes this harder than experiment 001:**
- No mention of "warehouse", "credits", "ACCOUNT_USAGE" — pure business language
- Requires the agent to explore multiple cost dimensions without being told which ones
- Answer quality depends on interpreting patterns, not just running SQL

---

### Test 2: Audit & Fix — Security Remediation (Single Domain, Developer)

**Domains:** data-security
**Persona:** Data engineer who inherited someone else's work
**Difficulty:** Moderate (must discover existing state, not just create from scratch)

**Prompt:**
> I inherited this SNOWFLAKE_LEARNING_DB database from someone who left. I think they set up some data masking but I'm not sure it's working right — we had an incident where an analyst saw SSNs they shouldn't have. Can you audit what's there, tell me if there are any problems, and fix whatever's broken?

**Pre-seeded state:**
- `LEGACY_MASK_EMAIL` policy using `CURRENT_ROLE()` (anti-pattern) applied to EMAIL column
- No policies on SSN, PHONE, DATE_OF_BIRTH (the "incident" — these are unprotected)
- CUSTOMER_NAME not masked

**Ground-truth checklist (10 items):**
- [ ] Discovered existing masking policies (SHOW MASKING POLICIES)
- [ ] Discovered existing policy assignments (POLICY_REFERENCES)
- [ ] Identified the `CURRENT_ROLE()` anti-pattern in LEGACY_MASK_EMAIL
- [ ] Identified unprotected PII columns (SSN, PHONE, DATE_OF_BIRTH, CUSTOMER_NAME)
- [ ] Ran SYSTEM$CLASSIFY to systematically find PII (not just manual inspection)
- [ ] Fixed or replaced the broken LEGACY_MASK_EMAIL policy with IS_ROLE_IN_SESSION()
- [ ] Created masking policies for unprotected PII columns
- [ ] Applied policies to all PII columns
- [ ] Verified masking works (queried as restricted role)
- [ ] Provided audit summary of what was found and what was fixed

**What makes this harder than experiment 001 T1:**
- Pre-existing broken state (not greenfield)
- Must audit before acting — creating new policies without checking existing ones would create conflicts
- The `CURRENT_ROLE()` anti-pattern must be detected, not just avoided
- The "incident" framing adds urgency and context the agent must interpret

---

### Test 3: Cross-Domain Pipeline — Transform + Observe + Secure (Business User)

**Domains:** data-transformation, data-observability, data-security
**Persona:** VP of Data who doesn't know Snowflake
**Difficulty:** Hard (3 domains, ambiguous requirements, conflicting signals)

**Prompt:**
> We've got customer and order data that different teams keep asking me about. I need a few things: some kind of automated summary that stays current so people stop running ad-hoc queries, a way to know if something goes wrong with the data before someone complains, and make sure the personal information is locked down. I also want to understand what depends on our customer table so I know the blast radius if we ever change it. Can you set all that up?

**Ground-truth checklist (14 items):**
- [ ] Dynamic table(s) for automated revenue/order summary
- [ ] Appropriate TARGET_LAG set
- [ ] Pipeline produces correct aggregated data
- [ ] Detected existing stale ANALYTICS.STALE_SUMMARY dynamic table (pre-seeded broken one)
- [ ] Either fixed/replaced or dropped the stale table (didn't ignore it)
- [ ] Lineage analysis: identified downstream dependencies of RAW.CUSTOMERS
- [ ] Impact analysis presented clearly (what would break if CUSTOMERS changes)
- [ ] SYSTEM$CLASSIFY or manual PII identification on CUSTOMERS
- [ ] Masking policies created with IS_ROLE_IN_SESSION()
- [ ] Policies applied to PII columns
- [ ] Masking verified
- [ ] Data quality / monitoring recommendation or setup (DMFs, alerts, or at minimum explained options)
- [ ] Discovered existing broken LEGACY_MASK_EMAIL (if not cleaned from T2 — run T3 independently)
- [ ] Results presented as a coherent summary, not just a list of SQL outputs

**What makes this harder than experiment 001 T3:**
- 3 domains including the new data-observability domain
- Pre-existing broken state (stale dynamic table, broken masking policy)
- "Blast radius" is business language for lineage/impact analysis
- "Know if something goes wrong" is vague — agent must decide between DMFs, alerts, or monitoring

---

### Test 4: AI-Powered Analysis — Documents + Enrichment (Developer)

**Domains:** ai-analytics, data-transformation
**Persona:** Data engineer building a new pipeline
**Difficulty:** Hard (new domain, multi-step, requires understanding AI function selection)

**Prompt:**
> I've got about a thousand support tickets in RAW.SUPPORT_TICKETS. I need to classify them by category (billing, technical, account, feature request), extract the product mentioned in each ticket, run sentiment analysis, and build a summary table that shows ticket volume and average sentiment by category and product over time. The summary should stay up to date automatically.

**Ground-truth checklist (12 items):**
- [ ] Used AI_CLASSIFY (or AI_COMPLETE with classification prompt) on ticket body
- [ ] Classification categories match the 4 requested (billing, technical, account, feature request)
- [ ] Used AI_EXTRACT to pull product mentions from ticket text
- [ ] Used AI_SENTIMENT on ticket body
- [ ] Results stored in a usable intermediate table or view
- [ ] Dynamic table for automated summary (volume + avg sentiment by category x product x time)
- [ ] Appropriate TARGET_LAG for the summary
- [ ] Summary produces correct aggregated data
- [ ] Pipeline is end-to-end functional (raw tickets → enriched → summary)
- [ ] AI function calls are efficient (not running on every refresh if data hasn't changed)
- [ ] Error handling for AI function failures (null/empty results)
- [ ] Results verified with sample data

**What makes this harder than anything in experiment 001:**
- AI functions are a new domain not tested before
- Requires selecting the right AI function for each task (classify vs. extract vs. sentiment)
- Multi-step pipeline: enrich raw data → aggregate enriched data
- Efficiency matters: naive implementation would re-run AI functions on unchanged data

---

### Test 5: Full Stack Chaos — Everything (Business User, Maximally Ambiguous)

**Domains:** All 6 (data-security, data-transformation, app-deployment, cost-ops, ai-analytics, data-observability)
**Persona:** New VP of Data, first week, doesn't know what exists
**Difficulty:** Very hard (6 domains, discovery-first, vague, contradictory)

**Prompt:**
> I just joined and I'm trying to understand what we have in SNOWFLAKE_LEARNING_DB. I need to know: what data is here and is any of it sensitive? Is anything broken or stale? What are people spending money on? I also need the support ticket data categorized and summarized somehow. And eventually I'll want a dashboard. Can you help me get a handle on all of this?

**Ground-truth checklist (18 items):**
- [ ] Discovery: explored schemas and tables in the database
- [ ] Discovery: described table structures and row counts
- [ ] Security: identified PII in CUSTOMERS (SYSTEM$CLASSIFY or manual)
- [ ] Security: audited existing masking policies (found LEGACY_MASK_EMAIL)
- [ ] Security: identified CURRENT_ROLE() anti-pattern
- [ ] Security: fixed or created proper masking policies
- [ ] Observability: identified stale ANALYTICS.STALE_SUMMARY
- [ ] Observability: ran lineage/dependency analysis
- [ ] Observability: provided data health assessment
- [ ] Cost: queried cost breakdown
- [ ] Cost: identified top cost drivers
- [ ] Cost: provided recommendations
- [ ] AI: classified support tickets by category
- [ ] AI: created summary of ticket trends
- [ ] Transform: created or fixed automated summary pipeline
- [ ] App: created dashboard (or provided plan for one)
- [ ] Coherent narrative: presented findings as an executive briefing, not a list of SQL outputs
- [ ] Prioritized: addressed most critical issues first (broken security > stale data > cost > nice-to-haves)

**What makes this the hardest test:**
- All 6 domains in one request
- Discovery-first: agent doesn't know what exists
- No specific instructions — agent must decide what to do and in what order
- Implicit prioritization: security issues should be addressed before building dashboards
- "Eventually I'll want a dashboard" is intentionally vague — agent must decide whether to build it now or defer

---

## Metrics (Same as Experiment 001, Plus Two)

| # | Metric | How to Capture |
|---|--------|----------------|
| 1 | **Time to done** | Stopwatch from first prompt to verified completion |
| 2 | **Steps to done** | Count of tool calls + SQL executions from session transcript |
| 3 | **Human interventions** | Count every correction, re-prompt, clarification |
| 4 | **Outcome correctness** | % of ground-truth checklist items passed |
| 5 | **Domain sequencing quality** (new) | Did the agent address domains in a sensible order? (security before app, discovery before action) |
| 6 | **Error recovery** (new) | When the agent hit an error or discovered a problem, did it self-recover, ask for help, or ignore it? |

### Scoring Domain Sequencing (Metric 5)

Rate 1-3:
- **3 (Optimal):** Addressed security/broken state first, then built on clean foundation
- **2 (Acceptable):** Reasonable order but some missed dependencies
- **1 (Poor):** Built new objects on broken state, or did low-priority work before critical fixes

### Scoring Error Recovery (Metric 6)

Rate per error encountered:
- **Self-recovered:** Agent detected the problem, diagnosed it, and fixed it without human help
- **Asked for help:** Agent detected the problem but needed human input to resolve
- **Ignored:** Agent missed the problem entirely or worked around it without fixing the root cause

---

## Execution Protocol

### Arm A: Cortex Code + Bundled Skills

Same as experiment 001. Use original bundled skills (restored from backup). Same `snowhouse` connection.

### Arm B: Cursor CLI + Standard Skills Library

1. Create a Cursor project directory with the expanded standard library
2. Configure `.cursorrules` as described above
3. Ensure `snow` CLI is on PATH with `snowhouse` connection
4. Launch Cursor in the project directory
5. Paste prompts exactly as written

### Environment Reset Between Tests

```sql
-- Drop all dynamic tables except the pre-seeded broken one
-- Drop all masking policies except LEGACY_MASK_EMAIL
-- Drop all Streamlit apps created during tests
-- Verify source data intact (500 customers, 5000 orders, ~1000 support tickets)
-- Re-apply LEGACY_MASK_EMAIL to EMAIL column if dropped
-- Re-suspend STALE_SUMMARY if dropped and re-created
```

For tests that explicitly require discovering pre-seeded broken state (T2, T3, T5), the broken objects must be present at test start. For T1 and T4 which don't involve security audit, the broken objects can be present but are not part of the scoring.

### Test Order

Run tests in order (T1 → T5) for each arm. Clean environment between each test. The broken objects (LEGACY_MASK_EMAIL, STALE_SUMMARY) are persistent fixtures, not per-test artifacts.

---

## Pre-Registration

### Hypotheses

**H1:** Cursor + Standard Library (Arm B) will score higher on outcome correctness for T3 and T5 (multi-domain tests) because the meta-router will actually sequence domains, unlike experiment 001 where it was bypassed.

**H2:** Arm B will require fewer human interventions across all tests because playbooks prescribe investigation-before-action patterns.

**H3:** Arm A will be faster on T1 and T4 (single/two-domain tests) because Cortex Code's native SQL execution is lower-latency than `snow sql` via bash.

**H4:** Arm B will handle pre-existing broken state better (T2, T3, T5) because playbooks include audit/discovery steps that bundled skills don't prescribe.

**H5:** Domain sequencing quality will be higher for Arm B because the meta-router's topological sort enforces a sensible order.

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
1. Arm A: T1 → T5 with clean-slate between each
2. Arm B: T1 → T5 with clean-slate between each
3. Record all sessions (screen recording + transcript export)

### Phase 4: Analysis
1. Score all tests against ground-truth checklists
2. Compare domain sequencing between arms
3. Analyze error recovery patterns
4. Write report.md with findings
5. Compare results to experiment 001 baseline

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

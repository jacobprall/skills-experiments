# Skills Benchmark: Bundled Skills vs. Standard Library

## Experiment Overview

**Objective:** Compare intent-to-result performance of Cortex Code CLI using two skill configurations:
- **Arm A (Control):** Pre-bundled skills (shipped with Cortex Code 1.0.20)
- **Arm B (Treatment):** Standard Snowflake Skills Library only

**Format:** Side-by-side video comparison. Same prompts, same account, same data. Each arm runs all three tests sequentially in a single recording session.

**Database:** `SNOWFLAKE_LEARNING_DB`
**Role:** `SNOWFLAKE_LEARNING_ADMIN_ROLE`
**Warehouse:** `SNOWFLAKE_LEARNING_WH`
**Restricted role (for masking verification):** `SNOWFLAKE_LEARNING_ROLE`

---

## What We're Measuring

Four metrics. That's it. Each one maps directly to what a business user cares about.

| # | Metric | What It Answers | How to Capture |
|---|--------|----------------|----------------|
| 1 | **Time to done** | "How long did I wait?" | Stopwatch from first prompt to verified completion |
| 2 | **Steps to done** | "How much stuff happened?" | Count of agent actions (tool calls + SQL executions + skill loads) from session transcript |
| 3 | **Human interventions** | "How much did I have to babysit?" | Count every correction, re-prompt, clarification, or manual fix the operator provides |
| 4 | **Outcome correctness** | "Did it actually work?" | Binary pass/fail on each item in the expected ground-truth checklist, scored as % |

### Why These Four

- **Time** is the single metric a business user viscerally experiences. If one arm takes 8 minutes and the other takes 22, nothing else matters.
- **Steps** is a proxy for cost, context window pressure, and agent confusion. Fewer steps = less compute, fewer tokens burned, less chance of the agent losing the thread.
- **Human interventions** measures self-sufficiency. A business user doesn't know Snowflake internals — every time they have to correct the agent, the product failed.
- **Outcome correctness** is the ground truth. Did it work or didn't it.

Credits are downstream of steps and time — they'll correlate. UX quality is downstream of interventions and correctness — if the agent gets it right with zero hand-holding, the UX was good. We don't need separate metrics for these.

---

## Auditing Steps and Tokens (Without the Standard Library Thread)

The standard library's thread model gives you a structured event log for free. For the bundled skills arm (and as a universal fallback), here's how to capture equivalent data:

### Step Counting

**Source:** Cortex Code session transcript (exported as markdown).

Every Cortex Code session can be exported. The transcript contains every tool call, every SQL execution, every skill load, and every agent response. To count steps:

```bash
# After exporting the transcript to a file:
# Count tool invocations (each is a discrete "step")
grep -c "Tool:" transcript_arm_a_test_1.md

# Count SQL executions specifically
grep -c "snowflake_sql_execute\|SQL\|```sql" transcript_arm_a_test_1.md

# Count skill loads
grep -c "skill\|SKILL" transcript_arm_a_test_1.md
```

For precision, manually walk the transcript and tally:
- **Skill loads** — how many skills were loaded into context
- **SQL executions** — how many queries were run against Snowflake
- **Tool calls** — how many non-SQL tools were invoked (bash, file reads, etc.)
- **Clarifying questions** — how many times the agent asked the user something
- **Total** — sum of all the above = "steps to done"

### Token Approximation

The transcript doesn't expose raw token counts, but you can approximate:

```python
# pip install tiktoken
import tiktoken

enc = tiktoken.encoding_for_model("claude-3-opus-20240229")  # or appropriate model

with open("transcript_arm_a_test_1.md") as f:
    text = f.read()

token_count = len(enc.encode(text))
print(f"Approximate tokens: {token_count}")
```

This captures the visible conversation tokens. It underestimates (doesn't include system prompts, skill content loaded behind the scenes) but gives a consistent relative comparison between arms.

### Snowflake Query Audit (Authoritative)

For the Snowflake side, `QUERY_HISTORY` is the ground truth. Run this after each test:

```sql
USE ROLE SNOWFLAKE_LEARNING_ADMIN;

SELECT
    query_id,
    query_text,
    start_time,
    end_time,
    DATEDIFF('second', start_time, end_time) AS duration_seconds,
    total_elapsed_time / 1000 AS elapsed_seconds,
    credits_used_cloud_services,
    rows_produced,
    error_code,
    error_message
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
    DATE_RANGE_START => '<test_start_timestamp>'::TIMESTAMP_LTZ,
    DATE_RANGE_END => '<test_end_timestamp>'::TIMESTAMP_LTZ,
    RESULT_LIMIT => 1000
))
WHERE warehouse_name = 'SNOWFLAKE_LEARNING_WH'
ORDER BY start_time;
```

This gives you: exact SQL count, execution times, errors, and per-query credit usage. Combined with the transcript step count, you have full auditability for both arms.

### Comparison: Thread Model vs. Transcript-Based Audit

| Capability | Standard Library Thread | Transcript + Query History |
|-----------|------------------------|---------------------------|
| Step count | Automatic (events) | Manual count from transcript |
| SQL audit | Events include SQL | `QUERY_HISTORY` view |
| Token count | Not captured | Approximate via tiktoken |
| Skill loads | Events include routing | Grep transcript for skill names |
| Error tracking | Events with recovery info | Grep transcript + `error_code` in query history |
| Structured / machine-readable | Yes (YAML events) | No (requires parsing) |
| Works for bundled skills arm | No | Yes |

The standard library thread model is strictly better for auditability — that's a valid finding to note in the video. But the transcript approach works for both arms.

---

## Test Environment Setup

### Prerequisites

- Snowflake account with `SNOWFLAKE_LEARNING_ADMIN_ROLE` access
- Cortex Code CLI v1.0.20 installed
- Screen recording software (OBS or similar) with timer overlay
- The orchestration script (`run_benchmark.sh`) on the Desktop

### Skill Swap Workaround (Arm B)

**Discovery:** Cortex Code's available skills list is **dual-sourced**. The `<available_skills>` block in the system prompt is partially hardcoded by the Cortex Code binary/server — it always advertises the original bundled skill names (e.g., `sensitive-data-classification`, `data-policy`, `dynamic-tables`) regardless of what's on disk. The `bundled_skills/` directory only provides the **content** that gets loaded when a skill is invoked.

**Failed approach:** Initially we tried replacing the entire `bundled_skills/` directory with 4 new SKILL.md wrappers (`data-security`, `data-transformation`, `app-deployment`, `standard-router`). The agent still tried to invoke the hardcoded skill names (e.g., `sensitive-data-classification`), which succeeded because Cortex Code found the SKILL.md file on disk — but loaded the wrong skill's content since our directory names didn't match.

**Working approach (content replacement):** We restore the original `bundled_skills/` directory structure (preserving all 23 directory names) but replace the SKILL.md **content** inside each test-relevant directory with our standard library material. The agent invokes `sensitive-data-classification` by name (because the registry tells it to), but loads our standard library data-security content.

**Mapping:**

| Bundled Skill Name (preserved) | Standard Library Content Loaded | Domain |
|---|---|---|
| `sensitive-data-classification` | data-security (561 lines) | Security |
| `data-policy` | data-security (561 lines) | Security |
| `data-governance` | data-security (561 lines) | Security |
| `dynamic-tables` | data-transformation (334 lines) | Transform |
| `dbt-projects-on-snowflake` | data-transformation (334 lines) | Transform |
| `openflow` | data-transformation (334 lines) | Transform |
| `developing-with-streamlit` | app-deployment (306 lines) | App |
| `deploy-to-spcs` | app-deployment (306 lines) | App |
| `build-react-app` | app-deployment (306 lines) | App |

The 13 unrelated skills (cortex-agent, iceberg, machine-learning, etc.) retain their original bundled content. They won't be triggered by our test prompts.

Sub-skill directories within each replaced skill were also removed so the agent only sees our standard library SKILL.md — no residual bundled sub-content.

**Implication for the benchmark:** The agent still uses the bundled skill *descriptions* (from the hardcoded registry) to decide which skill to invoke. This means the skill-selection behavior is identical between arms — only the content loaded after selection differs. This is actually a cleaner comparison: same trigger → different guidance.

**Version gotcha:** Cortex Code may auto-update or use a different installed version than expected. The skill swap must be applied to ALL installed versions under `~/.local/share/cortex/`. We discovered this when the B1 session launched on v1.0.21 while we'd only patched v1.0.20. Both `1.0.20+045458.1785e665caa4` and `1.0.21+235436.342efc1ea864` have been patched with backups.

### Data Setup

```sql
USE ROLE SNOWFLAKE_LEARNING_ADMIN_ROLE;
USE WAREHOUSE SNOWFLAKE_LEARNING_WH;

CREATE DATABASE IF NOT EXISTS SNOWFLAKE_LEARNING_DB;
CREATE SCHEMA IF NOT EXISTS SNOWFLAKE_LEARNING_DB.RAW;
CREATE SCHEMA IF NOT EXISTS SNOWFLAKE_LEARNING_DB.STAGING;
CREATE SCHEMA IF NOT EXISTS SNOWFLAKE_LEARNING_DB.ANALYTICS;
CREATE SCHEMA IF NOT EXISTS SNOWFLAKE_LEARNING_DB.GOVERNANCE;

USE SCHEMA SNOWFLAKE_LEARNING_DB.RAW;

CREATE OR REPLACE TABLE CUSTOMERS (
    customer_id STRING,
    customer_name STRING,
    email STRING,
    phone STRING,
    ssn STRING,
    segment STRING,
    department STRING,
    date_of_birth DATE
);

CREATE OR REPLACE TABLE ORDERS (
    order_id STRING,
    customer_id STRING,
    order_date TIMESTAMP,
    total_amount NUMBER(10,2),
    status STRING
);

INSERT INTO CUSTOMERS
SELECT
    'CUST-' || SEQ4(),
    RANDSTR(8, RANDOM()) || ' ' || RANDSTR(10, RANDOM()),
    LOWER(RANDSTR(8, RANDOM())) || '@example.com',
    '+1-555-' || LPAD(UNIFORM(1000000, 9999999, RANDOM())::STRING, 7, '0'),
    LPAD(UNIFORM(100000000, 999999999, RANDOM())::STRING, 9, '0'),
    CASE UNIFORM(1, 4, RANDOM())
        WHEN 1 THEN 'Enterprise' WHEN 2 THEN 'SMB'
        WHEN 3 THEN 'Startup' ELSE 'Consumer'
    END,
    CASE UNIFORM(1, 4, RANDOM())
        WHEN 1 THEN 'Sales' WHEN 2 THEN 'Engineering'
        WHEN 3 THEN 'Marketing' ELSE 'Support'
    END,
    DATEADD('day', -UNIFORM(7000, 25000, RANDOM()), CURRENT_DATE())
FROM TABLE(GENERATOR(ROWCOUNT => 500));

INSERT INTO ORDERS
SELECT
    'ORD-' || SEQ4(),
    'CUST-' || UNIFORM(0, 499, RANDOM()),
    DATEADD('hour', -UNIFORM(1, 8760, RANDOM()), CURRENT_TIMESTAMP()),
    ROUND(UNIFORM(10, 5000, RANDOM()) + UNIFORM(0, 99, RANDOM()) / 100, 2),
    CASE UNIFORM(1, 5, RANDOM())
        WHEN 1 THEN 'PENDING' WHEN 2 THEN 'SHIPPED' WHEN 3 THEN 'DELIVERED'
        WHEN 4 THEN 'RETURNED' ELSE 'CANCELLED'
    END
FROM TABLE(GENERATOR(ROWCOUNT => 5000));

-- Roles for masking verification (pre-existing on the account):
-- SNOWFLAKE_LEARNING_ROLE = restricted role (should see masked values)
-- SNOWFLAKE_LEARNING_ADMIN_ROLE = admin role (should see real values)
```

---

## Test 1: Basic (Single Domain — Data Security)

**Persona:** Compliance analyst
**Prompt:**

> I have customer data in SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS that probably contains PII. I need to find the sensitive columns, mask them so only authorized roles can see the real values, and verify the masking is working. I'm using the SNOWFLAKE_LEARNING_ADMIN_ROLE role and the SNOWFLAKE_LEARNING_WH warehouse. Can you help me set that up?

### Expected Ground-Truth Checklist

- [ ] `SYSTEM$CLASSIFY` run on `RAW.CUSTOMERS`
- [ ] Sensitive columns identified (email, phone, ssn, date_of_birth, customer_name)
- [ ] Masking policies created using `IS_ROLE_IN_SESSION()` (not `CURRENT_ROLE()`)
- [ ] Policies applied to identified columns
- [ ] Verification: masked values when queried as `SNOWFLAKE_LEARNING_ROLE`
- [ ] Verification: real values when queried as `SNOWFLAKE_LEARNING_ADMIN_ROLE`

**Outcome correctness** = (items passed / 6) × 100%

### What to Watch For

| Signal | Bundled (Arm A) | Standard Library (Arm B) |
|--------|----------------|-------------------------|
| Skill selection | 3 overlapping skills compete (`data-policy`, `data-governance`, `sensitive-data-classification`) | Single path: data-security router → `secure-sensitive-data` playbook |
| Context volume | `data-policy` = 2,061 lines, `data-governance` = 6,881 lines | Playbook + primitives on demand ≈ 500 lines |
| Pre-flight checks | Agent may or may not check for existing policies | Mandatory probes in playbook front-matter |
| Anti-pattern: `CURRENT_ROLE()` | Risk of using it (common LLM mistake) | Explicitly warned against in masking-policies primitive |

### Verification Queries

```sql
-- Check policies exist
SHOW MASKING POLICIES IN SCHEMA SNOWFLAKE_LEARNING_DB.RAW;

-- Test as restricted role
USE ROLE ANALYST_RESTRICTED;
SELECT email, phone, ssn FROM SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS LIMIT 3;
-- Expected: masked values

-- Test as steward
USE ROLE DATA_STEWARD;
SELECT email, phone, ssn FROM SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS LIMIT 3;
-- Expected: real values

-- Return to admin
USE ROLE SNOWFLAKE_LEARNING_ADMIN;
```

---

## Test 2: Moderate (Two Domains — Transformation + Security)

**Persona:** Business operations manager
**Prompt:**

> I need to build a pipeline that continuously transforms our raw order data in SNOWFLAKE_LEARNING_DB.RAW.ORDERS into a daily revenue summary by customer segment. The summary should refresh every 30 minutes. Also, the source CUSTOMERS table has PII that needs to be masked before anyone queries the enriched data. I'm using the SNOWFLAKE_LEARNING_ADMIN_ROLE role and the SNOWFLAKE_LEARNING_WH warehouse. Can you set this up end to end?

### Expected Ground-Truth Checklist

- [ ] Change tracking enabled on `RAW.ORDERS` and `RAW.CUSTOMERS`
- [ ] Staging dynamic table (cleaned orders) with `TARGET_LAG = DOWNSTREAM`
- [ ] Enrichment dynamic table (orders joined with customers) with `TARGET_LAG = DOWNSTREAM`
- [ ] Aggregation dynamic table (daily revenue by segment) with `TARGET_LAG = '30 minutes'`
- [ ] Masking policies applied to PII columns on `RAW.CUSTOMERS`
- [ ] Pipeline health verified (scheduling state shows `ACTIVE`)
- [ ] Masking verified with role-based testing
- [ ] Correct domain ordering (transformation before or interleaved with security — not security first)

**Outcome correctness** = (items passed / 8) × 100%

### What to Watch For

| Signal | Bundled (Arm A) | Standard Library (Arm B) |
|--------|----------------|-------------------------|
| Domain sequencing | Agent must figure out dependency order ad hoc | Meta-router topologically sorts: transformation → security |
| Context handoff | Table names from pipeline must flow to security phase by luck | `context_mapping`: `created_tables → target_scope` |
| Intermediate lag | May use time-based lag on all tables (wastes credits) | Playbook prescribes `DOWNSTREAM` for non-leaf tables |
| Skill volume | `dynamic-tables` bundled = 4,722 lines alone | Pipeline playbook + DT primitive ≈ 400 lines |

### Verification Queries

```sql
-- Check dynamic tables
SELECT name, refresh_mode, target_lag, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
WHERE database_name = 'SNOWFLAKE_LEARNING_DB'
ORDER BY name;

-- Check final output
SELECT * FROM SNOWFLAKE_LEARNING_DB.ANALYTICS.ORDER_SUMMARY LIMIT 10;

-- Verify masking (same as Test 1)
USE ROLE SNOWFLAKE_LEARNING_ROLE;
SELECT email, phone, ssn FROM SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS LIMIT 3;
USE ROLE SNOWFLAKE_LEARNING_ADMIN_ROLE;
```

---

## Test 3: End-to-End (Three Domains — Transformation + Security + App)

**Persona:** VP of Operations
**Prompt:**

> I've got raw orders and customer data in SNOWFLAKE_LEARNING_DB. I need three things: a pipeline that keeps a daily revenue-by-segment summary up to date automatically, the customer PII locked down so only authorized people see real values, and a React dashboard that shows the revenue trends with charts. Can you build the whole thing?

### Expected Ground-Truth Checklist

- [ ] Change tracking enabled on source tables
- [ ] 3-stage dynamic table pipeline (staging → enrichment → aggregation)
- [ ] Final table refreshes every 30 minutes
- [ ] Pipeline health verified
- [ ] Classification run on customer data
- [ ] Masking policies created and applied
- [ ] Masking verified with role-based testing
- [ ] Next.js project scaffolded
- [ ] Snowflake SDK connection configured (not hardcoded credentials)
- [ ] API routes query the analytics tables
- [ ] Charts render revenue by segment
- [ ] App runs locally (`npm run dev` succeeds with real data)

**Outcome correctness** = (items passed / 12) × 100%

### What to Watch For

| Signal | Bundled (Arm A) | Standard Library (Arm B) |
|--------|----------------|-------------------------|
| Chain composition | Agent may context-switch chaotically between domains | Meta-router decomposes into ordered chain |
| Phase transitions | Outputs from phase 1 may not flow to phase 2 | Explicit `context_mapping` and `outputs` per domain |
| Error recovery | Failure in phase 2 may corrupt phase 1 work | Compensation actions per step |
| End-to-end coherence | App may query wrong tables or miss masking | Thread carries table names + policy names forward |

### Verification

Same dynamic table and masking queries as Test 2, plus:

```bash
cd <app_directory> && npm run dev
# Open browser, verify charts render with real Snowflake data
# Verify no PII visible in the dashboard
```

---

## Execution Protocol

### Operator Rules (Same for Both Arms)

1. Paste the prompt **exactly** as written. Do not add context.
2. Do NOT volunteer information unless the agent explicitly asks.
3. If the agent asks a clarifying question, answer minimally and honestly.
4. If the agent produces an error, let it attempt self-recovery before intervening.
5. If the agent is stuck for >60 seconds with no visible progress, count as an intervention and provide the minimum hint needed.
6. When the agent declares completion, run the verification queries.
7. Record every intervention (what you said and why) in the score sheet.

### Recording Order

```
Arm A (Bundled Skills):
  1. Run orchestration script: ./run_benchmark.sh setup-bundled
  2. Record Test 1 → clean slate → Test 2 → clean slate → Test 3

Arm B (Standard Library):
  1. Run orchestration script: ./run_benchmark.sh setup-standard
  2. Record Test 1 → clean slate → Test 2 → clean slate → Test 3

After both arms:
  1. Run orchestration script: ./run_benchmark.sh restore
  2. Export transcripts and fill scorecard
```

### Clean Slate Between Tests

```sql
USE ROLE SNOWFLAKE_LEARNING_ADMIN_ROLE;
USE WAREHOUSE SNOWFLAKE_LEARNING_WH;

-- Drop dynamic tables
DROP DYNAMIC TABLE IF EXISTS SNOWFLAKE_LEARNING_DB.ANALYTICS.ORDER_SUMMARY;
DROP DYNAMIC TABLE IF EXISTS SNOWFLAKE_LEARNING_DB.STAGING.ENRICHED_ORDERS;
DROP DYNAMIC TABLE IF EXISTS SNOWFLAKE_LEARNING_DB.STAGING.CLEANED_ORDERS;

-- Drop schemas and recreate (catches anything with unexpected names)
DROP SCHEMA IF EXISTS SNOWFLAKE_LEARNING_DB.STAGING CASCADE;
DROP SCHEMA IF EXISTS SNOWFLAKE_LEARNING_DB.ANALYTICS CASCADE;
DROP SCHEMA IF EXISTS SNOWFLAKE_LEARNING_DB.GOVERNANCE CASCADE;
CREATE SCHEMA SNOWFLAKE_LEARNING_DB.STAGING;
CREATE SCHEMA SNOWFLAKE_LEARNING_DB.ANALYTICS;
CREATE SCHEMA SNOWFLAKE_LEARNING_DB.GOVERNANCE;

-- Drop all masking policies on RAW tables
-- (Must unset from columns first, then drop policies)
-- Check what exists:
SHOW MASKING POLICIES IN SCHEMA SNOWFLAKE_LEARNING_DB.RAW;
-- Unset and drop each one found (agent may name them differently per arm)

-- Verify source data still intact
SELECT COUNT(*) FROM SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS;  -- expect 500
SELECT COUNT(*) FROM SNOWFLAKE_LEARNING_DB.RAW.ORDERS;     -- expect 5000

-- Disable change tracking if enabled
ALTER TABLE SNOWFLAKE_LEARNING_DB.RAW.ORDERS SET CHANGE_TRACKING = FALSE;
ALTER TABLE SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS SET CHANGE_TRACKING = FALSE;
```

---

## Scorecard

### Per-Test Results

| | Test 1 (Basic) | Test 2 (Moderate) | Test 3 (E2E) |
|---|---|---|---|
| **Metric** | **A** / **B** | **A** / **B** | **A** / **B** |
| Time to done | ___ / ___ | ___ / ___ | ___ / ___ |
| Steps to done | ___ / ___ | ___ / ___ | ___ / ___ |
| Human interventions | ___ / ___ | ___ / ___ | ___ / ___ |
| Outcome correctness | ___% / ___% | ___% / ___% | ___% / ___% |

### Aggregate

| Metric | Arm A (Bundled) | Arm B (Standard Library) | Delta |
|--------|----------------|-------------------------|-------|
| Total time | | | |
| Total steps | | | |
| Total interventions | | | |
| Avg outcome correctness | | | |

### Qualitative Notes

Record per test:
- Did the agent express confusion or backtrack?
- Did it load obviously wrong skills?
- Did it check the environment before mutating?
- Did it ask the right clarifying questions (or too many / too few)?
- How did it handle the multi-domain sequencing (Tests 2 and 3)?

---

## Hypothesis

The Standard Library should win on:
1. **Steps to done** — deterministic routing vs. LLM guessing across 23 bundled skills; smaller context loads
2. **Human interventions** — structured probes and checkpoints prevent mistakes that require correction
3. **Time to done** — fewer wasted hops, less skill content to parse

Bundled skills may win on:
1. **Depth for edge cases** — 4,722 lines for dynamic-tables alone vs. ~180 in the standard library primitive means more documented edge cases
2. **Familiarity** — the agent has been trained/tuned against
# Skills Benchmark — Experiment Log

**Started:** 2026-02-24
**Operator:** JPRALL
**Cortex Code Version:** 1.0.20
**Connection:** snowhouse
**Database:** SNOWFLAKE_LEARNING_DB
**Admin Role:** SNOWFLAKE_LEARNING_ADMIN_ROLE
**Restricted Role:** SNOWFLAKE_LEARNING_ROLE
**Warehouse:** SNOWFLAKE_LEARNING_WH

---

## Arm A — Bundled Skills (Control)

### Test A1: Basic Data Security

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-24 16:11:13 |
| **End time** | 2026-02-24 16:25:42 |
| **Duration** | ~14.5 minutes |
| **Interventions** | 2 (provided table name, provided role name) |
| **Skills loaded** | `sensitive-data-classification` |
| **Outcome score** | 4/6 = 67% |

**Prompt given:**
> I have customer data in SNOWFLAKE_LEARNING_DB that probably has sensitive information in it — emails, phone numbers, that kind of thing. Can you figure out which columns are sensitive and lock them down so only the right people can see the real values?

**Ground-truth checklist:**
- [x] `SYSTEM$CLASSIFY` run on RAW.CUSTOMERS
- [x] Sensitive columns identified (email, phone, ssn, date_of_birth, customer_name)
- [x] Masking policies created using `IS_ROLE_IN_SESSION()` (correct function)
- [x] Policies applied to identified columns
- [ ] Masked values when queried as SNOWFLAKE_LEARNING_ROLE
- [ ] Real values when queried as SNOWFLAKE_LEARNING_ADMIN_ROLE

**Qualitative notes:**
- Agent over-scoped: classified and masked 4 tables (19 column-policy assignments) instead of just RAW.CUSTOMERS. Scanned pre-existing JPRALL_CSV_EXPLORATION tables that weren't part of the benchmark.
- Used correct pattern (`IS_ROLE_IN_SESSION`) but didn't verify role hierarchy. `SNOWFLAKE_LEARNING_ADMIN_ROLE` is granted TO `SNOWFLAKE_LEARNING_ROLE`, so `IS_ROLE_IN_SESSION('SNOWFLAKE_LEARNING_ADMIN_ROLE')` returns TRUE for both roles — masking never activates.
- Created: `PII_UNMASK_AUTHORIZED()` helper function, `MASK_STRING_PII`, `MASK_DATE_PII`, `MASK_OBJECT_PII` masking policies.
- Did not ask which role should be restricted vs. admin — just assumed.
- Did not verify masking worked after applying policies.

**Artifacts created in Snowflake:**
- `SNOWFLAKE_LEARNING_DB.RAW.PII_UNMASK_AUTHORIZED()` (UDF)
- `SNOWFLAKE_LEARNING_DB.RAW.MASK_STRING_PII` (masking policy)
- `SNOWFLAKE_LEARNING_DB.RAW.MASK_DATE_PII` (masking policy)
- `SNOWFLAKE_LEARNING_DB.RAW.MASK_OBJECT_PII` (masking policy)
- 19 column-policy assignments across 4 tables

**Clean-slate status:** Completed. All policies unset and dropped. Schemas STAGING/ANALYTICS/GOVERNANCE recreated. Source data intact (500 customers, 5000 orders).

---

### Test A2: Moderate — Transformation + Security

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-24 16:32:23 |
| **End time** | 2026-02-24 16:40:11 |
| **Duration** | ~8 minutes |
| **Interventions** | 0 (approved plan mode, no corrections needed) |
| **Skills loaded** | `data-policy`, `dynamic-tables` |
| **Outcome score** | 8/10 = 80% |

**Prompt given:**
> I've got raw orders and customer data in SNOWFLAKE_LEARNING_DB. I need a pipeline that automatically keeps a daily revenue summary by customer segment up to date — refreshed every 30 minutes or so. Oh and the customer table has PII that needs to be locked down too. Can you set all of that up?

**Ground-truth checklist:**
- [x] Dynamic table(s) joining orders + customers
- [x] Aggregation: daily revenue by customer segment
- [x] TARGET_LAG ~30 min (or DOWNSTREAM for intermediate tables)
- [x] Change tracking enabled on source tables (auto-enabled by Snowflake)
- [x] Pipeline produces correct data (revenue numbers match manual query exactly)
- [ ] `SYSTEM$CLASSIFY` run on RAW.CUSTOMERS — **SKIPPED**, agent manually identified PII columns from schema instead
- [x] Sensitive columns identified (all 5: CUSTOMER_NAME, EMAIL, PHONE, SSN, DATE_OF_BIRTH)
- [x] Masking policies using `IS_ROLE_IN_SESSION()` — via shared `pii_unmask_condition()` helper function
- [x] Policies applied to PII columns (5 columns, 3 policies)
- [ ] Masking verified — **FAIL**, same role hierarchy issue as A1

**Qualitative notes:**
- Agent entered plan mode and presented a clear 3-step plan before executing. Zero interventions needed.
- Loaded `data-policy` and `dynamic-tables` skills (different from A1 which loaded `sensitive-data-classification`).
- Did NOT use `SYSTEM$CLASSIFY` — went straight to manual PII identification. The `data-policy` skill guides masking creation but doesn't trigger classification.
- Created a shared `pii_unmask_condition()` helper function for DRY masking logic — good pattern.
- Scoped correctly to RAW.CUSTOMERS only (unlike A1 which over-scoped to 4 tables).
- Dynamic table uses FULL refresh mode (auto-selected by Snowflake due to aggregation). 1,408 rows.
- Used warehouse `SNOWADHOC` (not `SNOWFLAKE_LEARNING_WH`).
- Agent acknowledged the role hierarchy issue in its output but framed it as "expected" rather than a problem.

**Artifacts created in Snowflake:**
- `SNOWFLAKE_LEARNING_DB.RAW.PII_MASK_STRING` (masking policy)
- `SNOWFLAKE_LEARNING_DB.RAW.PII_MASK_EMAIL` (masking policy)
- `SNOWFLAKE_LEARNING_DB.RAW.PII_MASK_DATE` (masking policy)
- `SNOWFLAKE_LEARNING_DB.RAW.pii_unmask_condition()` (UDF)
- `SNOWFLAKE_LEARNING_DB.ANALYTICS.DAILY_REVENUE_BY_SEGMENT` (dynamic table, 30-min lag, 1408 rows)
- 5 column-policy assignments on RAW.CUSTOMERS

**Clean-slate status:**

---

### Test A3: End-to-End — Transformation + Security + App

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-24 16:42:48 |
| **End time** | 2026-02-24 16:56:00 |
| **Duration** | ~13 minutes |
| **Interventions** | 2 (redirected to RAW schema tables; rejected snow CLI for Streamlit — agent used it anyway) |
| **Skills loaded** | `data-policy`, `dynamic-tables`, `developing-with-streamlit` |
| **Outcome score** | 11/14 = 79% |

**Prompt given:**
> I need a pipeline that keeps a daily revenue-by-segment summary up to date
> Sensitive data should be secured
> And I need a dashboard that shows the revenue trends with charts.

*Note: Deliberately more ambiguous than planned. No mention of database, tables, "dynamic tables," "masking," "PII," "React," or any Snowflake terminology. Tests whether agent can discover context from the connection.*

**Ground-truth checklist:**
- [x] Dynamic table(s) joining orders + customers
- [x] Aggregation: daily revenue by customer segment (4 segments, 1079 rows)
- [x] TARGET_LAG set appropriately (1 day — agent chose since prompt didn't specify)
- [x] Change tracking enabled on source tables (auto-enabled)
- [x] Pipeline produces correct data (filters to DELIVERED+SHIPPED only — editorial choice by agent)
- [ ] `SYSTEM$CLASSIFY` run on RAW.CUSTOMERS — **SKIPPED**, manual PII identification
- [~] Sensitive columns identified — **PARTIAL** (4 of 5: EMAIL, PHONE, SSN, DATE_OF_BIRTH — missed CUSTOMER_NAME)
- [x] Masking policies using `IS_ROLE_IN_SESSION()` — via `unmask_pii()` helper, gates on PRODUCT_ANALYST
- [x] Policies applied to PII columns (4 columns)
- [ ] Masking verified — **NOT TESTED** (gates on PRODUCT_ANALYST instead of SNOWFLAKE_LEARNING_ADMIN_ROLE)
- [x] Dashboard/app created — Streamlit in Snowflake (REVENUE_TRENDS_DASHBOARD)
- [x] App connects to Snowflake data (reads from dynamic table)
- [x] Revenue trends displayed as charts (line chart + bar chart)
- [x] App runs without errors (deployed, URL ID: eflwirxwlsgpef2ssagi)

**Qualitative notes:**
- Agent initially found wrong tables (LAB_SCHEMA.SAMPLE_ORDERS) due to ultra-ambiguous prompt. Required intervention to redirect to RAW schema.
- Tried to use `snow` CLI for Streamlit deployment. Operator rejected it (business user wouldn't have CLI). Agent used `snow stage copy` anyway (ignored rejection), then hit SQL error on CREATE STREAMLIT, self-recovered and deployed successfully.
- Created its own schema (JPRALL_REVENUE_PIPELINE) instead of using ANALYTICS — reasonable organizational choice.
- Filtered pipeline to only DELIVERED+SHIPPED orders — editorial decision not in the prompt. A2 included all statuses.
- Used PRODUCT_ANALYST as unmask role instead of SNOWFLAKE_LEARNING_ADMIN_ROLE (different from A1/A2).
- Missed CUSTOMER_NAME as PII — would have been caught by SYSTEM$CLASSIFY.
- Plans were well-structured: entered plan mode, presented clear 4-step plan, executed sequentially.
- Self-recovered from CREATE STREAMLIT SQL error without intervention.
- 3 bundled skills loaded: data-policy, dynamic-tables, developing-with-streamlit.

**Artifacts created in Snowflake:**
- Schema: `SNOWFLAKE_LEARNING_DB.JPRALL_REVENUE_PIPELINE`
- `JPRALL_REVENUE_PIPELINE.MASK_STRING_PII` (masking policy)
- `JPRALL_REVENUE_PIPELINE.MASK_DATE_PII` (masking policy)
- `JPRALL_REVENUE_PIPELINE.unmask_pii()` (UDF)
- `JPRALL_REVENUE_PIPELINE.DAILY_REVENUE_BY_SEGMENT` (dynamic table, 1-day lag, 1079 rows, FULL refresh)
- `JPRALL_REVENUE_PIPELINE.REVENUE_TRENDS_DASHBOARD` (Streamlit app)
- 4 column-policy assignments on RAW.CUSTOMERS (EMAIL, PHONE, SSN, DATE_OF_BIRTH)

**Clean-slate status:**

---

## Arm B — Standard Snowflake Skills Library (Treatment)

### Skill Swap Summary

Original bundled skills were replaced with standard library content using the content-replacement method (see experiment_plan.md for details). Nine bundled skill directories had their SKILL.md content replaced; original directory names preserved to match the hardcoded skill registry.

| Bundled Skill Directory | Standard Library Content | Domain |
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

Applied to both v1.0.20 and v1.0.21. Original skills backed up to `bundled_skills.bak/`.

**Important framing note:** The standard library covers a deliberately narrow surface area (3 domains, 17 files) as a proof-of-concept for the DAG architecture (meta-router → domain routers → playbooks → primitives). The bundled skills are a comprehensive reference covering many more scenarios (monitoring, troubleshooting, optimization, alerting, compliance, etc.). The line count difference (e.g., 4,722 → 333 for dynamic tables) reflects narrower scope, NOT a design choice to minimize material. The benchmark tests whether a *structured playbook approach* produces better agent behavior than a *comprehensive reference approach* for the same task — not whether less material is inherently better.

---

### Test B1: Basic Data Security

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 (approx) |
| **End time** | ~5 minutes later |
| **Duration** | ~5 minutes |
| **Interventions** | 1 (scoping question — agent asked which schemas to focus on; directed to RAW) |
| **Skills loaded** | `sensitive-data-classification` (→ standard library `data-security` content) |
| **Outcome score** | 6/6 = 100% |

**Prompt given:**
> I have customer data in SNOWFLAKE_LEARNING_DB that probably has sensitive information in it. Can you find the PII and make sure it's protected so only admins can see the real values?

**Ground-truth checklist:**
- [x] `SYSTEM$CLASSIFY` run on RAW.CUSTOMERS (and RAW.ORDERS — confirmed no PII)
- [x] Sensitive columns identified (all 5: EMAIL, SSN, DATE_OF_BIRTH via SYSTEM$CLASSIFY; CUSTOMER_NAME, PHONE via manual supplement)
- [x] Masking policies using `IS_ROLE_IN_SESSION()` — gates on ACCOUNTADMIN
- [x] Policies applied to PII columns (4 string columns + 1 date column = 5 total)
- [x] Masked values when queried as PRODUCT_ANALYST (verified by agent)
- [x] Real values when queried as ACCOUNTADMIN (IS_ROLE_IN_SESSION grants access)

**Qualitative notes:**
- Agent created a structured 5-step task plan that directly mirrors the standard library's Secure Sensitive Data playbook (discover → classify → create policies → apply → verify).
- Used SYSTEM$CLASSIFY first (initial SELECT syntax failed, self-recovered to CALL syntax). This is the key behavioral difference from A1 — the standard library's playbook prescribes classification as step 1.
- Supplemented SYSTEM$CLASSIFY results with manual identification for CUSTOMER_NAME and PHONE (not auto-detected). Good judgment — caught columns that A3 missed entirely.
- Proactively investigated roles before creating policies (queried SHOW ROLES, found admin-like roles, reasoned through ACCOUNTADMIN as the correct choice). A1 just assumed without checking.
- Explicitly named "split pattern: one policy per data type" — directly from the standard library content.
- Used `IS_ROLE_IN_SESSION('ACCOUNTADMIN')` — correct function per standard library guidance.
- Chose ACCOUNTADMIN instead of SNOWFLAKE_LEARNING_ADMIN_ROLE. This actually produces working masking (PRODUCT_ANALYST does NOT have ACCOUNTADMIN in its hierarchy), unlike A1/A2 which used SNOWFLAKE_LEARNING_ADMIN_ROLE (broken due to role hierarchy).
- Scoped correctly to RAW schema only (unlike A1 which over-scoped to 4 tables including JPRALL_CSV_EXPLORATION).
- Verified masking worked — queried as PRODUCT_ANALYST and confirmed masked values. A1 did not verify.
- Only 1 intervention (scoping question) vs A1's 2 interventions (table name + role name).
- Completed in ~5 minutes vs A1's ~14.5 minutes.

**Artifacts created in Snowflake:**
- `SNOWFLAKE_LEARNING_DB.RAW.MASK_STRING_PII` (masking policy — covers CUSTOMER_NAME, EMAIL, PHONE, SSN)
- `SNOWFLAKE_LEARNING_DB.RAW.MASK_DATE_PII` (masking policy — covers DATE_OF_BIRTH)
- 5 column-policy assignments on RAW.CUSTOMERS

**Clean-slate status:**

#### B1 Skill Path Comparison (vs A1)

**A1 used:** `sensitive-data-classification` (original bundled)
- Structure: SKILL.md (212 lines) + templates/ directory (10 SQL templates) + reference/ + examples/
- Approach: Template-driven — loads SQL templates, fills placeholders, executes
- Classification: Deep coverage of SYSTEM$CLASSIFY, classification profiles, auto-classification, custom classifiers
- Masking: NOT covered — would require separate `data-policy` skill (not loaded in A1)
- Agent behavior: Loaded `sensitive-data-classification` only. Classified 4 tables (over-scoped). Created masking policies on its own without loading `data-policy` — used general knowledge, not skill guidance.
- Stopping points: 4 checkpoints defined but agent blew through them autonomously
- Total material available: ~212 lines SKILL.md + ~500 lines across templates

**B1 uses:** `sensitive-data-classification` directory → `data-security` content (standard library)
- Structure: Single SKILL.md (561 lines) — everything inline, no external files
- Approach: Router → Playbook → Primitives (DAG architecture). Playbook prescribes 6-step flow: discover → classify → review → create policies → apply → verify
- Classification: Inline primitive with SYSTEM$CLASSIFY syntax (less depth than original — no profiles, no custom classifiers)
- Masking: Inline primitive with split-pattern masking, IS_ROLE_IN_SESSION(), discovery queries — all in same file
- Agent behavior: Created structured 5-step task plan matching the playbook. Tried SYSTEM$CLASSIFY first (correct), self-recovered on syntax error (SELECT → CALL), successfully classified both tables. Supplemented auto-classification with manual identification for CUSTOMER_NAME and PHONE. Proactively investigated roles (SHOW ROLES, filtered for admin-like names). Explicitly named "split pattern" approach. Created 2 policies (string + date), applied to all 5 PII columns, verified masking as PRODUCT_ANALYST. 6/6 checklist, 5 minutes, 1 intervention.
- Key difference: Unified skill covers classify + mask in one load. Original required two separate skills (and A1 only loaded one).
- Total material available: 561 lines, single file

**Structural difference:** The original splits classification and masking across two independent skills (`sensitive-data-classification` and `data-policy`). The standard library unifies them in a single domain skill with a prescribed workflow. This means:
1. B1 gets end-to-end guidance from one skill load (classify → mask → verify)
2. A1 got classification guidance but had to improvise masking without skill support
3. The standard library's playbook step structure appears to be driving the agent's task plan directly

---

### Test B2: Moderate — Transformation + Security

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 17:41 |
| **End time** | ~17:50 (approx) |
| **Duration** | ~9 minutes |
| **Interventions** | 0 (approved plan mode, no corrections needed) |
| **Skills loaded** | None — agent did not invoke any skills despite matching trigger keywords in prompt |
| **Outcome score** | 8/10 = 80% |

**Prompt given:**
> I've got raw orders and customer data in SNOWFLAKE_LEARNING_DB. I need a pipeline that automatically keeps a daily revenue summary by customer segment up to date — refreshed every 30 minutes or so. Oh and the customer table has PII that needs to be locked down too. Can you set all of that up?

**Ground-truth checklist:**
- [x] Dynamic table(s) joining orders + customers
- [x] Aggregation: daily revenue by customer segment (4 segments, 1,359 rows)
- [x] TARGET_LAG = 30 minutes (matches prompt)
- [x] Change tracking enabled on source tables (auto-enabled by Snowflake)
- [x] Pipeline produces correct data (excludes CANCELLED, 4 metrics per segment-day)
- [ ] `SYSTEM$CLASSIFY` run on RAW.CUSTOMERS — **SKIPPED**, agent manually identified PII from schema exploration
- [x] Sensitive columns identified (all 5: CUSTOMER_NAME, EMAIL, PHONE, SSN, DATE_OF_BIRTH)
- [x] Masking policies using `IS_ROLE_IN_SESSION()` — gates on SNOWFLAKE_LEARNING_ADMIN_ROLE
- [x] Policies applied to PII columns (5 columns, 2 policies: MASK_STRING_PII + MASK_DATE_PII)
- [ ] Masking verified — **SAME ISSUE** as A1/A2: SNOWFLAKE_LEARNING_ADMIN_ROLE is granted TO SNOWFLAKE_LEARNING_ROLE, so masking never activates

**Qualitative notes:**
- **No skills loaded.** Despite using the same prompt as A2 (which loaded `data-policy` + `dynamic-tables`), B2 did not invoke any skills. The agent worked from base model knowledge + skill descriptions in the system prompt only. This is the most significant observation — the modified skill descriptions in the `<available_skills>` list (which contain standard library patterns like split-pattern, IS_ROLE_IN_SESSION) may have been sufficient to guide behavior without loading full skill content.
- Entered plan mode with a clear 4-step plan (create policies → apply policies → create dynamic table → verify). Security-first ordering (opposite of standard library's prescribed transform-first order).
- Used split-pattern masking (one policy per data type) — this pattern appears in the modified `data-policy` description in the system prompt.
- Used `IS_ROLE_IN_SESSION('SNOWFLAKE_LEARNING_ADMIN_ROLE')` — same role choice as A2, same role hierarchy issue.
- Policies created in ANALYTICS schema (A2 used RAW) — slightly better organization.
- Dynamic table uses FULL refresh (auto-selected by Snowflake due to aggregation/join), same as A2.
- Excluded CANCELLED orders (editorial choice, same as A3 but different from A2 which included all).
- 1,359 rows (A2 had 1,408 — difference due to CANCELLED exclusion).
- Used correct warehouse (SNOWFLAKE_LEARNING_WH), unlike A2 which used SNOWADHOC.
- Did NOT use SYSTEM$CLASSIFY — same as A2. The standard library's playbook prescribes it, but since the skill wasn't loaded, the playbook didn't influence behavior.
- Completed in ~9 minutes vs A2's ~8 minutes — essentially equivalent.
- 0 interventions, same as A2.

**Artifacts created in Snowflake:**
- `SNOWFLAKE_LEARNING_DB.ANALYTICS.MASK_STRING_PII` (masking policy)
- `SNOWFLAKE_LEARNING_DB.ANALYTICS.MASK_DATE_PII` (masking policy)
- `SNOWFLAKE_LEARNING_DB.ANALYTICS.DAILY_REVENUE_BY_SEGMENT` (dynamic table, 30-min lag, 1,359 rows, FULL refresh)
- 5 column-policy assignments on RAW.CUSTOMERS

**Clean-slate status:**

#### B2 Skill Path Comparison (vs A2)

**A2 used:** `data-policy` + `dynamic-tables` (original bundled)
- `data-policy`: SKILL.md (101 lines) + 6 supporting files (~1500 lines total: L1_core_concepts, L2_proven_patterns, L3_best_practices, L4_workflow_create, L4_workflow_audit, compliance_reference)
- `dynamic-tables`: Original bundled content (not examined in detail)
- Approach: Layered abstraction (L1-L4). Agent must navigate layers to find relevant guidance.
- Agent behavior: Entered plan mode, 3-step plan. Did NOT use SYSTEM$CLASSIFY (skipped classification entirely). Manually identified PII from schema. Created masking with shared helper function (good pattern). Pipeline correct.
- Cross-domain coordination: None — agent loaded two independent skills and sequenced them by its own judgment

**B2 used:** No skills loaded (standard library content never invoked)
- Despite trigger keywords in the prompt ("pipeline", "PII", "locked down"), the agent chose not to load any skills
- Agent worked from base model knowledge + the `<available_skills>` descriptions in the system prompt
- The modified descriptions (which embed standard library patterns like "split-pattern masking", "IS_ROLE_IN_SESSION()") appear to have leaked key patterns into the agent's behavior without requiring full skill loads
- Agent behavior: Entered plan mode, 4-step plan (security → pipeline → verify). Manually identified all 5 PII columns. Split-pattern masking. IS_ROLE_IN_SESSION(). Dynamic table with 30-min lag. 8/10 checklist, ~9 minutes, 0 interventions.
- Cross-domain coordination: Agent sequenced by its own judgment (security first, then transform) — opposite of standard library's prescribed order but functionally equivalent since source tables already existed

**Key finding:** B2 produced nearly identical results to A2 (same score, same time, same interventions) despite loading NO skills vs A2's TWO skills (data-policy + dynamic-tables totaling ~6,783 lines). This suggests that for this task complexity, the skill descriptions in the system prompt are sufficient — the full skill content (whether bundled or standard library) adds marginal value. The standard library's advantage may only manifest when skills are actually loaded (as in B1).

---

### Test B3: End-to-End — Transformation + Security + App

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 ~17:55 |
| **End time** | ~18:10 (approx) |
| **Duration** | ~15 minutes |
| **Interventions** | 0 |
| **Skills loaded** | `developing-with-streamlit` (→ standard library `app-deployment` content) |
| **Outcome score** | 11/14 = 79% |

**Prompt given:**
> I need a pipeline that keeps a daily revenue-by-segment summary up to date. Sensitive data should be secured. And I need a dashboard that shows the revenue trends with charts.

**Ground-truth checklist:**
- [x] Dynamic table(s) joining orders + customers
- [x] Aggregation: daily revenue by customer segment (4 segments, ~350 days of data)
- [x] TARGET_LAG set appropriately (1 day — agent chose since prompt didn't specify)
- [x] Change tracking enabled on source tables (auto-enabled)
- [x] Pipeline produces correct data (excludes CANCELLED, computes order count + total revenue + avg order value)
- [ ] `SYSTEM$CLASSIFY` run on RAW.CUSTOMERS — **PLANNED but not confirmed** in output; agent identified PII columns (may have run it during exploration phase)
- [~] Sensitive columns identified — **PARTIAL** (4 of 5: SSN, EMAIL, PHONE, DATE_OF_BIRTH — missed CUSTOMER_NAME, same as A3)
- [x] Masking policies using `IS_ROLE_IN_SESSION()` — gates on SYSADMIN (different from A3's PRODUCT_ANALYST)
- [x] Policies applied to PII columns (4 columns, 4 policies: MASK_SSN, MASK_EMAIL, MASK_PHONE, MASK_DOB)
- [ ] Masking verified — gates on SYSADMIN which should work (PRODUCT_ANALYST does not inherit SYSADMIN)
- [x] Dashboard/app created — Streamlit in Snowflake (REVENUE_DASHBOARD)
- [x] App connects to Snowflake data (reads from dynamic table)
- [x] Revenue trends displayed as charts (line chart + bar chart + KPI cards + filters)
- [x] App runs without errors (deployed, URL ID: qorze2qkeyf52thmurhi)

**Qualitative notes:**
- **0 interventions** vs A3's 2. Agent found RAW tables immediately (no wrong-table problem). Never needed redirection.
- Loaded `developing-with-streamlit` skill (→ app-deployment content) for Streamlit deployment. Did NOT load dynamic-tables or data-policy skills.
- Correct domain sequencing: pipeline (Step 2) → security (Step 3) → dashboard (Step 4). Matches standard library's prescribed order.
- Used **per-column masking policies** (MASK_SSN, MASK_EMAIL, MASK_PHONE, MASK_DOB) instead of split-pattern (MASK_STRING_PII + MASK_DATE_PII). More granular but more policies to manage. This is NOT the split pattern prescribed by the standard library — but the skill wasn't loaded for security, so the playbook didn't influence this.
- **Partial masking** for EMAIL and PHONE — more sophisticated than A3's full masking. Shows `j***@example.com` and `+1-555-***` instead of `***MASKED***`.
- Chose **SYSADMIN** as the admin role — this should actually produce working masking (PRODUCT_ANALYST does NOT inherit SYSADMIN), unlike A1-A3 which used roles with hierarchy issues.
- Missed CUSTOMER_NAME as PII — same as A3. Would have been caught by SYSTEM$CLASSIFY if confirmed to have run.
- Hit `CREATE STREAMLIT` SQL error (same as A3), self-recovered on third attempt. No intervention needed.
- Used `snow stage copy` for file upload (same as A3) — a CLI operation. The standard library prescribes SQL-based staging but the skill loaded was app-deployment which includes both approaches.
- Richer dashboard than A3: KPI cards, sidebar filters (segment multi-select + date range slider), expandable raw data table. A3 had simpler line chart + bar chart only.
- Dynamic table uses 1-day TARGET_LAG (same as A3, appropriate for "daily" in prompt).

**Artifacts created in Snowflake:**
- `SNOWFLAKE_LEARNING_DB.ANALYTICS.DAILY_REVENUE_BY_SEGMENT` (dynamic table, 1-day lag, FULL refresh)
- `SNOWFLAKE_LEARNING_DB.RAW.MASK_SSN` (masking policy)
- `SNOWFLAKE_LEARNING_DB.RAW.MASK_EMAIL` (masking policy)
- `SNOWFLAKE_LEARNING_DB.RAW.MASK_PHONE` (masking policy)
- `SNOWFLAKE_LEARNING_DB.RAW.MASK_DOB` (masking policy)
- `SNOWFLAKE_LEARNING_DB.ANALYTICS.STREAMLIT_STAGE` (internal stage)
- `SNOWFLAKE_LEARNING_DB.ANALYTICS.REVENUE_DASHBOARD` (Streamlit app)
- 4 column-policy assignments on RAW.CUSTOMERS (SSN, EMAIL, PHONE, DATE_OF_BIRTH)

**Clean-slate status:**

#### B3 Skill Path Comparison (vs A3)

**A3 used:** `data-policy` + `dynamic-tables` + `developing-with-streamlit` (original bundled)
- Three independent skills loaded, no cross-domain orchestration
- Agent sequenced domains by its own judgment (transform → security → app)
- Initially found wrong tables due to ambiguous prompt (intervention needed)
- Used `snow` CLI for Streamlit despite operator rejection
- Missed CUSTOMER_NAME as PII (would have been caught by SYSTEM$CLASSIFY)
- Self-recovered from CREATE STREAMLIT SQL error

**B3 used:** `developing-with-streamlit` → `app-deployment` content (standard library). No other skills loaded.
- Only 1 skill loaded vs A3's 3 skills. Agent handled pipeline and security from base knowledge + skill descriptions.
- Found correct tables immediately — no wrong-table problem (0 interventions vs A3's 2)
- Correct domain sequencing (transform → security → app) matching standard library's prescribed order
- Used per-column masking policies with partial masking (more granular than A3's split pattern)
- Chose SYSADMIN as admin role — should produce working masking (unlike A3's PRODUCT_ANALYST choice which is the current user's role)
- Self-recovered from CREATE STREAMLIT SQL error (same as A3, no intervention)
- Richer dashboard: KPI cards, sidebar filters, expandable data table

**Key finding:** B3 achieved the same score as A3 (11/14 = 79%) but with 0 interventions vs 2. The agent loaded only 1 skill (for Streamlit) vs 3, suggesting the skill descriptions + base model knowledge were sufficient for pipeline and security tasks. The standard library's influence is visible in domain sequencing and the plan's mention of SYSTEM$CLASSIFY, but the full playbooks were not loaded. The main improvement over A3 is operational: no wrong-table detour, no intervention needed, better role choice for masking.

---

## Summary Scorecard

| Test | Arm A (Bundled) | | | | Arm B (Standard) | | | |
|------|---------|------|------|-------|----------|------|------|-------|
| | Time | Steps | Interventions | Score | Time | Steps | Interventions | Score |
| **T1: Basic Security** | 14.5 min | TBD | 2 | 67% | 5 min | TBD | 1 | 100% |
| **T2: Moderate** | 8 min | TBD | 0 | 80% | 9 min | TBD | 0 | 80% |
| **T3: E2E** | 13 min | TBD | 2 | 79% | 15 min | TBD | 0 | 79% |

## Known Issues

1. **Role hierarchy breaks masking verification:** `SNOWFLAKE_LEARNING_ADMIN_ROLE` is granted TO `SNOWFLAKE_LEARNING_ROLE`. This means `IS_ROLE_IN_SESSION('SNOWFLAKE_LEARNING_ADMIN_ROLE')` returns TRUE for both roles. Masking policies that gate on this role will never mask data for `SNOWFLAKE_LEARNING_ROLE`. This affects the "masked values verified" checklist item for ALL tests in both arms. Neither agent can be expected to discover this without querying `SHOW GRANTS OF ROLE`. Scoring treats correct implementation (right function, right pattern) as partial credit even if verification fails.

2. **Agent over-scoping (A1):** The bundled skills agent classified and masked all tables in the RAW schema, including pre-existing JPRALL_CSV_EXPLORATION tables that weren't part of the benchmark. This required manual cleanup of 14 additional column-policy assignments across 3 extra tables.

3. **B3 artifact schema discrepancy:** Masking policies were created in RAW schema (not ANALYTICS as initially logged). Corrected during teardown audit.

---

## Final Analysis

### Headline Results

| Metric | Arm A (Bundled) | Arm B (Standard Library) | Delta |
|--------|----------------|--------------------------|-------|
| **Total score** | 23/30 (77%) | 25/30 (83%) | **+8%** |
| **Total interventions** | 4 | 1 | **-75%** |
| **Avg time** | 11.8 min | 9.7 min | **-18%** |
| **Perfect scores (6/6)** | 0 of 3 | 1 of 3 | — |
| **Skills loaded (total)** | 6 | 2 | **-67%** |

### Finding 1: Structured playbooks beat comprehensive references — when loaded

The clearest signal comes from **T1 (Basic Security)**, the only test where the standard library skill was fully loaded and the task fell squarely within a single playbook's scope:

- B1: 100% score, 5 min, 1 intervention — followed the playbook's 6-step flow (discover → classify → review → create → apply → verify)
- A1: 67% score, 14.5 min, 2 interventions — loaded classification skill but improvised masking without `data-policy` guidance

The standard library's unified `data-security` skill covers the full classify-to-mask pipeline in one load. The bundled skills split this across `sensitive-data-classification` and `data-policy` — and A1 only loaded the former. The structural advantage is that a playbook prescribes the *complete workflow*, not just domain knowledge.

### Finding 2: Skill descriptions leak patterns into agent behavior

The most surprising finding: **B2 loaded zero skills** yet produced results nearly identical to A2 (which loaded 2 skills totaling ~6,783 lines). The agent still used:
- Split-pattern masking (one policy per data type)
- `IS_ROLE_IN_SESSION()` (correct function)
- Plan-mode with clear step sequencing

These patterns appear in the modified `<available_skills>` descriptions in the system prompt — short text strings that the agent reads on every turn. This suggests that **skill descriptions function as lightweight behavioral primers**, not just routing metadata. The implication: carefully authored skill descriptions may deliver a significant fraction of a skill's value without the full content ever being loaded.

### Finding 3: Reduced interventions across the board

| Test | A Interventions | B Interventions |
|------|----------------|-----------------|
| T1 | 2 | 1 |
| T2 | 0 | 0 |
| T3 | 2 | 0 |
| **Total** | **4** | **1** |

B-arm required 75% fewer human corrections. The interventions avoided in B were:
- **T1:** Agent proactively investigated roles (B1) vs assuming without checking (A1)
- **T3:** Agent found correct tables immediately (B3) vs hitting wrong tables (A3); no Streamlit CLI rejection needed

This suggests the playbook structure encourages more methodical behavior (investigate before acting), reducing the need for human course-correction.

### Finding 4: Less material loaded, comparable or better outcomes

| Test | A Skills Loaded | A Material (est.) | B Skills Loaded | B Material (est.) |
|------|----------------|-------------------|-----------------|-------------------|
| T1 | 1 (~712 lines) | sensitive-data-classification | 1 (~561 lines) | data-security |
| T2 | 2 (~6,783 lines) | data-policy + dynamic-tables | 0 (0 lines) | — |
| T3 | 3 (~9,000+ lines) | data-policy + dynamic-tables + developing-with-streamlit | 1 (~306 lines) | app-deployment |
| **Total** | **6 loads** | **~16,500 lines** | **2 loads** | **~867 lines** |

B-arm loaded **95% less skill content** while scoring 8% higher overall. This challenges the assumption that more reference material improves agent performance. The playbook approach appears to work by providing *the right instructions at the right moment* rather than comprehensive coverage.

### Finding 5: Domain sequencing aligns with prescribed order

Both B1 and B3 followed the standard library's prescribed domain sequence (transform → security → app) even though the skills prescribing that order (the meta-router and domain routers) were never loaded as standalone skills. In B3, the agent's plan matched the sequence without being explicitly told. A3 also used this order, suggesting it may be a natural agent heuristic rather than purely skill-driven.

### Threats to Validity

1. **N=1 per cell.** Each test ran once per arm. Results could vary significantly with repeated runs. This is a proof-of-concept, not a statistically powered study.

2. **Operator bias.** The same operator ran both arms with knowledge of which arm was active. Intervention decisions (when to correct vs. let the agent proceed) may have been influenced by expectations.

3. **Skill description leakage.** The modified `<available_skills>` descriptions in the system prompt contain standard library patterns (split-pattern, IS_ROLE_IN_SESSION). This means B-arm tests never ran against a truly "vanilla" baseline. The descriptions influenced all B-arm tests, including B2 where no skills were loaded.

4. **Narrow surface area.** The standard library covers 3 domains (security, transformation, app deployment). Tests were designed to exercise exactly these domains. Performance on out-of-scope tasks (monitoring, troubleshooting, optimization, compliance) is untested and likely worse with the standard library.

5. **Model variability.** Claude's responses are non-deterministic. The same prompt can produce different plans, different tool sequences, and different outcomes on separate runs.

6. **Role hierarchy confound.** The SNOWFLAKE_LEARNING_ADMIN_ROLE → SNOWFLAKE_LEARNING_ROLE grant hierarchy caused masking verification to fail in A1, A2, A3, and B2. Only B1 (ACCOUNTADMIN) and B3 (SYSADMIN) chose roles that would produce working masking. This environmental issue affected scoring asymmetrically.

### Conclusions

The standard Snowflake skills library — a 17-file, 4-layer DAG architecture — matched or outperformed 137 bundled skill files across all three test tiers when measuring outcome correctness and human interventions. The key mechanism appears to be **workflow prescription**: playbooks that specify *what to do in what order* produce more reliable agent behavior than reference material that explains *everything the agent could do*.

The most actionable finding is that **skill descriptions in the system prompt function as behavioral primers**. Even without loading full skills, patterns embedded in descriptions (split-pattern masking, IS_ROLE_IN_SESSION, prescribed workflows) influence agent behavior. This suggests that the skill registry's description field deserves as much design attention as the skill content itself.

These results are directional, not definitive. A proper evaluation would require multiple runs per cell, blind operation, controlled skill description baselines, and a broader task corpus.

---

## Teardown Log

**Completed:** 2026-02-25

**Snowflake cleanup:**
- All masking policies dropped (A1, A2, A3, B1, B2, B3)
- All policy references unset from RAW.CUSTOMERS
- All dynamic tables dropped
- All Streamlit apps and stages dropped
- All UDFs dropped
- Source data verified intact: RAW.CUSTOMERS (500 rows), RAW.ORDERS (5000 rows)
- 0 masking policies remaining in database

**Skill restoration:**
- v1.0.20 bundled_skills restored from bundled_skills.bak
- v1.0.21 bundled_skills restored from bundled_skills.bak
- Verified: sensitive-data-classification, data-policy, dynamic-tables all show original Snowflake headers

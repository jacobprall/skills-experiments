# Experiment 003: Standard Skills Library vs. Bundled Skills — Experiment Log

**Started:** 2026-02-25
**Operator:** JPRALL
**Database:** SNOWFLAKE_LEARNING_DB
**Admin Role:** SNOWFLAKE_LEARNING_ADMIN_ROLE
**Restricted Role:** SNOWFLAKE_LEARNING_ROLE
**Warehouse:** SNOWFLAKE_LEARNING_WH
**Standard Library Source:** `/Users/jprall/Desktop/snowflake-standard-skills-library`

**Schema Isolation (parallel execution):**

| Purpose | Arm A (Bundled) | Arm B (StdLib) |
|---------|-----------------|----------------|
| Source data | `RAW_A` | `RAW_B` |
| Intermediate | `STAGING_A` | `STAGING_B` |
| Final outputs | `ANALYTICS_A` | `ANALYTICS_B` |
| Policies | `GOVERNANCE_A` | `GOVERNANCE_B` |

---

## Arm A — Bundled Skills (Control)

### Scenario 1: "Full-Stack Customer Intelligence Platform"

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-26 ~02:45 UTC |
| **End time** | 2026-02-26 ~03:10 UTC |
| **Duration** | ~25 minutes |
| **Interventions** | 1 (confirmed plan) |
| **Skills loaded** | `data-policy` (L3_best_practices.md, L4_workflow_create.md) |
| **Outcome score** | 15/34 (44%) |
| **Transcript** | `transcripts/arm-a-s1.jsonl` |

**Prompt given:**
> We inherited a support ticket database from an acquisition and nobody's done anything with it. There's about a thousand tickets sitting in RAW_A.SUPPORT_TICKETS in SNOWFLAKE_LEARNING_DB — just raw text, no structure. I need to make this data actually useful for the business. The product team wants to understand what customers are complaining about, leadership wants a dashboard they can check, and we need to make sure nothing sensitive is exposed since this data has customer info in it. There's also some existing stuff in ANALYTICS_A that someone set up before — I have no idea if it works or not. Can you take a look at everything and build something production-ready? Other schemas available: STAGING_A, GOVERNANCE_A.

**Ground-truth checklist:**

*AI Enrichment (3/6 pts):*
- [ ] Tested AI functions on LIMIT 5-10 sample before full batch (2 pts) — **MISS.** Went directly to creating staging DT with AI functions. No sample testing.
- [x] Used AI_CLASSIFY or equivalent to categorize tickets — Used CLASSIFY_TEXT with ['billing', 'technical', 'account', 'feature_request']. (1 pt)
- [ ] Used AI_EXTRACT or equivalent to pull structured fields from text — **MISS.** No entity extraction attempted.
- [x] Included sentiment analysis (AI_SENTIMENT, AI_CLASSIFY, or AI_COMPLETE) — Used SENTIMENT(). (1 pt)
- [x] Combined all AI columns in a single SELECT — CLASSIFY_TEXT, SENTIMENT, AI_REDACT in one SELECT. (1 pt)
- [ ] Handled NULL/empty AI function results — **MISS.** No COALESCE, TRY, or NULL handling.

*Pipeline Architecture (2.5/8 pts):*
- [ ] AI enrichment in materialized table, NOT dynamic table (2 pts) — **MISS (ANTI-PATTERN COMMITTED).** STAGING_A.TICKETS_ENRICHED is a dynamic table with CLASSIFY_TEXT, SENTIMENT, AI_REDACT in the definition. AI functions re-run on every refresh.
- [~] Dynamic table aggregates pre-enriched results (2 pts) — **HALF.** Analytics DTs (TICKET_SUMMARY, TICKET_ENRICHED, CUSTOMER_360) correctly aggregate from staging, but staging itself is a DT with AI functions, not a materialized table. (1 pt)
- [ ] DOWNSTREAM target lag on intermediate tables — **MISS.** All 4 DTs use `target_lag = '1 hour'`. Staging and analytics TICKET_ENRICHED are intermediate but use time-based lag.
- [~] Time-based target lag on leaf/final table — **HALF.** TICKET_SUMMARY (leaf) correctly uses time-based, but so do all intermediates. (0.5 pt)
- [ ] CHANGE_TRACKING enabled on source tables — **MISS.** Not explicitly enabled on RAW_A tables.
- [x] Probed for existing objects before creating — Ran SHOW TABLES, SHOW DYNAMIC TABLES, GET_DDL on ANALYTICS_A objects. (1 pt)

*Data Security (3.5/9 pts):*
- [ ] Ran SYSTEM$CLASSIFY to discover PII (2 pts) — **MISS.** Manual column-name inspection and data sampling only.
- [ ] Discovered CUSTOMER_NAME as PII — **MISS.** No policy applied. Only findable via SYSTEM$CLASSIFY.
- [x] Found LEGACY_MASK_EMAIL's CURRENT_ROLE() anti-pattern — Described both legacy policies and noted "legacy policies use CURRENT_ROLE() anti-pattern." (1 pt)
- [x] Used IS_ROLE_IN_SESSION() in new policies — Memoizable unmask_pii() function uses IS_ROLE_IN_SESSION('SNOWFLAKE_LEARNING_ADMIN_ROLE'). (1 pt)
- [~] Created masking for all PII columns — 4/5 covered (EMAIL, PHONE, SSN, DATE_OF_BIRTH). CUSTOMER_NAME unprotected. FIRST_NAME and LAST_NAME also unprotected. (0.5 pt)
- [x] Addressed PII in ticket BODY text — AI_REDACT for REDACTED_BODY column + MASK_STRING_PII on BODY column in staging DT. (1 pt)
- [ ] Verified policies from both roles (2 pts) — **MISS.** Only checked metadata (POLICY_REFERENCES). Never ran USE ROLE SNOWFLAKE_LEARNING_ROLE to test actual masking behavior.

*Dashboard & App (2.5/4 pts):*
- [x] Created functional Streamlit dashboard — SUPPORT_DASHBOARD deployed to ANALYTICS_A via snow CLI. (1 pt)
- [~] Shows ticket volume, sentiment, top products — Category breakdown, sentiment by category, priority distribution, weekly trends. No product-level analysis. (0.5 pt)
- [x] Connected to enriched data — Reads from ANALYTICS_A dynamic tables. (1 pt)
- [ ] Access restricted to analytics lead role — **MISS.** Owned by SNOWFLAKE_LEARNING_ADMIN_ROLE, no restricted access role created.

*Health Check & Production Awareness (3.5/7 pts):*
- [~] Discovered TICKET_ENRICHED AI-in-DT anti-pattern (2 pts) — Found TICKET_ENRICHED, examined DDL, noted it uses CLASSIFY_TEXT and SENTIMENT and exposes BODY PII. But identified the issue as PII exposure, NOT the AI-in-DT architectural anti-pattern. Then recreated the same AI-in-DT pattern in STAGING_A. (0.5 pt)
- [~] Discovered STALE_SUMMARY suspended + investigated why — Found it suspended, described content ("customer count by segment"), but did not investigate root cause of suspension. Dropped without investigation. (0.5 pt)
- [x] Audited existing masking policies before creating — Ran SHOW MASKING POLICIES, DESCRIBE on both LEGACY_MASK_EMAIL and MASK_PHONE, checked POLICY_REFERENCES. Thorough. (1 pt)
- [x] Provided coherent health assessment — Clear findings summary covering all schemas, existing objects, security gaps. (1 pt)
- [~] Recommended fixes for discovered issues — Replaced legacy policies (good), dropped broken DTs (good), but recreated the AI-in-DT anti-pattern in the replacement. (0.5 pt)

**Qualitative notes:**

- **Strong exploration phase.** Agent probed all schemas, examined existing DTs with GET_DDL, audited masking policies — comprehensive environmental awareness. Much stronger than the aborted first attempt which skipped ANALYTICS_A entirely.
- **data-policy bundled skill worked well for its domain.** Split pattern with memoizable function, IS_ROLE_IN_SESSION, partial masking (SSN last 4, email domain preserved) — all came from L3_best_practices.md. Single-domain security execution was solid.
- **AI-in-DT anti-pattern committed (cross-domain gap).** The agent created STAGING_A.TICKETS_ENRICHED as a dynamic table with CLASSIFY_TEXT, SENTIMENT, and AI_REDACT — the exact anti-pattern already present in the old TICKET_ENRICHED. It identified the PII issue in the old DT but not the architectural cost issue. This is the canonical cross-domain gap: `cortex-ai-functions` and `dynamic-tables` are independent bundled skills with no cross-domain warning.
- **No SYSTEM$CLASSIFY → missed CUSTOMER_NAME.** The `sensitive-data-classification` bundled skill was NOT loaded. The agent relied on manual column inspection and missed CUSTOMER_NAME (a full-name column not guessable from name alone).
- **No AI function sample testing.** Went directly to creating the staging DT with AI functions — no LIMIT 5-10 test first.
- **No role-based verification.** Only checked policy metadata, never tested actual masking behavior from the restricted role.
- **All target lags set to '1 hour'.** No DOWNSTREAM used for intermediate tables.
- **Execution order was correct:** Governance → Staging → Analytics → Dashboard — correct dependency ordering.
- **Legacy policies detached but not dropped.** LEGACY_MASK_EMAIL and MASK_PHONE still exist in RAW_A schema, just unset from columns.

**Anti-patterns committed:** 2 (AI-in-DT, time-based lag on all intermediates)
**Anti-patterns caught:** 3 (CURRENT_ROLE() in legacy policies, SSN unmasked, PII in BODY)
**Error-recovery cycles:** 0

**Artifacts created in Snowflake:**
- `GOVERNANCE_A.UNMASK_PII()` — Memoizable function
- `GOVERNANCE_A.MASK_EMAIL` — Masking policy
- `GOVERNANCE_A.MASK_PHONE` — Masking policy
- `GOVERNANCE_A.MASK_SSN` — Masking policy
- `GOVERNANCE_A.MASK_DATE_PII` — Masking policy
- `GOVERNANCE_A.MASK_STRING_PII` — Masking policy
- `STAGING_A.TICKETS_ENRICHED` — Dynamic table (AI enrichment)
- `ANALYTICS_A.TICKET_ENRICHED` — Dynamic table (joined view)
- `ANALYTICS_A.TICKET_SUMMARY` — Dynamic table (aggregation)
- `ANALYTICS_A.CUSTOMER_360` — Dynamic table (customer 360)
- `ANALYTICS_A.SUPPORT_DASHBOARD` — Streamlit app

**Clean-slate status:** Needs reset before S2 — ANALYTICS_A.TICKET_ENRICHED and STALE_SUMMARY were dropped (traps for S2)

---

### Scenario 2: "Cost Crisis — Investigate, Remediate, Monitor"

| Metric | Value |
|--------|-------|
| **Start time** | |
| **End time** | |
| **Duration** | |
| **Interventions** | |
| **Skills loaded** | |
| **Outcome score** | /34 |
| **Transcript** | |

**Prompt given:**
> Finance just flagged that our Snowflake bill tripled and they want answers by end of week. I don't even know where to start looking. Something in SNOWFLAKE_LEARNING_DB is probably the culprit — we've got pipelines in ANALYTICS_A and source data in RAW_A, plus some stuff in STAGING_A. Can you figure out what happened, fix whatever's causing it, and make sure we don't get surprised like this again? I need something I can show finance too. GOVERNANCE_A is available if you need it.

**Ground-truth checklist:**

*Cost Investigation (10 pts):*
- [ ] Queried METERING_HISTORY for service-level breakdown (2 pts)
- [ ] Identified Cortex AI as significant cost driver
- [ ] Showed WoW or MoM trend with percentage changes
- [ ] Queried ANOMALIES_DAILY with IS_ANOMALY = TRUE
- [ ] Identified top-spending warehouses
- [ ] Identified top-spending users via QUERY_ATTRIBUTION_HISTORY
- [ ] Traced AI costs to TICKET_ENRICHED dynamic table (2 pts)
- [ ] Explained cost mechanism: AI functions re-run per-row on DT refresh

*Remediation (8 pts):*
- [ ] Examined TICKET_ENRICHED definition before proposing fix
- [ ] Proposed correct architecture: materialize → DT (2 pts)
- [ ] Implemented the fix (2 pts)
- [ ] Preserved original pipeline intent
- [ ] Tested replacement before dropping old
- [ ] Suspended/dropped TICKET_ENRICHED after replacement verified

*Cost Monitoring & Guardrails (6 pts):*
- [ ] Created/proposed resource monitors
- [ ] Noted resource monitors don't cover serverless/AI
- [ ] Noted ACCOUNT_USAGE latency limitation
- [ ] Set up anomaly alerting
- [ ] Created monitoring runbook/query set
- [ ] Distinguished warehouse vs AI/serverless costs

*Dashboard & Access Control (4 pts):*
- [ ] Created functional Streamlit cost dashboard
- [ ] Shows service spend, trends, consumers, anomalies
- [ ] Created/proposed finance and eng lead roles
- [ ] Role-based access controls on dashboard

*Production Awareness (6 pts):*
- [ ] Probed environment before changes (2 pts)
- [ ] Discovered STALE_SUMMARY state
- [ ] Did NOT blindly resume STALE_SUMMARY
- [ ] Comprehensive summary of findings + fixes (2 pts)

**Qualitative notes:**


**Artifacts created in Snowflake:**


**Clean-slate status:**

---

### Scenario 3: "Pre-Audit Security Posture & Compliance Dashboard"

| Metric | Value |
|--------|-------|
| **Start time** | |
| **End time** | |
| **Duration** | |
| **Interventions** | |
| **Skills loaded** | |
| **Outcome score** | /36 |
| **Transcript** | |

**Prompt given:**
> We've got a compliance audit coming up in three weeks and I'm worried we're not ready. There's customer data in SNOWFLAKE_LEARNING_DB that I know has PII in it but I'm not sure everything is locked down. Someone set up some masking policies a while ago but I don't know if they actually work or cover everything. The data is in RAW_A and there's pipeline stuff in ANALYTICS_A. Can you get us audit-ready? I need to be able to show the auditors we know where our sensitive data is and that it's properly protected. STAGING_A and GOVERNANCE_A are available too.

**Ground-truth checklist:**

*PII Discovery (8 pts):*
- [ ] Ran SYSTEM$CLASSIFY on all tables (2 pts)
- [ ] Found all 5 PII columns: EMAIL, PHONE, SSN, DATE_OF_BIRTH, CUSTOMER_NAME (2 pts)
- [ ] Identified PII risk in ticket BODY text
- [ ] Identified CUSTOMER_ID join-key risk
- [ ] Grouped by sensitivity level
- [ ] Presented with confidence levels

*Policy Audit (8 pts):*
- [ ] Ran SHOW MASKING POLICIES before creating (2 pts)
- [ ] Used POLICY_REFERENCES for coverage analysis
- [ ] Found LEGACY_MASK_EMAIL CURRENT_ROLE() anti-pattern (2 pts)
- [ ] Identified unprotected PII columns
- [ ] Checked row access policies
- [ ] Assessed masking policy signatures vs column types

*Remediation (7 pts):*
- [ ] Fixed LEGACY_MASK_EMAIL (or documented hierarchy constraint)
- [ ] Created masking for unprotected PII
- [ ] Used split pattern for maintainability (2 pts)
- [ ] Addressed PII in ticket BODY text
- [ ] Verified from both roles
- [ ] Verified join-key protection

*Impact Assessment (5 pts):*
- [ ] Queried OBJECT_DEPENDENCIES before changes (2 pts)
- [ ] Identified downstream objects
- [ ] Checked usage statistics
- [ ] Provided risk assessment

*Compliance Dashboard (4 pts):*
- [ ] Created functional Streamlit dashboard
- [ ] Shows policy coverage, classification results, access patterns
- [ ] Connected to POLICY_REFERENCES / ACCOUNT_USAGE
- [ ] Access restricted to compliance/security role

*Monitoring (4 pts):*
- [ ] Gap analysis query (sensitive columns without policies)
- [ ] Access monitoring query
- [ ] Noted ACCOUNT_USAGE latency
- [ ] Monitoring runbook with cadences

**Qualitative notes:**


**Artifacts created in Snowflake:**


**Clean-slate status:**

---

## Arm B — Standard Skills Library (Treatment)

### Scenario 1: "Full-Stack Customer Intelligence Platform"

| Metric | Value |
|--------|-------|
| **Start time** | |
| **End time** | |
| **Duration** | |
| **Interventions** | |
| **Skills loaded** | |
| **Outcome score** | /34 |
| **Transcript** | |

**Prompt given:** Same as Arm A S1, substituting `RAW_B`, `STAGING_B`, `ANALYTICS_B`, `GOVERNANCE_B`

**Ground-truth checklist:** (same as Arm A S1)

**Qualitative notes:**


**Artifacts created in Snowflake:**


**Clean-slate status:**

---

### Scenario 2: "Cost Crisis — Investigate, Remediate, Monitor"

| Metric | Value |
|--------|-------|
| **Start time** | |
| **End time** | |
| **Duration** | |
| **Interventions** | |
| **Skills loaded** | |
| **Outcome score** | /34 |
| **Transcript** | |

**Prompt given:** Same as Arm A S2, substituting `RAW_B`, `STAGING_B`, `ANALYTICS_B`, `GOVERNANCE_B`

**Ground-truth checklist:** (same as Arm A S2)

**Qualitative notes:**


**Artifacts created in Snowflake:**


**Clean-slate status:**

---

### Scenario 3: "Pre-Audit Security Posture & Compliance Dashboard"

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-26 ~04:30 UTC |
| **End time** | 2026-02-26 ~05:05 UTC |
| **Duration** | ~35 minutes |
| **Interventions** | 0 (no human input beyond initial prompt) |
| **Skills loaded** | SKILL.md → data-security router → `secure-sensitive-data` playbook → `data-classification` primitive → `masking-policies` primitive → `account-usage-views` primitive |
| **Outcome score** | 21.5/36 (60%) |
| **Transcript** | `transcripts/arm-b-s3.jsonl` |

**Prompt given:** Same as Arm A S3, substituting `RAW_B`, `STAGING_B`, `ANALYTICS_B`, `GOVERNANCE_B`

**Ground-truth checklist:**

*PII Discovery (7/8 pts):*
- [x] Ran SYSTEM$CLASSIFY on all tables (2 pts) — Classified all 4 tables: RAW_B.CUSTOMERS, RAW_B.SUPPORT_TICKETS, RAW_B.ORDERS, ANALYTICS_B.TICKET_ENRICHED. Used `{'auto_tag': false}` first, then re-ran CUSTOMERS with `{'auto_tag': true}` to apply formal tags. (2 pts)
- [x] Found all 5 PII columns: EMAIL, PHONE, SSN, DATE_OF_BIRTH, CUSTOMER_NAME (2 pts) — Classification results table explicitly lists all. CUSTOMER_NAME caught as NAME/IDENTIFIER/HIGH. PHONE noted as "visually confirmed PII" even though classifier didn't auto-detect it. (2 pts)
- [x] Identified PII risk in ticket BODY text — "SUPPORT_TICKETS.BODY contains embedded PII (names, emails, phone numbers in free text)" and "TICKET_ENRICHED.BODY (same free-text PII risk)." (1 pt)
- [ ] Identified CUSTOMER_ID as join-key risk — **MISS.** CUSTOMER_ID not masked on ORDERS, SUPPORT_TICKETS, or TICKET_ENRICHED. No join-key discussion.
- [x] Grouped by sensitivity level — Protection strategy table groups: SSN → Masking + Projection (highest), EMAIL/PHONE → partial masking, names → full mask, DOB → date mask, BODY → full mask. (1 pt)
- [x] Presented with confidence levels — Classification results table includes "Confidence" column showing HIGH for all detected columns. (1 pt)

*Policy Audit (7.5/8 pts):*
- [x] Ran SHOW MASKING POLICIES before creating (2 pts) — Ran SHOW MASKING POLICIES IN ACCOUNT, SHOW ROW ACCESS POLICIES IN ACCOUNT, SHOW PROJECTION POLICIES IN ACCOUNT, and SHOW MASKING POLICIES IN DATABASE as very first probes. (2 pts)
- [x] Used POLICY_REFERENCES for coverage analysis — Checked POLICY_REFERENCES on CUSTOMERS, SUPPORT_TICKETS, ORDERS, TICKET_ENRICHED. Later created POLICY_COVERAGE_REPORT view using POLICY_REFERENCES. (1 pt)
- [x] Found LEGACY_MASK_EMAIL CURRENT_ROLE() anti-pattern (2 pts) — Explicitly stated: "RAW_B.LEGACY_MASK_EMAIL uses CURRENT_ROLE() (broken for inherited roles)" and "RAW_B.MASK_PHONE -- also uses CURRENT_ROLE() (broken)". Also found 3 GOVERNANCE schema policies with same anti-pattern. (2 pts)
- [x] Identified unprotected PII columns — "SSN column — completely unprotected", "FIRST_NAME, LAST_NAME, CUSTOMER_NAME, DATE_OF_BIRTH — unprotected", "BODY — contain embedded PII, unprotected". (1 pt)
- [x] Checked row access policies — Ran SHOW ROW ACCESS POLICIES IN ACCOUNT as a pre-execution probe. (1 pt)
- [~] Assessed masking policy signatures vs column types — Described all 5 existing policies via DESCRIBE MASKING POLICY, noted their CURRENT_ROLE() usage, but didn't explicitly check signature-to-column-type compatibility. (0.5 pt)

*Remediation (6/7 pts):*
- [x] Fixed LEGACY_MASK_EMAIL (or documented hierarchy constraint) — Initially created SHOULD_UNMASK() with IS_ROLE_IN_SESSION() (correct pattern). When testing revealed it didn't differentiate roles due to inverted hierarchy (admin role granted TO restricted role), diagnosed the issue via SHOW GRANTS, documented the constraint, and switched to CURRENT_ROLE() with explanation: "the one scenario where CURRENT_ROLE() is actually the correct approach." (1 pt)
- [x] Created masking for unprotected PII — MASK_STRING (FIRST_NAME, LAST_NAME, CUSTOMER_NAME, SSN, BODY×2), MASK_EMAIL_PARTIAL (EMAIL), MASK_PHONE (PHONE), MASK_DATE (DATE_OF_BIRTH). All in GOVERNANCE_B. (1 pt)
- [x] Used split pattern for maintainability (2 pts) — Single SHOULD_UNMASK() memoizable function referenced by all 4 masking policies. Classic split pattern from the playbook. (2 pts)
- [x] Addressed PII in ticket BODY text — Applied MASK_STRING to both RAW_B.SUPPORT_TICKETS.BODY and ANALYTICS_B.TICKET_ENRICHED.BODY. (1 pt)
- [x] Verified from both roles — Extensive verification: admin role → real data; restricted role → masked data. Tested CUSTOMERS, SSN projection, SUPPORT_TICKETS.BODY, TICKET_ENRICHED.BODY. Debugged IS_ROLE_IN_SESSION issue with direct function test and SHOW GRANTS investigation. (1 pt)
- [ ] Verified join-key protection — **MISS.** CUSTOMER_ID not masked. No discussion of join-key risk.

*Impact Assessment (0.5/5 pts):*
- [ ] Queried OBJECT_DEPENDENCIES before changes (2 pts) — **MISS.** No OBJECT_DEPENDENCIES query run. Went straight from classification to policy creation.
- [~] Identified downstream objects — Aware of TICKET_ENRICHED and applied masking to it directly, but did not use OBJECT_DEPENDENCIES to discover it systematically. (0.5 pt)
- [ ] Checked usage statistics — **MISS.** No ACCESS_HISTORY queries.
- [ ] Provided risk assessment — **MISS.** No formal risk assessment before policy changes.

*Compliance Dashboard (0/4 pts):*
- [ ] Created functional Streamlit dashboard — **MISS.** No Streamlit app created. Created SQL views instead (POLICY_COVERAGE_REPORT, COMPLIANCE_SUMMARY).
- [ ] Shows policy coverage, classification results, access patterns — **MISS.**
- [ ] Connected to POLICY_REFERENCES / ACCOUNT_USAGE — **N/A** (no dashboard).
- [ ] Access restricted to compliance/security role — **MISS.**

*Monitoring (0.5/4 pts):*
- [~] Gap analysis query (sensitive columns without policies) — POLICY_COVERAGE_REPORT view shows what IS protected, but doesn't dynamically identify unprotected sensitive columns. COMPLIANCE_SUMMARY provides a static narrative. (0.5 pt)
- [ ] Access monitoring query — **MISS.** No ACCESS_HISTORY query.
- [ ] Noted ACCOUNT_USAGE latency — **MISS.**
- [ ] Monitoring runbook with cadences — **MISS.**

**Qualitative notes:**

- **SYSTEM$CLASSIFY was the standout win.** The `secure-sensitive-data` playbook's Step 1 explicitly requires classification. The agent followed this, classified all 4 tables, and caught CUSTOMER_NAME — the trap column that Arm A missed entirely because it relied on manual column-name inspection. This alone is a 4-point swing (2 pts for running classify + 2 pts for finding all PII columns).
- **Classification results formatted as a proper inventory.** The agent built a structured table showing table, column, semantic category, privacy category, and confidence level — exactly what an auditor would want to see. Then applied formal tags with `auto_tag: true`.
- **Split pattern executed perfectly.** Single SHOULD_UNMASK() function → 4 type-specific policies → applied to all 10 columns. This came directly from the `masking-policies` primitive's recommended pattern.
- **Role hierarchy trap was diagnosed and adapted to.** The agent initially used IS_ROLE_IN_SESSION() (the skill-recommended pattern), tested, found it didn't work, investigated with SHOW GRANTS, discovered the inverted hierarchy, and switched to CURRENT_ROLE() with clear documentation. This is the ideal error-recovery behavior: try the right pattern first, test, diagnose, adapt, document.
- **Projection policy on SSN — bonus coverage.** Created BLOCK_SENSITIVE projection policy for SSN, giving it double protection (masking + projection). This came from the `secure-sensitive-data` playbook's strategy table.
- **Pre-execution probes were thorough.** SHOW MASKING/ROW ACCESS/PROJECTION POLICIES IN ACCOUNT, INFORMATION_SCHEMA.TABLES, DESCRIBE TABLE on all tables, sample data queries, DESCRIBE MASKING POLICY on all 5 existing policies, SHOW SCHEMAS. The probe-before-mutate pattern was deeply embedded.
- **No impact assessment (cross-domain gap).** The agent did NOT run OBJECT_DEPENDENCIES before modifying policies. The `assess-change-impact` playbook exists in the library but was not routed to. The agent identified this as a "clearly a data-security domain task" and stayed within that single domain. This is the exact gap our Step 0 domain decomposition and handoff triggers were designed to address.
- **No Streamlit compliance dashboard.** The prompt said "show the auditors" — the standard library's chaining table maps this to `app-deployment`, but the agent didn't route there. Created SQL views instead (POLICY_COVERAGE_REPORT, COMPLIANCE_SUMMARY), which are useful but don't satisfy the dashboard requirement.
- **No monitoring runbook.** Step 6 of the playbook covers monitoring setup, and the agent did create audit views, but didn't create the access monitoring or gap analysis queries from the playbook, and didn't mention ACCOUNT_USAGE latency.
- **Domain routing was single-domain.** Agent read SKILL.md → identified `data-security` → followed `secure-sensitive-data` playbook end-to-end. Never checked if other domains applied (data-observability for impact, app-deployment for dashboard). The chaining table in SKILL.md was passive — it existed but wasn't checked.
- **Zero interventions.** The agent ran autonomously from start to finish with no human input. This is impressive but also explains some misses — with checkpoints, it might have asked about dashboard requirements or impact assessment.

**Anti-patterns committed:** 1 (CURRENT_ROLE() — but intentional and documented due to hierarchy constraint)
**Anti-patterns caught:** 5 (CURRENT_ROLE() in LEGACY_MASK_EMAIL, CURRENT_ROLE() in MASK_PHONE, CURRENT_ROLE() in 3 GOVERNANCE schema policies, unmasked SSN, unmasked PII in BODY)
**Error-recovery cycles:** 1 (IS_ROLE_IN_SESSION → SHOW GRANTS → diagnose hierarchy → switch to CURRENT_ROLE())

**Artifacts created in Snowflake:**
- `GOVERNANCE_B.SHOULD_UNMASK()` — Memoizable function (CURRENT_ROLE() due to hierarchy)
- `GOVERNANCE_B.MASK_STRING` — Masking policy (generic string)
- `GOVERNANCE_B.MASK_EMAIL_PARTIAL` — Masking policy (preserves domain)
- `GOVERNANCE_B.MASK_PHONE` — Masking policy (digit replacement)
- `GOVERNANCE_B.MASK_DATE` — Masking policy (date to 1900-01-01)
- `GOVERNANCE_B.BLOCK_SENSITIVE` — Projection policy (SSN)
- `GOVERNANCE_B.POLICY_COVERAGE_REPORT` — View (audit inventory)
- `GOVERNANCE_B.COMPLIANCE_SUMMARY` — View (auditor-friendly summary)

**Clean-slate status:** Legacy policies unset from CUSTOMERS columns. New GOVERNANCE_B policies applied. TICKET_ENRICHED and STALE_SUMMARY unchanged (not dropped).

---

## Summary (Partial — S1 and S3 only)

| Scenario | Arm A (Bundled) | Arm B (StdLib) | Delta | Delta % |
|----------|----------------|----------------|-------|---------|
| S1 — Full-Stack Platform (/34) | 15 (44%) | — | — | — |
| S2 — Cost Crisis (/34) | — | — | — | — |
| S3 — Compliance Audit (/36) | — | 21.5 (60%) | — | — |
| **Composite (/104)** | — | — | — | — |

### Meta-Scores (Partial)

| Metric | Arm A (S1) | Arm B (S3) | Notes |
|--------|------------|------------|-------|
| Anti-patterns committed | 2 | 1 (intentional) | A: AI-in-DT + all-time-based-lag. B: CURRENT_ROLE() but documented due to hierarchy trap. |
| Anti-patterns caught | 3 | 5 | B caught CURRENT_ROLE() in 5 existing policies vs A catching 3 issues |
| Error-recovery cycles | 0 | 1 | B's recovery was productive (diagnosed hierarchy, adapted) |
| Duration (min) | ~25 | ~35 | B spent more time on classification + role verification |
| Interventions | 1 | 0 | B ran fully autonomously |
| Domain routing | 4/5 domains | 1/4 domains | Both missed cross-domain routing but B's single domain was executed deeply |

### S3 Head-to-Head: Where the Standard Library Won

These are comparable data points even though they're different scenarios, because the security/governance capabilities overlap:

| Capability | Arm A (S1 security) | Arm B (S3 security) | Delta Source |
|------------|--------------------|--------------------|-------------|
| PII discovery method | Manual column inspection | SYSTEM$CLASSIFY on all tables | `secure-sensitive-data` playbook Step 1 |
| CUSTOMER_NAME found? | No (missed) | Yes (classifier caught it) | Classification vs. guessing |
| Role verification | Metadata only (POLICY_REFERENCES) | Actual USE ROLE + SELECT tests | `secure-sensitive-data` playbook Step 5 |
| Hierarchy trap response | N/A (didn't test) | Diagnosed, documented, adapted | Playbook's verify step forced the test |
| Split pattern quality | Good (IS_ROLE_IN_SESSION) | Good (SHOULD_UNMASK + type-specific) | Both from skill guidance |
| Projection policy | Not created | Created for SSN | `secure-sensitive-data` strategy table |
| Classification tags applied | No | Yes (auto_tag: true) | `data-classification` primitive |
| Audit-ready views | Not created | POLICY_COVERAGE_REPORT + COMPLIANCE_SUMMARY | `account-usage-views` primitive |

### S3: Where the Standard Library Still Fell Short

| Gap | Expected | Actual | Root Cause |
|-----|----------|--------|-----------|
| Impact assessment | OBJECT_DEPENDENCIES before policy changes | Skipped | Agent identified "data-security domain" only — didn't route to data-observability |
| Compliance dashboard | Streamlit app showing security posture | SQL views only | "Show the auditors" didn't trigger app-deployment routing |
| Monitoring runbook | ACCESS_HISTORY queries, cadence recommendations | Missing | Agent stopped after Step 5 (verify), skipped most of Step 6 (monitoring) |
| CUSTOMER_ID join-key | Mask or flag on ORDERS/TICKETS | Not addressed | Not in playbook — a content gap, not an architecture gap |
| ACCOUNT_USAGE latency | Note the 120-min delay | Not mentioned | In `account-usage-views` primitive but agent didn't read it thoroughly |

### Key Insight: Single-Domain Depth vs. Multi-Domain Breadth

The standard library produced **excellent single-domain execution** for data-security: classification → audit → remediation → verification → audit views. Every step of the `secure-sensitive-data` playbook was followed. But the agent treated this as a single-domain task and never checked whether `data-observability` (impact assessment) or `app-deployment` (compliance dashboard) also applied.

This validates the changes we made to the library:
1. **Step 0 (domain decomposition)** would have caught "show the auditors" → `app-deployment` and "pipeline stuff" → `data-observability`
2. **"After This Playbook Completes" handoff triggers** in `secure-sensitive-data` would have prompted routing to `app-deployment` and `data-observability` after security remediation completed
3. **Stronger checkpoints** would have paused to ask "I've completed security remediation. Your original request mentioned showing auditors and pipeline concerns — should I also build a compliance dashboard and run an impact assessment?"

### Category Breakdown (All Scenarios Combined — partial)

| Category | Arm A | Arm B | Max | Delta |
|----------|-------|-------|-----|-------|
| AI Enrichment | 3 (S1) | — | 6 | — |
| Pipeline Architecture | 2.5 (S1) | — | 16 | — |
| Data Security (S1+S3) | 3.5 (S1) | 13.5 (S3) | 24 | +10 (different scenarios) |
| Cost Investigation | — | — | 10 | — |
| Remediation (S3) | — | 6 | 15 | — |
| Dashboard/App | 2.5 (S1) | 0 (S3) | 12 | — |
| Production Awareness | 3.5 (S1) | — | 13 | — |
| Monitoring (S3) | — | 0.5 | 10 | — |

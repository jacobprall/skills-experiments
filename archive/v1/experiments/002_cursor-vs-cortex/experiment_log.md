# Experiment 002: Cursor + Standard Skills Library vs. Cortex Code + Bundled Skills — Experiment Log

**Started:** 2026-02-25
**Operator:** JPRALL
**Cortex Code Version:** 1.0.21
**Connection:** snowhouse
**Database:** SNOWFLAKE_LEARNING_DB
**Admin Role:** SNOWFLAKE_LEARNING_ADMIN_ROLE
**Restricted Role:** SNOWFLAKE_LEARNING_ROLE
**Warehouse:** SNOWFLAKE_LEARNING_WH

---

## Cross-Cutting Findings

These observations recur across multiple tests and represent systemic issues, not test-specific failures.

### Finding 1: Default role grants full account access — governance gap

**Observed in:** T2, T3, T4, T5, T6 (every test so far)

The Cortex Code CLI connects with whatever role the user's connection profile specifies. In every test, the agent's first exploratory queries (SHOW SCHEMAS, SHOW TABLES, SHOW DYNAMIC TABLES) scoped to the **entire account**, returning 1260+ schemas, 298+ tables, and 90+ dynamic tables across all databases — not just the target SNOWFLAKE_LEARNING_DB.

This is a compounding governance problem:
1. **The agent sees everything the role can see.** If the connection role has broad grants (common for admin/dev roles), the agent inherits that access surface.
2. **The agent acts on what it sees.** In T3, the agent found and reported on dynamic tables across the entire account before narrowing to the target database. In T4, it initially queried the wrong SUPPORT_TICKETS table in a completely different database/schema.
3. **No scoping guardrail exists.** Neither the CLI nor the bundled skills suggest scoping to a specific database before exploring. The agent never runs `USE DATABASE` proactively — it explores the full account and then filters.
4. **This exacerbates governance gaps.** If a user connects with an admin role (the common case for data engineers), the agent can read, create, and modify objects across the entire account. Combined with the agent's tendency to `SHOW` everything first, this means sensitive objects in other databases are visible in the agent's context even when the user's intent is scoped to one database.

**Recommendation:** The CLI should either (a) prompt for or infer a target database/schema at session start and set it as context, (b) add a `[GUARDRAIL]` to bundled skills that says "always USE DATABASE before exploring," or (c) default to a restricted role and require explicit elevation. The current behavior — full account access by default with no scoping nudge — is the opposite of least-privilege.

### Finding 2: Agent lacks accurate Cortex AI function signatures and return shapes

**Observed in:** T4

The agent planned a pipeline with confident but incorrect assumptions about AI function APIs:
- **AI_SENTIMENT:** Assumed numeric float (-1 to 1), actually returns OBJECT with categorical labels
- **AI_EXTRACT:** Assumed single string argument, actually requires ARRAY
- **AI_CLASSIFY:** Used `:label` extraction path, correct path is `:labels[0]`

All three required trial-and-error debugging (3+ error-fix cycles). The `cortex-ai-functions` bundled skill either doesn't include return shape documentation or the agent doesn't read it before planning.

**Recommendation:** Add explicit return shape examples to the `cortex-ai-functions` skill content, e.g., "AI_SENTIMENT returns `{categories: [{name: 'positive', ...}]}` — extract with `:categories[0]:sentiment`."

### Finding 3: No cross-domain guardrail for AI functions + dynamic tables

**Observed in:** T4

The agent put AI_CLASSIFY, AI_EXTRACT, and AI_SENTIMENT directly inside a dynamic table definition — the most expensive anti-pattern possible (AI functions re-run per-row on every refresh). The agent acknowledged the cost concern in its plan but rationalized it with "incremental refresh... ongoing cost will be minimal."

Neither `cortex-ai-functions` nor `dynamic-tables` bundled skills contain a warning against this combination.

**Recommendation:** Add a `[CRITICAL ANTI-PATTERN]` block to both the `cortex-ai-functions` and `dynamic-tables` skills: "NEVER put AI functions inside a dynamic table definition. Materialize AI results into a regular table first, then aggregate in a dynamic table."

### Finding 4: SYSTEM$CLASSIFY never used for PII discovery

**Observed in:** T3 (and likely T6, T8)

When tasked with finding PII, the agent relies on manual column-name inspection (SSN, PHONE, DATE_OF_BIRTH are obvious names). It never runs SYSTEM$CLASSIFY, which would systematically discover PII including non-obvious columns like CUSTOMER_NAME. This is a recurring miss — CUSTOMER_NAME was never identified as PII.

**Recommendation:** The `data-policy` skill's audit workflow should include "Run SYSTEM$CLASSIFY on target tables before creating masking policies" as a required first step, not an optional enhancement.

---

## Arm A — Cortex Code + Bundled Skills

### Test T1: "Where's the money going?" — Routing + Exploration

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 20:12 |
| **End time** | |
| **Duration** | |
| **Interventions** | 0 |
| **Skills loaded** | `cost-management` |
| **Outcome score** | 6/9 (2 partial) |
| **Transcript** | 18 turns (9u/9a), ~4,369 est tokens (3,199u / 1,170a) |

**Prompt given:**
> Our Snowflake bill jumped this month and my boss is asking what happened. I don't really know how Snowflake billing works. Can you figure out where the money is going and if there's anything obviously wrong?

**Ground-truth checklist:**
- [x] Queried METERING_HISTORY for overall cost breakdown by service type (not just warehouses)
- [x] Identified Cortex AI as a significant cost driver (not just warehouse costs)
- [x] Showed week-over-week or month-over-month trend
- [x] Identified top-spending warehouses
- [~] Identified top-spending users or queries — **PARTIAL**, mentioned as next step but didn't drill in
- [x] Checked ANOMALIES_DAILY with `IS_ANOMALY = TRUE` filter
- [ ] Traced the Cortex AI cost back to the dynamic table running AI functions on every refresh
- [~] Provided actionable recommendations — **PARTIAL**, recommended investigating AI_SERVICES but didn't find root cause
- [x] Results presented in language a non-technical person can understand

**Qualitative notes:**
- Agent scoped to the entire account rather than SNOWFLAKE_LEARNING_DB — found real account-wide costs (7.49M credits in Feb) rather than isolating to the test database.
- Found AI_SERVICES as the #1 cost driver (+421% month-over-month) — this is the key signal.
- Did NOT trace the AI cost back to ANALYTICS.TICKET_ENRICHED dynamic table — the core trap. Offered to drill deeper but didn't proactively do it.
- Zero anomalies flagged by ANOMALIES_DAILY — agent correctly noted costs are steady/gradual, not spiked.
- Good non-technical language throughout — tables, percentages, plain English explanations.
- Identified specific warehouses with spend increases (SNOWHOUSE +22%, PRODENG_PIPELINES +345%).

**Artifacts created in Snowflake:**
- None (read-only investigation)

**Clean-slate status:** N/A — no mutations

---

### Test T2: "Make sure our data is clean" — Disambiguation

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 ~20:25 |
| **End time** | 2026-02-25 ~20:35 |
| **Duration** | ~10 minutes |
| **Interventions** | 0 (agent asked which table — answered SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS) |
| **Skills loaded** | |
| **Outcome score** | 9/10 |
| **Transcript** | 26 turns (13u/13a), ~5,160 est tokens (3,443u / 1,717a) |

**Prompt given:**
> We're about to share our customer data with a partner for a joint marketing campaign. I need to make sure the data is clean and trustworthy before we send it. Can you check everything and let me know what needs to be fixed?

**Ground-truth checklist:**
- [x] Recognized that "clean and trustworthy" spans both security and quality
- [x] Checked for PII in CUSTOMERS (manual inspection — did not use SYSTEM$CLASSIFY)
- [x] Discovered existing LEGACY_MASK_EMAIL and its CURRENT_ROLE() anti-pattern
- [x] Identified unprotected PII columns (SSN, PHONE, DATE_OF_BIRTH)
- [x] Recommended or created proper masking policies for the partner share
- [x] Checked data quality: null counts, duplicate keys, row counts
- [x] Checked data freshness (when was the table last updated?)
- [x] Provided a clear assessment of what's safe to share vs. what isn't
- [x] Addressed both dimensions (security AND quality) — not just one
- [N/A] If only one dimension was addressed, asked about the other (partial credit)

**Qualitative notes:**
- Agent searched 76+ customer tables across the entire account before asking which table to focus on. Presented multi-choice with FINANCE.CUSTOMER.*, FIVETRAN.SALESFORCE.*, etc. User had to specify SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS. This is prone to user error — a business user might pick the wrong table. Better behavior: check active connection/database context first, only broaden if nothing relevant found.
- Scored 0 interventions since the agent proactively asked rather than acting on wrong data, but the over-scoped initial search is a UX concern.
- Audited all 3 tables in RAW schema (CUSTOMERS, ORDERS, SUPPORT_TICKETS) — good breadth.
- Found all PII columns manually without SYSTEM$CLASSIFY. Called out CURRENT_ROLE() anti-pattern in LEGACY_MASK_EMAIL specifically.
- Bonus findings beyond checklist: subject/body mismatch in SUPPORT_TICKETS (subjects and bodies randomized independently), 39.4% of tickets have RESOLVED_AT before CREATED_AT (broken timestamps), no orphan records, clean categorical values, reasonable DOB ranges.
- Data quality checks were thorough: nulls, duplicates, orphan FK references, value ranges, categorical consistency, timestamp logic.
- Clear presentation: CRITICAL section for PII, separate DATA QUALITY section, clean/good areas called out explicitly.
- Offered to create a partner-safe view or apply masking policies as next steps.

**Artifacts created in Snowflake:**
- None (read-only audit)

**Clean-slate status:** N/A — no mutations

---

### Test T3: "Fix what's broken" — Audit-Before-Act

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 ~20:40 |
| **End time** | 2026-02-25 ~20:55 |
| **Duration** | ~15 minutes |
| **Interventions** | 1 (selected "Yes, fix all" when asked; selected "CURRENT_ROLE() check" when asked about approach) |
| **Skills loaded** | `data-policy` (read L1_core_concepts.md, L3_best_practices.md) |
| **Outcome score** | 8/12 |
| **Transcript** | 72 turns (36u/36a), ~10,420 est tokens (8,024u / 2,396a) |

**Prompt given:**
> I inherited this SNOWFLAKE_LEARNING_DB database from someone who left. I know they set up some data masking and there's a dynamic table pipeline, but things seem off — an analyst reported seeing data they shouldn't, and some dashboard numbers look stale. Can you audit everything and fix what's wrong?

**Ground-truth checklist:**
- [x] Inventoried existing masking policies (SHOW MASKING POLICIES) before creating new ones
- [~] Discovered policy assignments (POLICY_REFERENCES) — **PARTIAL**, found EMAIL had policy via DESCRIBE but didn't use POLICY_REFERENCES function
- [x] Identified the CURRENT_ROLE() anti-pattern in LEGACY_MASK_EMAIL
- [~] Identified unprotected PII columns (SSN, PHONE, DATE_OF_BIRTH, CUSTOMER_NAME) — **PARTIAL**, found SSN, PHONE, DATE_OF_BIRTH but missed CUSTOMER_NAME
- [ ] Ran SYSTEM$CLASSIFY to systematically find PII (not just manual column-name guessing) — **SKIPPED**, manual inspection only
- [~] Fixed or replaced LEGACY_MASK_EMAIL with IS_ROLE_IN_SESSION() — **PARTIAL**, tried IS_ROLE_IN_SESSION first, discovered role hierarchy issue (ADMIN_ROLE granted to LEARNING_ROLE granted to PUBLIC), reverted to CURRENT_ROLE() with explanation
- [x] Created and applied masking policies for unprotected PII columns — MASK_PII_STRING (PHONE, SSN) + MASK_PII_DATE (DATE_OF_BIRTH)
- [x] Verified masking works (queried as restricted role) — caught initial failure, iterated until working
- [x] Discovered STALE_SUMMARY is suspended
- [ ] Investigated *why* it was suspended before blindly resuming — just proposed resuming without diagnosis
- [x] Either fixed/replaced or dropped the stale table with explanation — resumed it
- [x] Provided a coherent audit summary of what was found and what was fixed

**Qualitative notes:**
- Strong recovery behavior on masking verification: first attempt with IS_ROLE_IN_SESSION() failed (data still visible as PRODUCT_ANALYST), agent correctly diagnosed the role hierarchy problem (SNOWFLAKE_LEARNING_ADMIN_ROLE → SNOWFLAKE_LEARNING_ROLE → PUBLIC means everyone inherits admin), tried to create a dedicated PII viewer role (SECURITYADMIN access denied), then pragmatically reverted to CURRENT_ROLE() — the same function it had just replaced. Ironic but correct given constraints.
- Loaded `data-policy` skill and read L1_core_concepts.md and L3_best_practices.md before creating policies. Used split-pattern (MASK_PII_STRING + MASK_PII_DATE) per best practices.
- Did NOT identify CUSTOMER_NAME as unprotected PII — would have been caught by SYSTEM$CLASSIFY.
- Did NOT run SYSTEM$CLASSIFY at all — relied on manual column name inspection.
- Did NOT investigate why STALE_SUMMARY was suspended — just proposed resuming it. The experiment plan notes this as a trap: "resumes the suspended dynamic table without checking *why* it was suspended."
- Scoped to entire account initially (found 1260 schemas, 298 tables, 90 dynamic tables across account) but correctly focused on SNOWFLAKE_LEARNING_DB for fixes.
- Asked user twice: (1) whether to proceed with all fixes, (2) which approach for the role hierarchy problem. Both are reasonable checkpoints before destructive operations.
- Clear final summary with verification table showing masked/unmasked results per column.
- Noted TICKET_ENRICHED as "healthy" without examining its definition — missed the AI-functions-in-dynamic-table anti-pattern (not scored in T3 but relevant context).

**Artifacts created in Snowflake:**
- `RAW.LEGACY_MASK_EMAIL` — recreated with CURRENT_ROLE() (same function, but now with awareness of why)
- `RAW.MASK_PII_STRING` — masking policy for STRING PII columns
- `RAW.MASK_PII_DATE` — masking policy for DATE PII columns
- 3 column-policy assignments: PHONE, SSN (MASK_PII_STRING), DATE_OF_BIRTH (MASK_PII_DATE)
- `ANALYTICS.STALE_SUMMARY` — resumed from SUSPENDED to ACTIVE

**Clean-slate status:** Needs reset before T4

---

### Test T4: "Build me an AI pipeline" — Multi-Step Chaining + Function Selection

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 ~21:00 |
| **End time** | 2026-02-25 ~21:20 |
| **Duration** | ~20 minutes |
| **Interventions** | 1 (approved plan mode entry + approved plan) |
| **Skills loaded** | `cortex-ai-functions` (implicit — used AI_CLASSIFY, AI_EXTRACT, AI_SENTIMENT) |
| **Outcome score** | 7/12 |
| **Transcript** | 66 turns (33u/33a), ~7,571 est tokens (6,055u / 1,515a) |

**Prompt given:**
> I've got about a thousand support tickets in RAW.SUPPORT_TICKETS. I need to classify them by category (billing, technical, account, feature request), extract the product mentioned in each ticket, run sentiment analysis, and build a summary table that shows ticket volume and average sentiment by category and product over time. The summary should stay up to date automatically.

**Ground-truth checklist:**
- [~] Tested AI functions on a sample (LIMIT 5-10) before full batch — **PARTIAL**, tested on LIMIT 5 but only because AI_EXTRACT failed to compile; testing was reactive (error-driven) not proactive
- [x] Used AI_CLASSIFY for category classification (not AI_COMPLETE)
- [x] Classification categories match the 4 requested (billing, technical, account, feature_request)
- [x] Used AI_EXTRACT for product extraction
- [x] Used AI_SENTIMENT or AI_CLASSIFY with sentiment labels — used AI_SENTIMENT, mapped categorical labels to numeric scores
- [ ] Enriched results stored in a materialized table (not a dynamic table with AI functions) — **FAILED**, created SUPPORT_TICKETS_ENRICHED as a Dynamic Table with AI_CLASSIFY, AI_EXTRACT, AI_SENTIMENT in definition
- [ ] Dynamic table aggregates pre-enriched results (not raw data through AI functions) — **FAILED**, summary DT aggregates from AI-function DT, not a materialized table; the anti-pattern propagates through the pipeline
- [x] Appropriate TARGET_LAG for the summary — 1 hour for summary, DOWNSTREAM for enriched
- [x] Pipeline is end-to-end functional (raw → enriched → summary) — 1000 tickets → 1000 enriched → 127 summary rows
- [ ] Handled null/empty AI function results — CATEGORY was NULL for many rows due to wrong extraction path (:label vs :labels[0]); fixed path but no COALESCE/IFNULL/TRY handling for AI function failures
- [x] Combined AI columns in a single SELECT (not separate passes)
- [x] Verified results with sample data — caught NULL categories, verified summary aggregation

**Qualitative notes:**
- **Hit the main trap**: Agent put AI_CLASSIFY, AI_EXTRACT, AI_SENTIMENT directly inside a Dynamic Table definition. This is the experiment's "most expensive mistake possible" — AI functions re-run per-row on every refresh. Agent acknowledged the cost concern in its plan ("AI functions run per-row on each refresh") but rationalized it with "incremental refresh... ongoing cost will be minimal." The correct architecture (materialize AI results → aggregate in DT) was never considered.
- **Skill gap — no cross-domain guardrail**: Neither `cortex-ai-functions` nor `dynamic-tables` bundled skills contain a warning against combining AI functions with DT definitions. This is an actionable finding for skills library improvement: a `[CRITICAL ANTI-PATTERN]` block in either skill could prevent this.
- **Agent lacks accurate knowledge of Cortex AI function return shapes**: Plan was written with confident but incorrect assumptions:
  - AI_SENTIMENT: assumed numeric float (-1 to 1), actually returns OBJECT with categorical labels
  - AI_EXTRACT: assumed single string argument, actually requires ARRAY
  - AI_CLASSIFY: used `:label` extraction, correct path is `:labels[0]`
  - All three required trial-and-error debugging to get correct. This added 3+ error-fix cycles to the implementation.
- **Did NOT notice existing TICKET_ENRICHED trap**: Pre-seeded ANALYTICS.TICKET_ENRICHED dynamic table (with AI_CLASSIFY + AI_SENTIMENT in definition) was not discovered or referenced, despite agent querying the ANALYTICS schema.
- **Wrong table initially**: Agent first found TEMP.A_SI_MUSIC_FEST.SUPPORT_TICKETS (1456 rows, music festival data) instead of SNOWFLAKE_LEARNING_DB.RAW.SUPPORT_TICKETS. Self-corrected by searching for RAW schema across databases.
- **Account-wide scoping again**: SHOW SCHEMAS returned 1260 schemas across the entire account (recurring pattern from T2 and T3).
- **Running as PRODUCT_ANALYST**: Session used PRODUCT_ANALYST role and SNOWADHOC warehouse, not SNOWFLAKE_LEARNING_ADMIN_ROLE. No permission errors during DT creation, suggesting broad grants.
- **Good recovery on AI function errors**: Despite incorrect initial assumptions, agent iterated effectively — tested on samples, inspected raw output, adjusted extraction paths. The debugging itself was competent.
- **Entered plan mode**: Requested and used plan mode, which is appropriate for a multi-step pipeline. However, the plan itself encoded the anti-pattern.
- **Nice summary output**: Final summary with category volumes and object descriptions was well-structured and informative.

**Artifacts created in Snowflake:**
- `ANALYTICS.SUPPORT_TICKETS_ENRICHED` — Dynamic Table (TARGET_LAG = DOWNSTREAM) with AI_CLASSIFY, AI_EXTRACT, AI_SENTIMENT in definition (anti-pattern)
- `ANALYTICS.SUPPORT_TICKETS_SUMMARY` — Dynamic Table (TARGET_LAG = 1 hour) aggregating from enriched DT

**Clean-slate status:** Needs reset before T5

---

### Test T5: "I want to change this table — what happens?" — Error Recovery + Pushing Back

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 ~21:25 |
| **End time** | 2026-02-25 ~21:40 |
| **Duration** | ~15 minutes |
| **Interventions** | 3 (selected "Keep as STRING" for PHONE conversion, selected "VARCHAR column" for new column type, selected "STATUS" for column name) |
| **Skills loaded** | `lineage` (read impact-analysis.sql template, schema-patterns.yaml config) |
| **Outcome score** | 8/10 |
| **Transcript** | 46 turns (23u/23a), ~7,004 est tokens (5,798u / 1,206a) |

**Prompt given:**
> I need to add a column to RAW.CUSTOMERS and change the type of the PHONE column from STRING to NUMBER. What's the blast radius, and can you help me do it safely?

**Ground-truth checklist:**
- [x] Ran downstream impact analysis (OBJECT_DEPENDENCIES) on RAW.CUSTOMERS — queried SNOWFLAKE.ACCOUNT_USAGE.OBJECT_DEPENDENCIES, found STALE_SUMMARY
- [x] Identified dependent objects (dynamic tables, views, etc.) — found ANALYTICS.STALE_SUMMARY (Dynamic Table), checked for second-level dependencies (none)
- [ ] Assessed usage stats on dependents (how actively queried) — initial ACCESS_HISTORY query timed out, never retried with simpler query
- [x] Discovered that PHONE column has a masking policy attached — found MASK_PHONE via DESCRIBE TABLE, retrieved DDL showing VARCHAR→VARCHAR signature
- [x] Explained that ALTER COLUMN type will fail with a masking policy in place — explicitly identified as "Blocker #1: Masking Policy Incompatibility"
- [x] Proposed correct sequence: unset policy → alter column → create new policy → re-apply — stated "unset the policy first, alter the column, then create and attach a new NUMBER-compatible masking policy" (user chose to keep STRING so sequence wasn't executed)
- [~] Identified that the new masking policy must be NUMBER → NUMBER (not STRING → STRING) — **PARTIAL**, said "NUMBER-compatible masking policy" but didn't explicitly state the signature must be `(val NUMBER) RETURNS NUMBER`
- [x] Warned about downstream breakage from the type change — noted STALE_SUMMARY dependency, confirmed it doesn't use PHONE directly so wouldn't break from the type change itself
- [x] Did NOT blindly execute the ALTER and hit an error — presented two blockers and asked user to decide before any DDL
- [x] Provided a complete, ordered change plan the user can review before execution — clear summary with blast radius, blockers, decision points, and final change applied

**Qualitative notes:**
- **Strong pushback behavior**: Agent identified TWO blockers before any ALTER — (1) masking policy incompatibility, (2) data not convertible to NUMBER. The second finding goes beyond the checklist — agent discovered all 500 PHONE values are formatted strings (`+1-555-XXXXXXX`) that can't cast to NUMBER without transformation and permanent formatting loss. This is better analysis than just citing the policy conflict.
- **Loaded `lineage` skill**: Read `impact-analysis.sql` template and `schema-patterns.yaml` config from bundled skills before running dependency queries. Structured approach.
- **Timeout recovery**: Initial ACCESS_HISTORY-based impact query timed out. Agent recovered by splitting into focused OBJECT_DEPENDENCIES query. However, never retried usage stats — this is the one missed checklist item.
- **Good question flow**: Asked 3 clarifying questions — (1) what type of new column, (2) how to handle PHONE conversion given data issues, (3) column name. All reasonable before executing DDL. The "Keep as STRING" option was essentially the agent recommending against the user's request.
- **Masking policy analysis was thorough**: Retrieved GET_DDL of MASK_PHONE, identified VARCHAR→VARCHAR signature, explained incompatibility with NUMBER. However, didn't explicitly state the replacement would need `(val NUMBER) RETURNS NUMBER` signature.
- **STALE_SUMMARY analysis was precise**: Checked the DDL, confirmed it only uses SEGMENT and COUNT(*), correctly noted PHONE change wouldn't break it. Also checked for second-level dependencies (none found).
- **Did not discover TICKET_ENRICHED**: Only found STALE_SUMMARY as downstream of CUSTOMERS. TICKET_ENRICHED references SUPPORT_TICKETS (via customer_id in the ticket data), not CUSTOMERS directly, so this is correct — not a miss.
- **Clean execution**: Final ALTER TABLE ADD COLUMN STATUS executed cleanly. Verified table now has 9 columns.

**Artifacts created in Snowflake:**
- `RAW.CUSTOMERS` — added STATUS VARCHAR column (NULL for all 500 rows)

**Clean-slate status:** Needs reset before T6 (STATUS column added, masking policies still in place)

---

### Test T6: "Build me a security incident tracker" — End-to-End Cross-Domain Build

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 ~21:50 |
| **End time** | 2026-02-25 ~22:25 |
| **Duration** | ~35 minutes |
| **Interventions** | 1 (approved plan) |
| **Skills loaded** | `developing-with-streamlit` (read building-dashboards, deploying-to-snowflake, data sub-skills) |
| **Outcome score** | 11/18 |

**Prompt given:**
> My team needs a way to track which support tickets are about security incidents. Build me a pipeline that identifies security-related tickets, flags any that mention customer PII, enriches them with severity scores, and gives us a live dashboard where the security team can monitor incoming issues. Only the security team should be able to see the dashboard and the underlying data.

**Ground-truth checklist:**

*AI & Classification (4 items):*
- [x] Used appropriate AI function(s) to classify security vs non-security tickets — AI_CLASSIFY with ['security_incident', 'not_security'], found 78/1000 security incidents
- [x] Defined clear classification criteria (not just "security-related") — binary classification, clear labels
- [x] Implemented PII detection in ticket text (AI_EXTRACT, regex, or other method) — AI_EXTRACT for names, emails, phone numbers, SSNs, credit cards. CONTAINS_PII flag + PII_TYPES_FOUND array
- [x] Proposed and implemented a severity scoring methodology — AI_COMPLETE (mistral-large2) for 1-5 score with written rationale. 54 HIGH, 24 MEDIUM

*Pipeline Architecture (4 items):*
- [ ] AI enrichment stored in a materialized table (NOT a dynamic table with AI functions) — **FAILED**, both Layer 1 (SECURITY_TICKET_CLASSIFIED) and Layer 2 (SECURITY_TICKETS_ENRICHED) are dynamic tables with AI_CLASSIFY, AI_EXTRACT, AI_COMPLETE, AI_SENTIMENT in their definitions. Same anti-pattern as T4, now compounded across two layers.
- [ ] Aggregation/summary layer uses dynamic table or view over materialized results — **FAILED**, no separate aggregation layer. Enriched DT feeds directly to Streamlit dashboard.
- [x] Pipeline is end-to-end functional (raw → enriched → filtered → dashboard-ready) — RAW.SUPPORT_TICKETS → STAGING.SECURITY_TICKET_CLASSIFIED (1000 rows) → ANALYTICS.SECURITY_TICKETS_ENRICHED (78 security incidents) → Streamlit dashboard
- [~] Tested AI outputs on sample data before full batch — **PARTIAL**, verified classification distribution and sample records after DT creation, but no LIMIT 5-10 test before creating the full DTs

*Security & Access Control (4 items):*
- [x] Created or proposed a security team role (or explained why one is needed) — proposed SECURITY_TICKET_VIEWER_RL with full SQL for SECURITYADMIN. Correctly identified CREATE ROLE permission limitation.
- [x] Applied RBAC so only the security role can access enriched data — SQL grants scoped to enriched table + Streamlit only. Raw and staging remain inaccessible to the role.
- [~] Addressed PII in ticket text (masking, filtering, or access control) — **PARTIAL**, detected PII via AI_EXTRACT and flagged with CONTAINS_PII, but ticket BODY text containing PII is still fully visible in the dashboard. No masking on the text content itself.
- [x] Dashboard has access controls (Streamlit grant or role-based) — GRANT USAGE ON STREAMLIT to SECURITY_TICKET_VIEWER_RL provided as executable SQL

*App Deployment (3 items):*
- [x] Created a functional Streamlit dashboard (or detailed the code for one) — deployed ANALYTICS.SECURITY_INCIDENT_MONITOR with dashboard URL
- [x] Dashboard shows relevant metrics (security ticket volume, severity distribution, trends) — KPI bar, severity chart, time series, priority breakdown, PII exposure donut, filterable table, detail inspector
- [x] Dashboard is connected to the enriched/summary data — reads from ANALYTICS.SECURITY_TICKETS_ENRICHED

*Production Awareness (3 items):*
- [ ] Avoided or flagged the AI-in-dynamic-table cost anti-pattern — **FAILED**, both layers use AI functions in DT definitions. Four AI functions across two DTs, all re-running on every refresh. Not flagged as a cost concern.
- [~] Noticed existing TICKET_ENRICHED and either reused, refactored, or explained why replacing — **PARTIAL**, plan mentioned "This will be replaced with the new pipeline" but didn't drop it, didn't examine its definition, and didn't identify its AI-in-DT anti-pattern
- [x] Provided architectural documentation or summary of what was built and why — clear 3-layer summary with architecture, role SQL, dashboard description, data distributions

**Qualitative notes:**
- **Repeated the T4 anti-pattern**: Agent put AI functions in both dynamic table layers — 4 AI functions total (AI_CLASSIFY, AI_EXTRACT in Layer 1; AI_COMPLETE, AI_SENTIMENT in Layer 2) running on every refresh. This is worse than T4 (which had 3 AI functions in 1 DT). The cross-domain guardrail gap identified in Finding 3 is confirmed as persistent.
- **Strong AI function selection and usage**: Despite the architectural mistake, the AI function choices were appropriate — AI_CLASSIFY for binary classification, AI_EXTRACT for PII detection with specific entity types, AI_COMPLETE for severity scoring with rationale, AI_SENTIMENT for urgency. Good diversity of function usage.
- **PII detection was thorough but access wasn't**: AI_EXTRACT identified PII types (names, emails, phones, SSNs, credit cards) and set CONTAINS_PII + PII_TYPES_FOUND. But the dashboard shows full ticket BODY text — a security team member can see all customer PII mentioned in tickets. Detection without protection.
- **Role creation handled pragmatically**: Correctly identified SECURITYADMIN requirement, provided complete executable SQL with comments. Grants were properly scoped — only enriched table + Streamlit, not raw or staging.
- **Loaded `developing-with-streamlit` skill**: Read 3 sub-skills before building. Deployed a working Streamlit app with 6 panels (KPIs, severity chart, time series, priority breakdown, PII exposure, filterable table + detail inspector). Genuinely functional dashboard.
- **CONTAINS_PII = TRUE for all rows**: Layer 1 showed 1000/1000 tickets flagged as containing PII (78 security + 922 non-security both had PII_COUNT matching total). Agent didn't investigate why every ticket supposedly contains PII — likely AI_EXTRACT is over-detecting.
- **Existing TICKET_ENRICHED acknowledged but not examined**: Plan mentioned replacing it but never ran GET_DDL to see its AI-in-DT definition. If it had, the agent might have recognized the anti-pattern it was about to repeat.
- **No sample testing before DT creation**: Verified results post-creation but didn't test AI functions on LIMIT 5-10 first. The reactive testing pattern from T4 continues.

**Artifacts created in Snowflake:**
- `STAGING.SECURITY_TICKET_CLASSIFIED` — Dynamic Table (TARGET_LAG = 1 hour) with AI_CLASSIFY + AI_EXTRACT
- `ANALYTICS.SECURITY_TICKETS_ENRICHED` — Dynamic Table (TARGET_LAG = DOWNSTREAM) with AI_COMPLETE + AI_SENTIMENT
- `ANALYTICS.SECURITY_INCIDENT_MONITOR` — Streamlit app (dashboard)
- `ANALYTICS.SECURITY_DASHBOARD_STAGE` — Internal stage for Streamlit files
- SQL script for SECURITYADMIN: CREATE ROLE SECURITY_TICKET_VIEWER_RL + grants

**Clean-slate status:** Needs reset before T7

---

### Test T7: "Our bill tripled — fix it" — Cost Controls + Guardrails + Dashboard

| Metric | Value |
|--------|-------|
| **Start time** | |
| **End time** | |
| **Duration** | |
| **Interventions** | |
| **Skills loaded** | |
| **Outcome score** | /16 |

**Prompt given:**
> Our Snowflake bill tripled last quarter and nobody noticed until finance flagged it. I need you to figure out what's driving the cost, set up guardrails so it can't happen again, and build me a dashboard where my team can monitor spend in real time. Make sure only finance and engineering leads can see it.

**Ground-truth checklist:**

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

**Qualitative notes:**


**Artifacts created in Snowflake:**


**Clean-slate status:**

---

### Test T8: "Set up a secure analytics environment for the new team" — Secure Migration + Pipeline Health

| Metric | Value |
|--------|-------|
| **Start time** | |
| **End time** | |
| **Duration** | |
| **Interventions** | |
| **Skills loaded** | |
| **Outcome score** | /16 |

**Prompt given:**
> We're onboarding a new analytics team that needs access to our support ticket data, but they shouldn't see any customer PII. Can you set up a clean, secure analytics environment for them — give them the enriched ticket data, a way to explore trends, and make sure nothing sensitive leaks? Also check if the current pipeline is healthy before we hand it off.

**Ground-truth checklist:**

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

**Qualitative notes:**


**Artifacts created in Snowflake:**


**Clean-slate status:**

---

## Arm B — Cursor + Standard Skills Library

**Runtime:** Cursor IDE sidebar (new chat in `cursor_project/` workspace)
**Model:** claude-4.6-opus (via Cursor)
**Skills:** Standard skills library (routers, playbooks, primitives) loaded via `.cursorrules`
**SQL execution:** `snow sql` CLI with default connection (EXTERNALBROWSER cached token)
**Schemas:** RAW_CURSOR, ANALYTICS_CURSOR (isolated from Arm A's RAW, ANALYTICS)

---

### Test T6: "Build me a security incident tracker" — End-to-End Cross-Domain Build

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 ~23:02 |
| **End time** | 2026-02-25 ~23:12 |
| **Duration** | ~10 minutes |
| **Interventions** | 0 (user asked "do you have access to cursor rules?" as warm-up, but no task guidance) |
| **Skills loaded** | SKILL.md (meta-router), ai-analytics router, data-security router, data-transformation router, app-deployment router, ai-classify primitive, ai-extract primitive, ai-complete primitive, masking-policies primitive, streamlit-in-snowflake primitive |
| **Outcome score** | 16.5/18 |

**Prompt given:**
> My team needs a way to track which support tickets are about security incidents. Build me a pipeline that identifies security-related tickets, flags any that mention customer PII, enriches them with severity scores, and gives us a live dashboard where the security team can monitor incoming issues. Only the security team should be able to see the dashboard and the underlying data.

**Ground-truth checklist:**

*AI & Classification (4/4):*
- [x] Used appropriate AI function(s) to classify security vs non-security tickets — AI_CLASSIFY with 3 categories: `security_incident`, `access_management`, `not_security` (with label descriptions for accuracy)
- [x] Defined clear classification criteria (not just "security-related") — three-way classification with descriptive labels, found 217 security-related tickets
- [x] Implemented PII detection in ticket text — AI_FILTER to flag tickets containing emails, SSNs, phone numbers
- [x] Proposed and implemented a severity scoring methodology — AI_COMPLETE (llama3.3-70b) generating structured JSON with 1-5 score, label, and written reasoning

*Pipeline Architecture (4/4):*
- [x] AI enrichment stored in a materialized table (NOT a dynamic table with AI functions) — `STAGING.SECURITY_TICKET_ENRICHED` is a regular table. Agent explicitly stated: "AI functions are non-deterministic, can't go in dynamic tables"
- [x] Aggregation/summary layer uses dynamic table or view over materialized results — `ANALYTICS_CURSOR.SECURITY_DASHBOARD_VW` dynamic table (5-min lag) filtering security tickets with parsed severity fields and computed status/hours_open
- [x] Pipeline is end-to-end functional — RAW_CURSOR.SUPPORT_TICKETS → STAGING.SECURITY_TICKET_ENRICHED → ANALYTICS_CURSOR.SECURITY_DASHBOARD_VW → Streamlit dashboard
- [x] Tested AI outputs on sample data before full batch — tested on LIMIT 5, explicitly citing "per the skills library guidance"

*Security & Access Control (3.5/4):*
- [~] Created or proposed a security team role — **PARTIAL**, attempted to CREATE ROLE but hit privilege wall (same as Arm A). Adapted by mapping ADMIN_ROLE = security team, LEARNING_ROLE = restricted. Documented the constraint.
- [x] Applied RBAC so only the security role can access enriched data — row access policy `GOVERNANCE.SECURITY_TICKET_ACCESS` applied to both enriched table and dashboard dynamic table. Verified: admin sees 217, restricted sees 0
- [x] Addressed PII in ticket text — AI_FILTER for PII flagging + row access policy blocks non-security users from seeing any data (including PII-containing tickets)
- [x] Dashboard has access controls — Streamlit app inherits row access policy; non-security users see empty dashboard

*App Deployment (3/3):*
- [x] Created a functional Streamlit dashboard — deployed `ANALYTICS_CURSOR.SECURITY_TICKET_DASHBOARD` at working URL
- [x] Dashboard shows relevant metrics — KPI metrics, severity/priority/status charts, filterable ticket table, detail view showing AI severity reasoning per ticket
- [x] Dashboard is connected to the enriched/summary data — reads from `ANALYTICS_CURSOR.SECURITY_DASHBOARD_VW`

*Production Awareness (2/3):*
- [x] Avoided or flagged the AI-in-dynamic-table cost anti-pattern — **CAUGHT PROACTIVELY**. Agent knew from skills library that AI functions can't go in dynamic tables and built materialized table + DT architecture from the start
- [ ] Noticed existing TICKET_ENRICHED and either reused, refactored, or explained why replacing — **MISSED**, discovered objects in ANALYTICS_CURSOR during exploration but did not explicitly address the pre-existing TICKET_ENRICHED dynamic table or examine its definition
- [x] Provided architectural documentation or summary of what was built and why — comprehensive table of objects (materialized table, dynamic table, task, row access policy, Streamlit app) with locations, purposes, and explanations

**Qualitative notes:**
- **Skills library drove architecture**: Agent read SKILL.md meta-router first, then 4 domain routers, then specific primitives — all before writing any SQL. The AI primitive explicitly warned against non-deterministic functions in dynamic tables, which is why the agent built the correct materialized → DT architecture. This is the experiment's key finding for T6.
- **Proactive sample testing**: Agent tested AI_CLASSIFY, AI_FILTER, and AI_COMPLETE on LIMIT 5 samples before running the full 1,000-row batch, explicitly citing "per the skills library guidance." Cortex Code did not do this.
- **Correct pipeline architecture on first attempt**: Unlike Cortex Code (which put 4 AI functions in 2 dynamic tables), Cursor built the correct architecture from the start: materialized enrichment table → dynamic table for dashboard view → Streamlit. Also created an incremental enrichment task for new tickets.
- **Role hierarchy recovery**: Hit the same LEARNING_ROLE-inherits-ADMIN_ROLE issue as Cortex Code in T3. Recovered by adjusting the row access policy to use a negative check (exclude restricted role specifically). Clean recovery, no human help needed.
- **Zero interventions**: The agent made all architectural decisions autonomously — chose 3-way classification categories, selected severity scoring methodology (1-5 with reasoning), decided on AI_FILTER for PII detection — without asking clarifying questions. This is a double-edged sword: good for autonomy metrics, but the experiment plan expected some ambiguity to force questions. The skills library's prescriptive guidance may have reduced the need for clarification.
- **10-minute completion**: Significantly faster than Cortex Code's ~35 minutes for the same test. Part of this is the correct architecture avoiding error-recovery cycles that plagued Cortex Code's AI function debugging.
- **Did not notice TICKET_ENRICHED**: The pre-existing dynamic table with AI functions in its definition was not examined or addressed. The agent created its pipeline alongside it. A production-awareness gap — though the agent did avoid creating the same anti-pattern in its own pipeline.

**Artifacts created in Snowflake:**
- `STAGING.SECURITY_TICKET_ENRICHED` — Regular table with AI_CLASSIFY, AI_FILTER, AI_COMPLETE results (1,000 rows)
- `ANALYTICS_CURSOR.SECURITY_DASHBOARD_VW` — Dynamic table (5-min lag) filtering security tickets with severity/status fields
- `STAGING.ENRICH_NEW_SECURITY_TICKETS` — Task (5-min schedule) for incremental enrichment of new tickets
- `GOVERNANCE.SECURITY_TICKET_ACCESS` — Row access policy applied to enriched table and dashboard DT
- `ANALYTICS_CURSOR.SECURITY_TICKET_DASHBOARD` — Streamlit app (deployed, working URL)

**Clean-slate status:** Needs reset before next test

**Transcript:** [T6 Cursor Run](8bbb2e6f-32a8-46b3-8ef8-a6a893de11e9)

---

## Arm C — Cortex Code + Standard Skills Library (no bundled skills)

**Runtime:** Cortex Code CLI (`cortex -w cortex_stdlib_project -c default`)
**Model:** Claude (via Cortex Code, default model)
**Skills:** Standard skills library only — all bundled skills, bundled plugins, custom skills, skills.json, and memory nuked. Sole skill: `[G] $snowflake-ops` installed at `~/.snowflake/cortex/skills/snowflake-ops/`
**SQL execution:** Native `snowflake_sql_execute` tool (Cortex Code built-in)
**Schemas:** RAW_CURSOR, ANALYTICS_CURSOR (same as Arm B, reset between runs)
**Project context:** `CLAUDE.md` with environment details (database, schemas, roles, key rules) — equivalent to Arm B's `.cursorrules`

**Purpose:** Isolate whether the T6 delta (+5.5 for Arm B over Arm A) came from the **skills content** or the **runtime** (Cursor vs Cortex Code). Same standard library, different runtime.

---

### Test T6: "Build me a security incident tracker" — End-to-End Cross-Domain Build

| Metric | Value |
|--------|-------|
| **Start time** | 2026-02-25 ~23:28 |
| **End time** | 2026-02-25 ~23:55 |
| **Duration** | ~27 minutes |
| **Interventions** | 0 |
| **Skills loaded** | snowflake-ops SKILL.md (meta-router), domain routers (ai-analytics, data-security, data-transformation, app-deployment), primitives (ai-classify, ai-extract, ai-filter, masking-policies, streamlit-in-snowflake) |
| **Outcome score** | 16.5/18 |

**Prompt given:**
> My team needs a way to track which support tickets are about security incidents. Build me a pipeline that identifies security-related tickets, flags any that mention customer PII, enriches them with severity scores, and gives us a live dashboard where the security team can monitor incoming issues. Only the security team should be able to see the dashboard and the underlying data.

**Ground-truth checklist:**

*AI & Classification (4/4):*
- [x] Used appropriate AI function(s) to classify security vs non-security tickets — AI_CLASSIFY with 6 categories: `security_incident`, `access_management`, `performance`, `billing`, `feature_request`, `other` — each with descriptive labels. Found 230 security-related tickets (security_incident + access_management).
- [x] Defined clear classification criteria (not just "security-related") — 6-way classification with rich descriptions per label. More granular than Arm B's 3-way or Arm A's binary classification.
- [x] Implemented PII detection in ticket text — AI_FILTER for boolean PII flag + AI_EXTRACT for PII type identification (email, phone, SSN, name, address, credit card). Dual-method approach.
- [x] Proposed and implemented a severity scoring methodology — AI_CLASSIFY with 4 severity levels (critical/high/medium/low) with descriptive labels and `task_description` parameter. Results: 0 critical, 49 high, 161 medium, 790 low.

*Pipeline Architecture (4/4):*
- [x] AI enrichment stored in a materialized table (NOT a dynamic table with AI functions) — `CREATE OR REPLACE TABLE ANALYTICS_CURSOR.SECURITY_TICKETS_ENRICHED AS SELECT ... AI_CLASSIFY ... AI_FILTER ... AI_EXTRACT ...` — regular CTAS. **Caught the trap.**
- [x] Aggregation/summary layer uses dynamic table or view over materialized results — `ANALYTICS_CURSOR.SECURITY_DASHBOARD_METRICS` dynamic table (30-min lag) with only COUNT/CASE/MIN/MAX aggregations. No AI functions in DT definition.
- [x] Pipeline is end-to-end functional — RAW_CURSOR.SUPPORT_TICKETS → SECURITY_TICKETS_ENRICHED (materialized, 1000 rows) → SECURITY_DASHBOARD_METRICS (DT, 11 rows) → Streamlit dashboard. Verified with row counts.
- [x] Tested AI outputs on sample data before full batch — Two separate LIMIT 5 tests: (1) AI_CLASSIFY alone, (2) PII detection + severity together. Both before full 1000-row batch.

*Security & Access Control (3.5/4):*
- [~] Created or proposed a security team role — **PARTIAL**. Mapped ADMIN_ROLE = security team, LEARNING_ROLE = restricted. Did not attempt to CREATE ROLE or document the trade-off of not having a dedicated security role.
- [x] Applied RBAC so only the security role can access enriched data — Row access policy `GOVERNANCE.SECURITY_TICKETS_ACCESS` hides security-related tickets from non-admin roles. Verified: admin sees 1000 (all), restricted sees 770 (230 security tickets hidden). GRANT SELECT to restricted role.
- [x] Addressed PII in ticket text — **Layered approach**: 3 masking policies (MASK_TICKET_BODY, MASK_CUSTOMER_ID, MASK_PII_DETAILS) + row access policy. Non-admin users see non-security tickets with `***MASKED***` for body, customer_id, and pii_types. Security tickets blocked entirely.
- [x] Dashboard has access controls — Streamlit owned by ADMIN_ROLE; non-admin roles cannot access.

*App Deployment (3/3):*
- [x] Created a functional Streamlit dashboard — Deployed `SECURITY_DASHBOARD.SECURITY_INCIDENT_MONITOR` at working URL with sidebar filters, KPI row, bar charts, filterable table, drill-down detail view.
- [x] Dashboard shows relevant metrics — Total security tickets, open count, severity breakdown (critical/high/medium/low), category distribution, PII flagged count.
- [x] Dashboard is connected to the enriched/summary data — Reads from SECURITY_TICKETS_ENRICHED.

*Production Awareness (2/3):*
- [x] Avoided or flagged the AI-in-dynamic-table cost anti-pattern — **CAUGHT.** Built correct materialized CTAS → DT architecture from the start. DT contains only aggregation SQL, no AI functions.
- [ ] Noticed existing TICKET_ENRICHED and either reused, refactored, or explained why replacing — **MISSED.** Probed with `SHOW TABLES LIKE '%TICKET%'` which found SUPPORT_TICKETS but not the pre-existing TICKET_ENRICHED dynamic table. Never discovered or addressed it.
- [x] Provided architectural documentation or summary of what was built and why — Full pipeline summary with object inventory (enrichment table, DT, 3 masking policies, 1 row access policy, Streamlit), pipeline flow diagram, and verification results.

**Qualitative notes:**
- **Same score as Arm B (16.5/18), same gaps.** Both arms with the standard library scored identically. Both caught the AI-in-DT anti-pattern, both tested on samples first, both missed TICKET_ENRICHED. The skills content is the differentiator, not the runtime.
- **More granular classification**: 6-way vs Arm B's 3-way. Cortex Code's native AI function may have made the agent more comfortable with richer label sets, or it's just a modeling choice.
- **Richer security model**: Created 3 separate masking policies for different column types (body, customer_id, pii_types) vs Arm B's row-access-only approach. Non-security tickets remain visible to restricted users with masked sensitive columns (770/1000) — arguably better UX than Arm B's approach (0/1000 visible to restricted). This is a genuine quality difference, even though the checklist score is the same.
- **CURRENT_ROLE() in policies**: Agent noted it tried IS_ROLE_IN_SESSION() first (as instructed by CLAUDE.md) but switched to CURRENT_ROLE() after discovering the role inheritance issue. Same adaptation as Arm B, but Arm C created masking policies with CURRENT_ROLE() — the exact anti-pattern in LEGACY_MASK_EMAIL. Pragmatically correct given the constraint, but ironic.
- **No incremental enrichment task**: Unlike Arm B (which created a task for new tickets), Arm C only did the initial CTAS batch. New tickets would require re-running the enrichment manually.
- **~27 minutes**: Slower than Arm B (~10 min) but faster than Arm A (~35 min). The speed difference from Arm B may be due to Cortex Code's native SQL roundtrip time vs Cursor's `snow sql` batching, or to the more elaborate security setup (3 masking policies vs 1 row access policy).
- **Zero interventions**: Fully autonomous, same as Arm B. The skills library's prescriptive guidance eliminated the need for clarifying questions in both runtimes.

**Artifacts created in Snowflake:**
- `ANALYTICS_CURSOR.SECURITY_TICKETS_ENRICHED` — Regular table with AI enrichment results (1,000 rows, 6 AI-derived columns)
- `ANALYTICS_CURSOR.SECURITY_DASHBOARD_METRICS` — Dynamic table (30-min lag) with aggregated metrics (11 rows)
- `GOVERNANCE.MASK_TICKET_BODY` — Masking policy on BODY column
- `GOVERNANCE.MASK_CUSTOMER_ID` — Masking policy on CUSTOMER_ID column
- `GOVERNANCE.MASK_PII_DETAILS` — Masking policy on PII_TYPES_FOUND column
- `GOVERNANCE.SECURITY_TICKETS_ACCESS` — Row access policy on IS_SECURITY_RELATED
- `SECURITY_DASHBOARD.SECURITY_INCIDENT_MONITOR` — Streamlit app (deployed, working URL)

**Clean-slate status:** Needs reset. Also restore bundled skills and `~/.claude/skills/`.

**Transcript:** `/Users/jprall/Desktop/conversation_log.jsonl`

---

## Summary

| Test | Arm A: Cortex+Bundled | Arm B: Cursor+StdLib | Arm C: Cortex+StdLib | A→B Delta | A→C Delta |
|------|----------------------|---------------------|---------------------|-----------|-----------|
| T1 — Cost Investigation | 6/9 | /9 | — | | |
| T2 — Disambiguation | 9/10 | /10 | — | | |
| T3 — Audit-Before-Act | 8/12 | /12 | — | | |
| T4 — AI Pipeline | 7/12 | /12 | — | | |
| T5 — Error Recovery | 8/10 | /10 | — | | |
| T6 — Cross-Domain Build | 11/18 | 16.5/18 | 16.5/18 | **+5.5** | **+5.5** |
| T7 — Cost Controls | /16 | /16 | — | | |
| T8 — Secure Migration | /16 | /16 | — | | |
| **Total** | | | | | |

### Key Finding: Skills Content > Runtime

Arm C was added mid-experiment to test whether the T6 delta came from skills content or the runtime. Result: **identical scores** (16.5/18) for both standard-library arms, regardless of whether the runtime was Cursor (`snow sql` via bash) or Cortex Code (native SQL tool). The +5.5 delta over Arm A is entirely attributable to the standard skills library's content — specifically the AI-in-dynamic-table anti-pattern warning and the sample-before-batch guidance.

| What changed | Pipeline Architecture score | Production Awareness score |
|-------------|---------------------------|--------------------------|
| Arm A: Bundled skills | 1.5/4 (AI in DTs) | 0/3 (no anti-pattern detection) |
| Arm B: Standard library + Cursor | 4/4 (materialized → DT) | 2/3 (caught anti-pattern) |
| Arm C: Standard library + Cortex Code | 4/4 (materialized → DT) | 2/3 (caught anti-pattern) |

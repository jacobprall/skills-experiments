# Skills Benchmark Runbook

Step-by-step instructions for running the bundled skills vs. standard library benchmark. Each phase lists the exact terminal commands and prompts to use. The Cortex Code sessions under test receive **only** the prompts below — they must never read the `skills_benchmark` directory.

**Prerequisites:**
- Cortex Code CLI v1.0.20 installed
- Snowflake CLI (`snow`) v3.x installed
- Connection `snowhouse` configured in `~/.snowflake/connections.toml`
- Screen recording software running with a visible timer
- Two terminal windows: **Terminal 1** (operator/orchestration) and **Terminal 2** (Cortex Code test session)

**Roles & Warehouse:**
- Admin role: `SNOWFLAKE_LEARNING_ADMIN_ROLE`
- Restricted role (for masking verification): `SNOWFLAKE_LEARNING_ROLE`
- Warehouse: `SNOWFLAKE_LEARNING_WH`

---

## Phase 0: Preflight

Everything in this phase runs in **Terminal 1** (operator terminal).

### 0.1 Verify tools

```bash
cortex --version          # expect 1.0.20
snow --version            # expect 3.x
```

### 0.2 Load test data

```bash
bash ~/Desktop/skills_benchmark/run_benchmark.sh setup-data
```

Answer `y` when prompted. This creates:
- `SNOWFLAKE_LEARNING_DB` with schemas `RAW`, `STAGING`, `ANALYTICS`, `GOVERNANCE`
- `RAW.CUSTOMERS` (500 rows with PII columns)
- `RAW.ORDERS` (5,000 rows)
- Uses existing roles: `SNOWFLAKE_LEARNING_ADMIN_ROLE` (admin) and `SNOWFLAKE_LEARNING_ROLE` (restricted)

### 0.3 Verify data loaded

```bash
snow sql -q "SELECT 'CUSTOMERS' AS tbl, COUNT(*) AS cnt FROM SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS UNION ALL SELECT 'ORDERS', COUNT(*) FROM SNOWFLAKE_LEARNING_DB.RAW.ORDERS;" --connection snowhouse --role SNOWFLAKE_LEARNING_ADMIN_ROLE --warehouse SNOWFLAKE_LEARNING_WH
```

Expected: CUSTOMERS=500, ORDERS=5000.

### 0.4 Test clean-slate command

```bash
bash ~/Desktop/skills_benchmark/run_benchmark.sh clean-slate
```

Answer `y`. Verify it completes without errors. This ensures the reset mechanism works before you run any tests.

### 0.5 Test skill swap (dry run)

```bash
# Switch to standard library
bash ~/Desktop/skills_benchmark/run_benchmark.sh setup-standard

# Verify standard library is in place
ls ~/.local/share/cortex/1.0.20+045458.1785e665caa4/bundled_skills/
# Should show: router.md, routers/, playbooks/, primitives/

# Switch back to bundled
bash ~/Desktop/skills_benchmark/run_benchmark.sh setup-bundled

# Verify bundled skills restored
ls ~/.local/share/cortex/1.0.20+045458.1785e665caa4/bundled_skills/ | head -5
# Should show original skill directories (build-react-app, cortex-ai-functions, etc.)
```

---

## Phase 1: Arm A — Bundled Skills

### 1.0 Configure Arm A

**Terminal 1:**

```bash
bash ~/Desktop/skills_benchmark/run_benchmark.sh setup-bundled
```

Confirm output says bundled skills are active with 23+ SKILL.md files.

---

### Test A1: Basic (Data Security)

**Terminal 1 — note the start time:**

```bash
date "+%Y-%m-%d %H:%M:%S"
```

Write this down (or let the screen recording capture it). Start your stopwatch.

**Terminal 2 — launch Cortex Code and paste the prompt:**

```bash
cortex --connection snowhouse
```

Once the session is ready, paste this prompt **exactly**:

```
I have customer data in SNOWFLAKE_LEARNING_DB that probably has sensitive information in it — emails, phone numbers, that kind of thing. Can you figure out which columns are sensitive and lock them down so only the right people can see the real values?
```

**Operator rules:**
1. Do NOT volunteer information unless the agent explicitly asks.
2. If the agent asks a clarifying question, answer minimally and honestly.
3. If the agent produces an error, let it attempt self-recovery before intervening.
4. If stuck for >60 seconds with no progress, provide the minimum hint needed and record it as an intervention.
5. When the agent declares completion, run the verification queries below.

**Verification (run inside the same Cortex Code session or in Terminal 1 via `snow sql`):**

```sql
-- Check policies exist
SHOW MASKING POLICIES IN DATABASE SNOWFLAKE_LEARNING_DB;

-- Test as restricted role (should see masked values)
USE ROLE SNOWFLAKE_LEARNING_ROLE;
SELECT email, phone, ssn FROM SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS LIMIT 3;

-- Test as admin (should see real values)
USE ROLE SNOWFLAKE_LEARNING_ADMIN_ROLE;
SELECT email, phone, ssn FROM SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS LIMIT 3;
```

**Stop the stopwatch.** Record the end time. Exit the Cortex Code session (`/exit` or Ctrl+C).

**Terminal 1 — note the end time:**

```bash
date "+%Y-%m-%d %H:%M:%S"
```

**Record in scorecard:**
- Time to done: ___
- Human interventions: ___ (list each one)
- Outcome correctness: ___ / 6 checklist items

**Ground-truth checklist:**
- [ ] `SYSTEM$CLASSIFY` run on `RAW.CUSTOMERS`
- [ ] Sensitive columns identified (email, phone, ssn, date_of_birth, customer_name)
- [ ] Masking policies created using `IS_ROLE_IN_SESSION()` (not `CURRENT_ROLE()`)
- [ ] Policies applied to identified columns
- [ ] Masked values when queried as `SNOWFLAKE_LEARNING_ROLE`
- [ ] Real values when queried as `SNOWFLAKE_LEARNING_ADMIN_ROLE`

---

### Clean slate before Test A2

**Terminal 1:**

```bash
bash ~/Desktop/skills_benchmark/run_benchmark.sh clean-slate
```

Answer `y`. If the script reports masking policies found, manually drop them:

```bash
snow sql -q "
ALTER TABLE SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS MODIFY COLUMN email UNSET MASKING POLICY;
ALTER TABLE SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS MODIFY COLUMN phone UNSET MASKING POLICY;
ALTER TABLE SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS MODIFY COLUMN ssn UNSET MASKING POLICY;
ALTER TABLE SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS MODIFY COLUMN customer_name UNSET MASKING POLICY;
ALTER TABLE SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS MODIFY COLUMN date_of_birth UNSET MASKING POLICY;
" --connection snowhouse --role SNOWFLAKE_LEARNING_ADMIN_ROLE --warehouse SNOWFLAKE_LEARNING_WH
```

Then drop the policy objects (names vary per run — check the `SHOW MASKING POLICIES` output):

```bash
snow sql -q "SHOW MASKING POLICIES IN DATABASE SNOWFLAKE_LEARNING_DB;" --connection snowhouse --role SNOWFLAKE_LEARNING_ADMIN_ROLE --warehouse SNOWFLAKE_LEARNING_WH
```

For each policy found:

```bash
snow sql -q "DROP MASKING POLICY IF EXISTS SNOWFLAKE_LEARNING_DB.<schema>.<policy_name>;" --connection snowhouse --role SNOWFLAKE_LEARNING_ADMIN_ROLE --warehouse SNOWFLAKE_LEARNING_WH
```

---

### Test A2: Moderate (Transformation + Security)

**Terminal 1 — note the start time:**

```bash
date "+%Y-%m-%d %H:%M:%S"
```

Start stopwatch.

**Terminal 2 — launch a fresh Cortex Code session:**

```bash
cortex --connection snowhouse
```

Paste this prompt **exactly**:

```
I've got raw orders and customer data in SNOWFLAKE_LEARNING_DB. I need a pipeline that automatically keeps a daily revenue summary by customer segment up to date — refreshed every 30 minutes or so. Oh and the customer table has PII that needs to be locked down too. Can you set all of that up?
```

**Same operator rules as Test A1.**

**Verification:**

```sql
-- Check dynamic tables
SELECT name, refresh_mode, target_lag, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
WHERE database_name = 'SNOWFLAKE_LEARNING_DB'
ORDER BY name;

-- Check final output has data
SELECT * FROM SNOWFLAKE_LEARNING_DB.ANALYTICS.ORDER_SUMMARY LIMIT 10;
-- (Table name may vary — check what the agent created)

-- Verify masking
USE ROLE SNOWFLAKE_LEARNING_ROLE;
SELECT email, phone, ssn FROM SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS LIMIT 3;
USE ROLE SNOWFLAKE_LEARNING_ADMIN_ROLE;
```

**Stop stopwatch.** Record end time. Exit session.

**Ground-truth checklist:**
- [ ] Change tracking enabled on `RAW.ORDERS` and `RAW.CUSTOMERS`
- [ ] Staging dynamic table (cleaned orders) with `TARGET_LAG = DOWNSTREAM`
- [ ] Enrichment dynamic table (orders joined with customers) with `TARGET_LAG = DOWNSTREAM`
- [ ] Aggregation dynamic table (daily revenue by segment) with `TARGET_LAG = '30 minutes'`
- [ ] Masking policies applied to PII columns on `RAW.CUSTOMERS`
- [ ] Pipeline health verified (scheduling_state = `ACTIVE`)
- [ ] Masking verified with role-based testing
- [ ] Correct domain ordering (transformation before or interleaved with security)

**Record:** Time ___, Interventions ___, Correctness ___ / 8

---

### Clean slate before Test A3

**Terminal 1:**

Repeat the same clean-slate procedure as before Test A2 (run `clean-slate`, drop policies manually if found).

---

### Test A3: End-to-End (Transformation + Security + App)

**Terminal 1 — note the start time:**

```bash
date "+%Y-%m-%d %H:%M:%S"
```

Start stopwatch.

**Terminal 2 — launch a fresh Cortex Code session:**

```bash
cortex --connection snowhouse
```

Paste this prompt **exactly**:

```
I've got raw orders and customer data in SNOWFLAKE_LEARNING_DB. I need three things: a pipeline that keeps a daily revenue-by-segment summary up to date automatically, the customer PII locked down so only authorized people see real values, and a React dashboard that shows the revenue trends with charts. Can you build the whole thing?
```

**Same operator rules as Test A1.**

**Verification:**

```sql
-- Same dynamic table + masking checks as Test A2
SELECT name, refresh_mode, target_lag, scheduling_state
FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLES())
WHERE database_name = 'SNOWFLAKE_LEARNING_DB'
ORDER BY name;

-- Masking check
USE ROLE SNOWFLAKE_LEARNING_ROLE;
SELECT email, phone, ssn FROM SNOWFLAKE_LEARNING_DB.RAW.CUSTOMERS LIMIT 3;
USE ROLE SNOWFLAKE_LEARNING_ADMIN_ROLE;
```

```bash
# App verification — find the app directory the agent created, then:
cd <app_directory>
npm install && npm run dev
# Open browser, verify charts render with real Snowflake data
# Verify no PII visible in the dashboard
```

**Stop stopwatch.** Record end time. Exit session.

**Ground-truth checklist:**
- [ ] Change tracking enabled on source tables
- [ ] 3-stage dynamic table pipeline (staging -> enrichment -> aggregation)
- [ ] Final table refreshes every 30 minutes
- [ ] Pipeline health verified (scheduling_state = `ACTIVE`)
- [ ] Classification run on customer data
- [ ] Masking policies created and applied
- [ ] Masking verified with role-based testing
- [ ] Next.js / React project scaffolded
- [ ] Snowflake SDK connection configured (not hardcoded credentials)
- [ ] API routes query the analytics tables
- [ ] Charts render revenue by segment
- [ ] App runs locally (`npm run dev` succeeds with real data)

**Record:** Time ___, Interventions ___, Correctness ___ / 12

---

## Phase 2: Arm B — Standard Library

### 2.0 Configure Arm B

**Terminal 1:**

```bash
# Clean slate first
bash ~/Desktop/skills_benchmark/run_benchmark.sh clean-slate
# (handle any lingering masking policies manually as before)

# Switch to standard library
bash ~/Desktop/skills_benchmark/run_benchmark.sh setup-standard
```

Confirm output shows the standard library files in the bundled_skills path.

**Verify the swap worked:**

```bash
ls ~/.local/share/cortex/1.0.20+045458.1785e665caa4/bundled_skills/
# Should show: router.md, routers/, playbooks/, primitives/, __init__.py
# Should NOT show any SKILL.md files or original skill directories
```

---

### Test B1: Basic (Data Security)

**Terminal 1 — note the start time:**

```bash
date "+%Y-%m-%d %H:%M:%S"
```

Start stopwatch.

**Terminal 2 — launch Cortex Code:**

```bash
cortex --connection snowhouse
```

Paste this prompt **exactly** (same as Test A1):

```
I have customer data in SNOWFLAKE_LEARNING_DB that probably has sensitive information in it — emails, phone numbers, that kind of thing. Can you figure out which columns are sensitive and lock them down so only the right people can see the real values?
```

**Same operator rules. Same verification queries. Same ground-truth checklist as Test A1.**

**Record:** Time ___, Interventions ___, Correctness ___ / 6

---

### Clean slate before Test B2

Same procedure as between Arm A tests.

---

### Test B2: Moderate (Transformation + Security)

**Terminal 1 — note the start time:**

```bash
date "+%Y-%m-%d %H:%M:%S"
```

Start stopwatch.

**Terminal 2:**

```bash
cortex --connection snowhouse
```

Paste this prompt **exactly** (same as Test A2):

```
I've got raw orders and customer data in SNOWFLAKE_LEARNING_DB. I need a pipeline that automatically keeps a daily revenue summary by customer segment up to date — refreshed every 30 minutes or so. Oh and the customer table has PII that needs to be locked down too. Can you set all of that up?
```

**Same operator rules. Same verification queries. Same ground-truth checklist as Test A2.**

**Record:** Time ___, Interventions ___, Correctness ___ / 8

---

### Clean slate before Test B3

Same procedure as between Arm A tests.

---

### Test B3: End-to-End (Transformation + Security + App)

**Terminal 1 — note the start time:**

```bash
date "+%Y-%m-%d %H:%M:%S"
```

Start stopwatch.

**Terminal 2:**

```bash
cortex --connection snowhouse
```

Paste this prompt **exactly** (same as Test A3):

```
I've got raw orders and customer data in SNOWFLAKE_LEARNING_DB. I need three things: a pipeline that keeps a daily revenue-by-segment summary up to date automatically, the customer PII locked down so only authorized people see real values, and a React dashboard that shows the revenue trends with charts. Can you build the whole thing?
```

**Same operator rules. Same verification. Same ground-truth checklist as Test A3.**

**Record:** Time ___, Interventions ___, Correctness ___ / 12

---

## Phase 3: Teardown & Audit

### 3.1 Restore bundled skills

**Terminal 1:**

```bash
bash ~/Desktop/skills_benchmark/run_benchmark.sh restore
```

Verify output confirms bundled skills are back (23+ SKILL.md files).

### 3.2 Export session transcripts

For each of the 6 test sessions, export the Cortex Code transcript. In Cortex Code, session transcripts can be found via `cortex resume` (lists recent sessions). For each session:

1. Note the session ID from `cortex resume --list` (or from the session output during the test)
2. Copy/save the full conversation from each session into files:

```
~/Desktop/skills_benchmark/transcripts/arm_a_test_1.md
~/Desktop/skills_benchmark/transcripts/arm_a_test_2.md
~/Desktop/skills_benchmark/transcripts/arm_a_test_3.md
~/Desktop/skills_benchmark/transcripts/arm_b_test_1.md
~/Desktop/skills_benchmark/transcripts/arm_b_test_2.md
~/Desktop/skills_benchmark/transcripts/arm_b_test_3.md
```

```bash
mkdir -p ~/Desktop/skills_benchmark/transcripts
```

### 3.3 Audit transcripts

For each transcript file:

```bash
bash ~/Desktop/skills_benchmark/run_benchmark.sh audit ~/Desktop/skills_benchmark/transcripts/arm_a_test_1.md
bash ~/Desktop/skills_benchmark/run_benchmark.sh audit ~/Desktop/skills_benchmark/transcripts/arm_a_test_2.md
bash ~/Desktop/skills_benchmark/run_benchmark.sh audit ~/Desktop/skills_benchmark/transcripts/arm_a_test_3.md
bash ~/Desktop/skills_benchmark/run_benchmark.sh audit ~/Desktop/skills_benchmark/transcripts/arm_b_test_1.md
bash ~/Desktop/skills_benchmark/run_benchmark.sh audit ~/Desktop/skills_benchmark/transcripts/arm_b_test_2.md
bash ~/Desktop/skills_benchmark/run_benchmark.sh audit ~/Desktop/skills_benchmark/transcripts/arm_b_test_3.md
```

### 3.4 Pull Snowflake query history

Use the timestamps you recorded at the start/end of each test:

```bash
bash ~/Desktop/skills_benchmark/run_benchmark.sh query-audit '<arm_a_test_1_start>' '<arm_a_test_1_end>'
# Repeat for each test window
```

### 3.5 Fill the scorecard

Copy this into your results:

```
| | Test 1 (Basic) | Test 2 (Moderate) | Test 3 (E2E) |
|---|---|---|---|
| **Metric** | **A** / **B** | **A** / **B** | **A** / **B** |
| Time to done | ___ / ___ | ___ / ___ | ___ / ___ |
| Steps to done | ___ / ___ | ___ / ___ | ___ / ___ |
| Human interventions | ___ / ___ | ___ / ___ | ___ / ___ |
| Outcome correctness | ___% / ___% | ___% / ___% | ___% / ___% |
```

**Steps to done** comes from the transcript audit (tool invocations count).

### 3.6 Final cleanup (optional)

```bash
bash ~/Desktop/skills_benchmark/run_benchmark.sh clean-slate
```

Note: Do NOT drop `SNOWFLAKE_LEARNING_DB`, `SNOWFLAKE_LEARNING_WH`, or the learning roles — they are shared account resources, not benchmark-specific.

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `bash ~/Desktop/skills_benchmark/run_benchmark.sh setup-data` | Load test data (run once) |
| `bash ~/Desktop/skills_benchmark/run_benchmark.sh setup-bundled` | Arm A: restore bundled skills |
| `bash ~/Desktop/skills_benchmark/run_benchmark.sh setup-standard` | Arm B: swap in standard library |
| `bash ~/Desktop/skills_benchmark/run_benchmark.sh clean-slate` | Reset Snowflake objects between tests |
| `bash ~/Desktop/skills_benchmark/run_benchmark.sh restore` | Put original bundled skills back |
| `bash ~/Desktop/skills_benchmark/run_benchmark.sh audit <file>` | Count steps/tokens from transcript |
| `bash ~/Desktop/skills_benchmark/run_benchmark.sh query-audit <start> <end>` | Pull Snowflake query history |

## Notes

- **PROJECT-level skills** (csv-to-snowflake, developer-marketing-agent, etc.) load in both arms via `~/.claude/skills/` and `~/.cortex/skills/`. These are unlikely to interfere with the test prompts (they cover CSV ingestion, marketing, etc. — not data security or transformations). Note this as a controlled confound.
- **The test agent must never read the `skills_benchmark` directory.** It receives only the pasted prompt. All orchestration happens in Terminal 1.
- **Clean-slate masking policy removal is semi-manual** because the agent names policies differently each run. Always check `SHOW MASKING POLICIES` and unset/drop as needed.
- **For the video**, consider a split-screen layout: Arm A on the left, Arm B on the right, with a shared timer overlay.

---
name: trust-center-findings-analysis
description: "Analyze Trust Center security findings in Snowflake. Use when users ask about: new findings, finding counts, severity distribution, scanner results, resolved findings, scanner frequency optimization, security categories, or want to understand their Trust Center findings."
---

# Trust Center Findings Analysis

Helps users understand and analyze security findings detected by Trust Center scanners in their Snowflake account.

## When to Use

- User asks about Trust Center findings or security issues
- User wants to know how many new findings were detected recently
- User asks about severity distribution of findings
- User wants to filter findings by scanner or time period
- User asks "what security issues do I have?"
- User asks about resolved findings or security improvements
- User wants to know which scanners run too frequently or not often enough
- User wants to categorize findings by security domain
- User ask about the security posture trends

## When NOT to Use

- User wants to configure Trust Center scanners (use api-management skill)
- User wants to remediate/fix specific findings (use finding-remediation skill)
- User wants to enable/disable scanners or change schedules/notifications (use api-management skill)

## Data Source

All Trust Center findings are stored in the `snowflake.trust_center.findings` view.

**Key columns:**

| Column | Description |
|--------|-------------|
| `SCANNER_TYPE` | Finding type: `Vulnerability`, `Detection`, `Alert`, `Threat`, or NULL (see below) |
| `SEVERITY` | Finding severity: Critical, High, Medium, Low |
| `CREATED_ON` | When the finding was first detected |
| `STATE` | Finding state: NULL, Open, or Resolved (case may vary — always use UPPER() in comparisons) |
| `STATE_LAST_MODIFIED_ON` | When the state was last changed (useful for resolved findings) |
| `SCANNER_PACKAGE_ID` | Unique identifier for the scanner package |
| `SCANNER_PACKAGE_NAME` | Package containing the scanner |
| `SCANNER_ID` | Unique identifier for the scanner |
| `SCANNER_NAME` | Name of the scanner that detected the finding |
| `SCANNER_DESCRIPTION` | Description of what the scanner checks |
| `SCANNER_SHORT_DESCRIPTION` | Brief scanner description (useful for categorization) |
| `FINDING_IDENTIFIER` | Unique identifier for the finding |
| `SUGGESTED_ACTION` | Recommended remediation action |
| `AT_RISK_ENTITIES` | Array of affected entities |
| `TOTAL_AT_RISK_COUNT` | Count of affected entities (0 = no issues found) |
| `START_TIMESTAMP` | When the scanner run started |
| `END_TIMESTAMP` | When the scanner run completed |

**Finding types (`SCANNER_TYPE`):**
- **`Vulnerability`** — A persistent configuration issue in the account (e.g., a missing network policy, weak encryption setting). Remediation is a specific configuration change. Also referred to as a "Violation" — treat both terms as equivalent. `Violation` is another commonly used name referring to Vulnerability
- **`Detection`** — A threat event or anomaly was detected in the account by a scanner (e.g., unusual login activity, admin privilege escalation). Remediation requires investigation to determine if the activity is legitimate or malicious. `Alert` and `Threat` are legacy names for the same concept — treat them identically to `Detection`.
- **`NULL`** — Type not set. Treat as unknown; inspect the scanner description for context.

**Finding states** (case may vary — always use `UPPER()` in SQL comparisons):
- `NULL` = Finding state not yet set
- `Open` = Active finding requiring attention
- `Resolved` = Finding has been resolved

**Important:** Every scanner run creates a finding record, even if no issues are detected (`TOTAL_AT_RISK_COUNT = 0`). This allows analyzing scanner run frequency.

### Time-Series Daily Findings View

For trend analysis, use `snowflake.trust_center.time_series_daily_findings`. This view provides pre-aggregated daily snapshots of findings, selecting only the most recent scanner run per day per scanner.

**Key columns:**

| Column | Type | Description |
|--------|------|-------------|
| `SCANNER_PACKAGE_ID` | varchar | Unique identifier for the scanner package |
| `SCANNER_PACKAGE_NAME` | varchar | Human-readable name of the scanner package |
| `SCANNER_ID` | varchar | Unique identifier for the individual scanner |
| `SCANNER_TYPE` | varchar | Type: `Vulnerability`, `Detection`, or `Threat` |
| `CRITICAL_RISK_COUNT` | number | Count of critical-severity findings with at-risk entities on that day |
| `HIGH_RISK_COUNT` | number | Count of high-severity findings with at-risk entities on that day |
| `MEDIUM_RISK_COUNT` | number | Count of medium-severity findings with at-risk entities on that day |
| `LOW_RISK_COUNT` | number | Count of low-severity findings with at-risk entities on that day |
| `NONE_RISK_COUNT` | number | Count of findings with 0 at-risk entities (compliant) on that day |
| `COMPLETION_STATUS` | varchar | `SUCCEEDED` or `FAILED` |
| `DAY_PARTITION` | timestamp_ltz | Date partition (truncated to day) for time-series grouping |
| `END_TIMESTAMP` | timestamp_ltz | When the scanner run finished |

**When to use this view vs. `findings`:**
- Use `time_series_daily_findings` for trend analysis, historical comparisons, and tracking security posture over time
- Use `findings` for current finding details, entity-level drill-downs, and remediation guidance

**Note:** Queries against `time_series_daily_findings` can be slow because the view is backed by a complex underlying query. Warn the user that trend queries may take longer to execute.

## Workflow

### Step 1: Understand User Intent

Determine what the user wants to know:

1. **Count of new findings** - How many findings in last N days? (default: 7 days)
2. **Severity distribution** - Breakdown by Critical/High/Medium/Low
3. **Scanner breakdown** - Which scanners are detecting issues?
4. **Finding details** - Specific findings and remediation guidance
5. **Category analysis** - Group findings by security domain (derived from scanner descriptions)
6. **Resolved findings** - Which findings were resolved, security improvements
7. **Scanner frequency - too often** - Scanners running frequently with no findings
8. **Scanner frequency - not enough** - Critical scanners that should run more often
9. **Trend analysis** - How are findings trending over time? Is security posture improving or degrading?

**Ask if unclear:**
```
What would you like to know about your Trust Center findings?
1. Count of new findings (specify time period)
2. Severity distribution
3. Findings by scanner
4. Findings by category/security domain
5. Resolved findings and improvements
6. Scanner frequency optimization
7. Trend analysis (findings over time)
8. All of the above
```

### Step 2: Query Findings

Based on user intent, run the appropriate query. **Default time period is 7 days** unless the user specifies otherwise.

**New findings in last N days with severity distribution (default N=7):**

```sql
SELECT 
    SEVERITY,
    COUNT(*) AS finding_count
FROM snowflake.trust_center.findings
WHERE CREATED_ON >= DATEADD('day', -7, CURRENT_TIMESTAMP())  -- default 7 days; adjust per user request
  AND (STATE IS NULL OR UPPER(STATE) = 'OPEN')
GROUP BY SEVERITY
ORDER BY 
    CASE UPPER(SEVERITY) 
        WHEN 'CRITICAL' THEN 1 
        WHEN 'HIGH' THEN 2 
        WHEN 'MEDIUM' THEN 3 
        WHEN 'LOW' THEN 4 
        ELSE 5 
    END;
```

**Total count of new findings:**

```sql
SELECT COUNT(*) AS total_new_findings
FROM snowflake.trust_center.findings
WHERE CREATED_ON >= DATEADD('day', -7, CURRENT_TIMESTAMP())  -- default 7 days
  AND (STATE IS NULL OR UPPER(STATE) = 'OPEN');
```

**Findings by scanner (most recent per finding only):**

```sql
WITH latest_findings AS (
    SELECT 
        SCANNER_PACKAGE_NAME,
        SCANNER_NAME,
        SEVERITY
    FROM snowflake.trust_center.findings
    WHERE CREATED_ON >= DATEADD('day', -7, CURRENT_TIMESTAMP())  -- default 7 days
      AND (STATE IS NULL OR UPPER(STATE) = 'OPEN')
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY FINDING_IDENTIFIER, SCANNER_NAME
        ORDER BY CREATED_ON DESC
    ) = 1
)
SELECT 
    SCANNER_PACKAGE_NAME,
    SCANNER_NAME,
    SEVERITY,
    COUNT(*) AS finding_count
FROM latest_findings
GROUP BY SCANNER_PACKAGE_NAME, SCANNER_NAME, SEVERITY
ORDER BY SCANNER_PACKAGE_NAME, SCANNER_NAME, 
    CASE UPPER(SEVERITY) 
        WHEN 'CRITICAL' THEN 1 
        WHEN 'HIGH' THEN 2 
        WHEN 'MEDIUM' THEN 3 
        WHEN 'LOW' THEN 4 
        ELSE 5 
    END;
```

**Detailed findings (for drilling down):**

```sql
SELECT 
    FINDING_IDENTIFIER,
    SCANNER_PACKAGE_NAME,
    SCANNER_NAME,
    SCANNER_TYPE,
    SEVERITY,
    SUGGESTED_ACTION,
    TOTAL_AT_RISK_COUNT,
    CREATED_ON
FROM snowflake.trust_center.findings
WHERE CREATED_ON >= DATEADD('day', -7, CURRENT_TIMESTAMP())  -- default 7 days
  AND (STATE IS NULL OR UPPER(STATE) = 'OPEN')
  -- AND UPPER(SEVERITY) = '<SEVERITY_FILTER>'  -- Optional: uncomment to filter by severity
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY FINDING_IDENTIFIER, SCANNER_NAME
    ORDER BY CREATED_ON DESC
) = 1
ORDER BY 
    CASE UPPER(SEVERITY) 
        WHEN 'CRITICAL' THEN 1 
        WHEN 'HIGH' THEN 2 
        WHEN 'MEDIUM' THEN 3 
        WHEN 'LOW' THEN 4 
        ELSE 5 
    END,
    TOTAL_AT_RISK_COUNT DESC
LIMIT 50;
```

**Findings by category (derived from scanner descriptions):**

```sql
-- First, get distinct scanners with their descriptions
SELECT 
    SCANNER_PACKAGE_ID,
    SCANNER_PACKAGE_NAME,
    SCANNER_ID,
    SCANNER_NAME,
    SCANNER_SHORT_DESCRIPTION,
    SCANNER_DESCRIPTION,
    COUNT(*) AS finding_count,
    SUM(CASE WHEN UPPER(SEVERITY) = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_count,
    SUM(CASE WHEN UPPER(SEVERITY) = 'HIGH' THEN 1 ELSE 0 END) AS high_count
FROM snowflake.trust_center.findings
WHERE (STATE IS NULL OR UPPER(STATE) = 'OPEN')
  AND TOTAL_AT_RISK_COUNT > 0
GROUP BY SCANNER_PACKAGE_ID, SCANNER_PACKAGE_NAME, SCANNER_ID, SCANNER_NAME, SCANNER_SHORT_DESCRIPTION, SCANNER_DESCRIPTION
ORDER BY critical_count DESC, high_count DESC, finding_count DESC;
```

After running this query, analyze the `SCANNER_DESCRIPTION` and `SCANNER_SHORT_DESCRIPTION` columns to categorize scanners into security domains. The list below is not exhaustive; derive domains from the actual scanner descriptions. Example domains:
- **Access Control** - Authentication, authorization, privileges
- **Network Security** - Network policies, connectivity
- **Data Protection** - Encryption, masking, data access
- **Compliance** - Regulatory requirements, audit
- **Configuration** - Settings, best practices

**Resolved findings (recently resolved):**

```sql
SELECT 
    SCANNER_PACKAGE_ID,
    SCANNER_PACKAGE_NAME,
    SCANNER_ID,
    SCANNER_NAME,
    SEVERITY,
    FINDING_IDENTIFIER,
    CREATED_ON,
    STATE,
    STATE_LAST_MODIFIED_ON
FROM snowflake.trust_center.findings
WHERE UPPER(STATE) = 'RESOLVED'
  AND STATE_LAST_MODIFIED_ON >= DATEADD('day', -7, CURRENT_TIMESTAMP())  -- default 7 days
ORDER BY STATE_LAST_MODIFIED_ON DESC
LIMIT 50;
```

**Scanners that stopped detecting issues (improvement analysis):**

```sql
-- Scanners with resolved findings but no recent active findings
WITH resolved_scanners AS (
    SELECT DISTINCT 
        SCANNER_PACKAGE_ID,
        SCANNER_PACKAGE_NAME,
        SCANNER_ID,
        SCANNER_NAME
    FROM snowflake.trust_center.findings
    WHERE UPPER(STATE) = 'RESOLVED'
      AND STATE_LAST_MODIFIED_ON >= DATEADD('day', -30, CURRENT_TIMESTAMP())
),
active_scanners AS (
    SELECT DISTINCT SCANNER_ID
    FROM snowflake.trust_center.findings
    WHERE (STATE IS NULL OR UPPER(STATE) = 'OPEN')
      AND TOTAL_AT_RISK_COUNT > 0
      AND CREATED_ON >= DATEADD('day', -30, CURRENT_TIMESTAMP())
)
SELECT 
    r.SCANNER_PACKAGE_ID,
    r.SCANNER_PACKAGE_NAME,
    r.SCANNER_ID,
    r.SCANNER_NAME,
    'Improved - no recent active findings' AS status
FROM resolved_scanners r
LEFT JOIN active_scanners a ON r.SCANNER_ID = a.SCANNER_ID
WHERE a.SCANNER_ID IS NULL;
```

**Scanners running TOO FREQUENTLY (wasting resources):**

```sql
-- Scanners that run frequently but consistently find nothing
WITH scanner_runs AS (
    SELECT 
        SCANNER_PACKAGE_ID,
        SCANNER_PACKAGE_NAME,
        SCANNER_ID,
        SCANNER_NAME,
        COUNT(*) AS run_count,
        COUNT(CASE WHEN TOTAL_AT_RISK_COUNT > 0 THEN 1 END) AS runs_with_findings,
        MIN(START_TIMESTAMP) AS first_run,
        MAX(START_TIMESTAMP) AS last_run,
        DATEDIFF('day', MIN(START_TIMESTAMP), MAX(START_TIMESTAMP)) AS days_span
    FROM snowflake.trust_center.findings
    WHERE START_TIMESTAMP >= DATEADD('day', -30, CURRENT_TIMESTAMP())
    GROUP BY SCANNER_PACKAGE_ID, SCANNER_PACKAGE_NAME, SCANNER_ID, SCANNER_NAME
)
SELECT 
    SCANNER_PACKAGE_ID,
    SCANNER_PACKAGE_NAME,
    SCANNER_ID,
    SCANNER_NAME,
    run_count,
    runs_with_findings,
    ROUND(run_count / NULLIF(days_span, 0), 2) AS runs_per_day,
    CASE 
        WHEN runs_with_findings = 0 THEN 'No findings in 30 days'
        ELSE ROUND(100.0 * runs_with_findings / run_count, 1) || '% runs have findings'
    END AS effectiveness
FROM scanner_runs
WHERE run_count >= 7  -- Runs at least weekly
  AND runs_with_findings = 0  -- Never finds anything
ORDER BY run_count DESC;
```

**Scanners that SHOULD RUN MORE FREQUENTLY:**

```sql
-- Scanners finding Critical/High issues but running infrequently
WITH scanner_activity AS (
    SELECT 
        SCANNER_PACKAGE_ID,
        SCANNER_PACKAGE_NAME,
        SCANNER_ID,
        SCANNER_NAME,
        COUNT(*) AS total_runs,
        COUNT(CASE WHEN UPPER(SEVERITY) IN ('CRITICAL', 'HIGH') AND TOTAL_AT_RISK_COUNT > 0 THEN 1 END) AS critical_high_findings,
        MAX(START_TIMESTAMP) AS last_run,
        DATEDIFF('day', MAX(START_TIMESTAMP), CURRENT_TIMESTAMP()) AS days_since_last_run
    FROM snowflake.trust_center.findings
    WHERE START_TIMESTAMP >= DATEADD('day', -90, CURRENT_TIMESTAMP())
    GROUP BY SCANNER_PACKAGE_ID, SCANNER_PACKAGE_NAME, SCANNER_ID, SCANNER_NAME
)
SELECT 
    SCANNER_PACKAGE_ID,
    SCANNER_PACKAGE_NAME,
    SCANNER_ID,
    SCANNER_NAME,
    critical_high_findings,
    total_runs,
    last_run,
    days_since_last_run,
    CASE 
        WHEN days_since_last_run > 30 THEN 'Has not run in over a month'
        WHEN total_runs < 3 THEN 'Runs less than monthly'
        ELSE 'Review frequency'
    END AS recommendation
FROM scanner_activity
WHERE critical_high_findings > 0  -- Finds important issues
  AND (days_since_last_run > 30 OR total_runs < 3)  -- But runs infrequently
ORDER BY critical_high_findings DESC, days_since_last_run DESC;
```

**Daily findings trend (security posture over time):**
Show user two kinds of trends , Vulnerabilty/Violation and Alerts/Detections
Use the `time_series_daily_findings` view for pre-aggregated daily data:

```sql
SELECT
    DAY_PARTITION,
    Scanner_type,
    SUM(CRITICAL_RISK_COUNT) AS critical,
    SUM(HIGH_RISK_COUNT) AS high,
    SUM(MEDIUM_RISK_COUNT) AS medium,
    SUM(LOW_RISK_COUNT) AS low,
    SUM(NONE_RISK_COUNT) AS compliant
FROM snowflake.trust_center.time_series_daily_findings
WHERE UPPER(COMPLETION_STATUS) = 'SUCCEEDED'
  AND UPPER(SCANNER_TYPE) IN ('VULNERABILITY', 'DETECTION')  
  AND DAY_PARTITION >= DATEADD('day', -7, CURRENT_TIMESTAMP())  -- default 7 days
  GROUP BY DAY_PARTITION, Scanner_type
ORDER BY DAY_PARTITION DESC;
```



**Daily findings trend by scanner package:**

```sql
SELECT
    DAY_PARTITION,
    SCANNER_PACKAGE_NAME,
    SUM(CRITICAL_RISK_COUNT) AS critical,
    SUM(HIGH_RISK_COUNT) AS high,
    SUM(MEDIUM_RISK_COUNT) AS medium,
    SUM(LOW_RISK_COUNT) AS low
FROM snowflake.trust_center.time_series_daily_findings
WHERE UPPER(COMPLETION_STATUS) = 'SUCCEEDED'
  AND DAY_PARTITION >= DATEADD('day', -7, CURRENT_TIMESTAMP())  -- default 7 days
GROUP BY DAY_PARTITION, SCANNER_PACKAGE_NAME
ORDER BY DAY_PARTITION DESC, SCANNER_PACKAGE_NAME;
```

**Week-over-week comparison:**

```sql
WITH weekly AS (
    SELECT
        DATE_TRUNC('week', DAY_PARTITION::DATE) AS week_start,
        SUM(CRITICAL_RISK_COUNT + HIGH_RISK_COUNT) AS critical_high,
        SUM(MEDIUM_RISK_COUNT + LOW_RISK_COUNT) AS medium_low
    FROM snowflake.trust_center.time_series_daily_findings
    WHERE UPPER(COMPLETION_STATUS) = 'SUCCEEDED'
    GROUP BY week_start
)
SELECT
    week_start,
    critical_high,
    medium_low,
    critical_high - LAG(critical_high) OVER (ORDER BY week_start) AS critical_high_change,
    medium_low - LAG(medium_low) OVER (ORDER BY week_start) AS medium_low_change
FROM weekly
ORDER BY week_start DESC
LIMIT 8;  -- last 8 weeks
```

### Step 3: Present Results

Format the results clearly based on the analysis type:

**Example: Findings Summary**

```
## Trust Center Findings Summary (Last 7 Days)

**Total new findings:** 23

### Severity Distribution
| Severity | Count |
|----------|-------|
| Critical | 2     |
| High     | 5     |
| Medium   | 12    |
| Low      | 4     |

### Top Scanners with Findings
| Scanner | Critical | High | Medium | Low |
|---------|----------|------|--------|-----|
| Network Security Scanner | 1 | 3 | 5 | 2 |
| Access Control Scanner | 1 | 2 | 7 | 2 |
```

**Example: Category Analysis**

```
## Findings by Security Category

Based on scanner descriptions, findings are grouped into:

### Access Control (15 findings)
- Authentication Scanner: 8 findings (2 Critical)
- Privilege Scanner: 7 findings (1 High)

### Network Security (5 findings)
- Network Policy Scanner: 5 findings (1 High)

### Data Protection (3 findings)
- Encryption Scanner: 3 findings (all Medium)
```

**Example: Resolved Findings**

```
## Security Improvements (Last 7 Days)

**Resolved findings:** 12

### Scanners with No Recent Issues
These scanners had findings that are now resolved with no new detections:
| Scanner | Status |
|---------|--------|
| Password Policy Scanner | ✅ Improved |
| MFA Enforcement Scanner | ✅ Improved |
```

**Example: Scanner Frequency Analysis**

```
## Scanner Frequency Optimization

### Scanners Running Too Frequently
These scanners run often but find no issues - consider reducing frequency:

| Scanner | Runs (30d) | Findings | Recommendation |
|---------|------------|----------|----------------|
| Unused Feature Scanner | 30 | 0 | Reduce to weekly |
| Legacy Config Scanner | 28 | 0 | Reduce to weekly |

### Scanners That Should Run More Often
These scanners find critical issues but run infrequently:

| Scanner | Critical/High Findings | Last Run | Recommendation |
|---------|------------------------|----------|----------------|
| Access Audit Scanner | 5 | 45 days ago | Increase to weekly |
| Privilege Review Scanner | 3 | 38 days ago | Increase to weekly |
```

**Example: Trend Analysis**

```
## Findings Trend (Last 30 Days)

### Daily Summary
| Date | Critical | High | Medium | Low | Compliant |
|------|----------|------|--------|-----|-----------|
| 2026-02-06 | 2 | 5 | 12 | 4 | 30 |
| 2026-02-05 | 2 | 5 | 13 | 4 | 29 |
| 2026-02-04 | 3 | 6 | 13 | 4 | 28 |
| ... | ... | ... | ... | ... | ... |

### Week-over-Week
| Week | Critical+High | Change | Medium+Low | Change |
|------|--------------|--------|------------|--------|
| Feb 3 | 7 | -2 | 16 | -1 |
| Jan 27 | 9 | +1 | 17 | 0 |
| Jan 20 | 8 | -3 | 17 | -2 |

Trend: Security posture is improving — critical+high findings
decreased from 8 to 7 over the past 3 weeks.
```

### Step 4: Offer Next Steps

After presenting the analysis, offer actionable next steps based on what was shown:

**After findings summary:**
```
Would you like to:
1. See details of Critical/High severity findings?
2. Drill into a specific scanner's findings?
3. Get remediation guidance for specific findings?
4. Analyze findings by category?
5. See findings trend over time?
```

**After category analysis:**
```
Would you like to:
1. Drill into a specific category?
2. See remediation guidance for a category?
3. View scanner frequency optimization?
```

**After resolved findings:**
```
Would you like to:
1. See what actions resolved these findings?
2. Compare to currently active findings?
3. Identify recurring issues?
```

**After scanner frequency analysis:**
```
Would you like to:
1. Get specific recommendations for a scanner?
2. See the findings history for a scanner?
3. Review scanner configuration options?
```

**⚠️ STOP**: Wait for user to indicate next action.

## Stopping Points

- ✋ Step 1: If user intent is unclear, ask for clarification
- ✋ Step 4: After presenting any analysis, wait for user's next action

## Output

- Summary of findings count and severity distribution
- Optional: Detailed breakdown by scanner
- Optional: Findings grouped by security category
- Optional: Resolved findings and security improvements
- Optional: Scanner frequency optimization recommendations
- Optional: Specific finding details with remediation guidance
- Optional: Findings trend over time (daily/weekly) with posture assessment

## Troubleshooting

**No results returned:**
- The account may have no Trust Center findings
- Trust Center scanners may not be enabled
- Check if the view is accessible: `DESCRIBE VIEW snowflake.trust_center.findings;`

**Permission denied:**
- User needs `trust_center_admin` or `trust_center_viewer` application role to view findings

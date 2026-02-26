---
name: trust-center-scanner-analysis
description: "Analyze Trust Center scanners and scanner packages in Snowflake. Use when users ask about: scanners, scanner packages, scanner coverage, disabled scanners, scanner schedules, scanner categories, CIS benchmarks, Security Essentials, Threat Intelligence, or want to understand their Trust Center scanner configuration."
---

# Trust Center Scanner Analysis

Helps users understand, categorize, and optimize the Trust Center scanners configured in their Snowflake account.

## Background

Trust Center scanners are the smallest unit of Snowflake's detection/vulnerability ecosystem. Each scanner checks a specific area or configuration in the customer's Snowflake account for security issues.

**Scanner types:** Scanners produce two types of findings:
- **Vulnerability** - Persistent configuration issues (e.g., CIS Benchmark checks). Remediation is a specific config change.
- **Detection** - Event-based threat detections (e.g., unusual logins, admin privilege grants). Remediation requires investigation.

**Cost model:** Scanner packages and their scanners are pre-installed in every Snowflake account at no cost. Packages/scanners only incur credit costs when they are enabled and actively running. Simply having them installed (disabled) is free.

**Major Scanner Packages (pre-installed in every account):**

| Package | Description | Default Schedule | Schedule Configurable? | Cost |
|---------|-------------|-----------------|----------------------|------|
| Security Essentials | Complimentary scanner package for Snowflake-recommended checks | Monthly | No (fixed monthly schedule, but on-demand runs can be triggered) | Default monthly run is free (covered by Snowflake). Ad-hoc runs incur credits. |
| CIS Benchmarks | Scanners based on the Snowflake CIS Benchmark | Daily | Yes (package and individual scanner schedules) | Credits consumed per scan |
| Threat Intelligence | Detection scanners for unauthorized access risks | Daily/event-driven | Yes (package and individual scanner schedules) | Credits consumed per scan |

Additional packages may also exist (e.g., `APPLICATION_SECURITY` for native app vulnerabilities, or custom scanner packages). Query `snowflake.trust_center.scanner_packages` for the full list.

## When to Use

- User asks about Trust Center scanners or scanner packages
- User wants to know which scanners are enabled or disabled
- User asks about scanner schedules or frequency
- User wants to categorize scanners by security domain
- User asks "what scanners do I have?" or "what security checks are running?"
- User wants to identify gaps in scanner coverage
- User asks about CIS Benchmarks, Security Essentials, or Threat Intelligence
- User wants to optimize scanner schedules or notifications

## When NOT to Use

- User asks about specific findings from scanners (use findings-analysis skill)
- User wants to enable/disable scanners or change schedules/notifications (use api-management skill)

## Data Sources

### Scanners View

All scanners are accessible in `snowflake.trust_center.scanners`.

**Key columns:**

| Column | Type | Description |
|--------|------|-------------|
| `NAME` | varchar | Name of the scanner |
| `ID` | varchar | Unique ID for the scanner (aliased from `scanner_id`) |
| `SHORT_DESCRIPTION` | varchar | Scanner short description |
| `DESCRIPTION` | varchar | Full description of the scanner |
| `SCANNER_PACKAGE_ID` | varchar | Unique ID for the scanner package |
| `STATE` | varchar | `TRUE` = enabled, `FALSE` or NULL = not enabled (case may vary — use `UPPER()` in comparisons) |
| `SCHEDULE` | varchar | Cron schedule (e.g., `USING CRON 7 6 * * 2 America/Los_Angeles`). NULL for event-driven scanners. |
| `NOTIFICATION` | varchar | JSON object with keys: `NOTIFY_ADMINS` (TRUE/FALSE), `SEVERITY_THRESHOLD`, `USERS` (array). Empty `{}` means no notification configured. |
| `LAST_SCAN_TIMESTAMP` | timestamp_ltz | When the scanner last completed a scan. NULL for event-driven scanners or scanners that haven't run yet. |

**Scanner execution types:**
- **Scheduled scanners** - Have a `SCHEDULE` value (cron expression). Run periodically.
- **Event-driven scanners** - Have no `SCHEDULE` (NULL). Trigger on relevant events. These will also have NULL `LAST_SCAN_TIMESTAMP` even when enabled — this is normal.

Additional columns exist for extension/plugin scanners (e.g., `SOURCE_DATABASE_ID`, `SOURCE_DATABASE`, `EXTENSION_ID`, `EXTENSION_NAME`, `SCANNER_PACKAGE_SOURCE_TYPE`, `SCANNER_PACKAGE_SOURCE`). These are relevant for third-party marketplace scanner packages and are typically NULL for built-in scanners.

### Scanner Packages View

Scanner packages are accessible in `snowflake.trust_center.scanner_packages`.

**Key columns:**

| Column | Type | Description |
|--------|------|-------------|
| `NAME` | varchar | Name of the scanner package |
| `ID` | varchar | Unique ID for the scanner package (aliased from `scanner_package_id`) |
| `DESCRIPTION` | varchar | Description of the scanner package |
| `DEFAULT_SCHEDULE` | varchar | Default schedule as per the package manifest |
| `STATE` | varchar | `TRUE` = enabled, `FALSE` or NULL = not enabled (case may vary — use `UPPER()` in comparisons) |
| `SCHEDULE` | varchar | Current active schedule. May differ from `DEFAULT_SCHEDULE` if user customized it (CIS Benchmarks and Threat Intelligence are configurable; Security Essentials is not). |
| `NOTIFICATION` | varchar | JSON object with keys: `NOTIFY_ADMINS`, `SEVERITY_THRESHOLD`, `USERS`. Package-level notification config. |
| `LAST_ENABLED_TIMESTAMP` | timestamp_ltz | When the package was last enabled |
| `LAST_DISABLED_TIMESTAMP` | timestamp_ltz | When the package was last disabled |

Additional columns exist for extension/plugin packages (e.g., `PROVIDER`, `SOURCE_DATABASE_ID`, `SOURCE_DATABASE`, `EXTENSION_ID`, `EXTENSION_NAME`, `SCANNER_PACKAGE_SOURCE_TYPE`, `SCANNER_PACKAGE_SOURCE`). These are relevant for third-party marketplace scanner packages.

**Required roles:** `trust_center_admin` or `trust_center_viewer`.

## Workflow

### Step 1: Understand User Intent

Determine what the user wants to know:

1. **Scanner inventory** - What scanners exist and their status?
2. **Category analysis** - Group scanners by security domain
3. **Disabled scanner review** - Important scanners that aren't enabled
4. **Frequency analysis** - Scanners that run too infrequently
5. **Coverage gap analysis** - Security domains with no scanner coverage
6. **Notification recipients audit** - Scanners without notification recipients
7. **Scanner health check** - Enabled scanners that haven't run recently

**Ask if unclear:**
```
What would you like to know about your Trust Center scanners?
1. Scanner inventory and status overview
2. Categorize scanners by security domain
3. Find important scanners that aren't enabled
4. Find scanners that run too infrequently
5. Identify coverage gaps
6. Audit notification recipients
7. Scanner health check (enabled but not running)
8. All of the above
```

### Step 2: Query Scanner Data

Based on user intent, run the appropriate query.

**Full scanner inventory with package info:**

```sql
SELECT
    s.NAME,
    s.ID,
    s.SHORT_DESCRIPTION,
    s.DESCRIPTION,
    s.SCANNER_PACKAGE_ID,
    sp.NAME AS PACKAGE_NAME,
    s.STATE,
    s.SCHEDULE,
    s.NOTIFICATION,
    s.LAST_SCAN_TIMESTAMP
FROM snowflake.trust_center.scanners s
LEFT JOIN snowflake.trust_center.scanner_packages sp
    ON s.SCANNER_PACKAGE_ID = sp.ID
ORDER BY sp.NAME, s.NAME;
```

**Scanner status summary by package:**

```sql
SELECT
    sp.NAME AS PACKAGE_NAME,
    s.STATE AS SCANNER_STATE,
    s.SCHEDULE AS SCANNER_SCHEDULE,
    COUNT(*) AS scanner_count
FROM snowflake.trust_center.scanners s
LEFT JOIN snowflake.trust_center.scanner_packages sp
    ON s.SCANNER_PACKAGE_ID = sp.ID
GROUP BY ALL
ORDER BY 1,2,3;
```

**Disabled scanners (candidates to enable):**

```sql
SELECT
    s.NAME,
    s.ID,
    s.SHORT_DESCRIPTION,
    s.DESCRIPTION,
    sp.NAME AS PACKAGE_NAME
FROM snowflake.trust_center.scanners s
LEFT JOIN snowflake.trust_center.scanner_packages sp
    ON s.SCANNER_PACKAGE_ID = sp.ID
WHERE (s.STATE IS NULL OR UPPER(s.STATE) != 'TRUE') -- scanner state can be TRUE/FALSE/null, only TRUE indicates scanner enabled
ORDER BY sp.NAME, s.NAME;
```

**Scheduled scanners that ran too infrequently (last scan older than 30 days):**

```sql
SELECT
    s.NAME,
    s.ID,
    s.SHORT_DESCRIPTION,
    sp.NAME AS PACKAGE_NAME,
    s.STATE,
    s.SCHEDULE,
    s.LAST_SCAN_TIMESTAMP,
    DATEDIFF('day', s.LAST_SCAN_TIMESTAMP, CURRENT_TIMESTAMP()) AS days_since_last_scan
FROM snowflake.trust_center.scanners s
LEFT JOIN snowflake.trust_center.scanner_packages sp
    ON s.SCANNER_PACKAGE_ID = sp.ID
WHERE UPPER(s.STATE) = 'TRUE'
  AND s.SCHEDULE IS NOT NULL        -- Exclude event-driven scanners
  AND s.LAST_SCAN_TIMESTAMP IS NOT NULL
  AND DATEDIFF('day', s.LAST_SCAN_TIMESTAMP, CURRENT_TIMESTAMP()) > 30
ORDER BY days_since_last_scan DESC;
```

**Enabled scheduled scanners that have NEVER run (potential health issue):**

```sql
SELECT
    s.NAME,
    s.ID,
    s.SHORT_DESCRIPTION,
    sp.NAME AS PACKAGE_NAME,
    s.STATE,
    s.SCHEDULE
FROM snowflake.trust_center.scanners s
LEFT JOIN snowflake.trust_center.scanner_packages sp
    ON s.SCANNER_PACKAGE_ID = sp.ID
WHERE UPPER(s.STATE) = 'TRUE'
  AND s.SCHEDULE IS NOT NULL        -- Exclude event-driven scanners (NULL schedule + NULL last_scan is normal)
  AND s.LAST_SCAN_TIMESTAMP IS NULL
ORDER BY sp.NAME, s.NAME;
```

**Enabled scanners without notification recipients configured:**

A notification has recipients if it notifies admins OR specifies custom users:
- **Notify admins:** `{"NOTIFY_ADMINS":"TRUE","SEVERITY_THRESHOLD":"CRITICAL","USERS":[]}`
- **Notify custom users:** `{"NOTIFY_ADMINS":"FALSE","SEVERITY_THRESHOLD":"MEDIUM","USERS":["\"snow@flake.com\"","SNOWFLAKE","ADMIN_ABC"]}`

A notification has NO recipients if it is NULL, empty `{}`, or has `NOTIFY_ADMINS=FALSE` with an empty `USERS` array.

```sql
SELECT
    s.NAME,
    s.ID,
    s.SHORT_DESCRIPTION,
    sp.NAME AS PACKAGE_NAME,
    s.STATE,
    s.NOTIFICATION
FROM snowflake.trust_center.scanners s
LEFT JOIN snowflake.trust_center.scanner_packages sp
    ON s.SCANNER_PACKAGE_ID = sp.ID
WHERE UPPER(s.STATE) = 'TRUE'
  AND (
    s.NOTIFICATION IS NULL
    OR s.NOTIFICATION = '{}'
    OR (
      UPPER(PARSE_JSON(s.NOTIFICATION):NOTIFY_ADMINS::STRING) = 'FALSE'
      AND ARRAY_SIZE(PARSE_JSON(s.NOTIFICATION):USERS) = 0
    )
  )
ORDER BY sp.NAME, s.NAME;
```

**All scanner descriptions for categorization:**

```sql
SELECT
    s.NAME,
    s.ID,
    s.SHORT_DESCRIPTION,
    s.DESCRIPTION,
    sp.NAME AS PACKAGE_NAME,
    s.STATE
FROM snowflake.trust_center.scanners s
LEFT JOIN snowflake.trust_center.scanner_packages sp
    ON s.SCANNER_PACKAGE_ID = sp.ID
ORDER BY sp.NAME, s.NAME;
```

After running the query above, use the `DESCRIPTION` and `SHORT_DESCRIPTION` text to classify each scanner into security domains. This is an LLM classification task — read the description and assign the most appropriate domain. The list below is not exhaustive; derive domains from the actual scanner descriptions. Example domains:
- **Network Security** - Network policies, IP allow-lists, connectivity restrictions
- **Identity & Access Management** - Authentication, MFA, passwords, roles, privileges
- **Data Protection** - Encryption, masking, data sharing, data access controls
- **Configuration Management** - Account settings, parameters, best practices
- **Monitoring & Logging** - Audit logging, activity monitoring, alerting
- **Compliance** - Regulatory requirements, CIS benchmark adherence

Present the categorization as a table grouped by domain, noting which scanners are enabled vs disabled in each category.

### Step 3: Present Results

Format results based on the analysis type.

**Example: Scanner Inventory**

```
## Trust Center Scanner Overview

### Scanner Packages
| Package | Total Scanners | TRUE (enabled) | FALSE (disabled) | Default Schedule |
|---------|---------------|----------------|------------------|-----------------|
| Security Essentials | 5 | 5 | 0 | Monthly |
| CIS Benchmarks | 30 | 27 | 3 | Daily |
| Threat Intelligence | 10 | 8 | 2 | Varies (scheduled/event-driven) |

### Summary
- **Total scanners:** 45
- **Enabled (TRUE):** 40 (89%)
- **Disabled (FALSE):** 5 (11%)
```

**Example: Category Analysis**

```
## Scanners by Security Domain

### Network Security (8 scanners)
| Scanner | Package | State | Last Scan |
|---------|---------|-------|-----------|
| 3.1 Account-level network policy | CIS Benchmarks | TRUE | 3 days ago |
| 3.1 Account-level network policy | Security Essentials | TRUE | 24 days ago |
| ... | ... | ... | ... |

### Identity & Access Management (15 scanners)
| Scanner | Package | State | Last Scan |
|---------|---------|-------|-----------|
| 1.4 MFA for human users | Security Essentials | TRUE | 24 days ago |
| 1.5 Minimum password length | CIS Benchmarks | FALSE | 31 days ago |
| ... | ... | ... | ... |

### Coverage Summary
| Domain | Total | Enabled (TRUE) | Gap? |
|--------|-------|----------------|------|
| Network Security | 8 | 6 | No |
| Identity & Access Management | 15 | 13 | Partial |
| Data Protection | 5 | 5 | No |
| Monitoring & Logging | 3 | 1 | Yes - review |
```

**Example: Disabled Scanner Review**

```
## Important Disabled Scanners

These scanners are currently disabled but may provide valuable security coverage:

### High Priority (recommend enabling)
| Scanner | Package | What It Checks |
|---------|---------|---------------|
| MFA Policy Scanner | CIS Benchmarks | Ensures MFA is enforced for all users |
| Network Policy Scanner | CIS Benchmarks | Validates network access restrictions |

### Medium Priority
| Scanner | Package | What It Checks |
|---------|---------|---------------|
| ... | ... | ... |

Note: All scanners are pre-installed for free. Enabling them incurs credit
costs per scan run. Security Essentials' default monthly run is free (covered
by Snowflake), but ad-hoc runs incur credits. CIS Benchmark and Threat
Intelligence scanner runs always consume credits.
```

**Example: Scanner Health Check**

```
## Scanner Health Check

### Scheduled Scanners That Haven't Run Recently (STATE=TRUE)
| Scanner | Package | Days Since Last Scan | Schedule |
|---------|---------|---------------------|----------|
| 4.9 Tri-Secret Secure | CIS Benchmarks | 80 | Weekly |
| 1.5 Minimum password length | CIS Benchmarks | 31 | Weekly |

### Scheduled Scanners That Have Never Run (STATE=TRUE)
| Scanner | Package | Schedule |
|---------|---------|----------|
| 1.18 PAT network policy | CIS Benchmarks | Weekly |

### Event-Driven Scanners (no schedule — this is normal)
| Scanner | Package | State |
|---------|---------|-------|
| Sensitive Parameter Protection | Threat Intelligence | TRUE |
| Dormant User Login | Threat Intelligence | TRUE |
| Authentication Policy Changes | Threat Intelligence | TRUE |

Note: Event-driven scanners have no schedule and no LAST_SCAN_TIMESTAMP.
They trigger on relevant account events. This is expected behavior.

Recommendation: Investigate why scheduled scanners above are not executing
as configured.
```

### Step 4: Offer Next Steps

After presenting the analysis, offer actionable next steps:

**After scanner inventory:**
```
Would you like to:
1. Categorize scanners by security domain?
2. Review disabled scanners that should be enabled?
3. Check scanner health and run frequency?
4. Audit notification recipients?
```

**After category analysis:**
```
Would you like to:
1. See recommendations for coverage gaps?
2. Review disabled scanners in a specific category?
3. Analyze scanner run frequency?
```

**After disabled scanner review:**
```
Would you like to:
1. Understand the cost implications of enabling more scanners?
2. See which security domains would benefit most from enabling scanners?
3. Check the findings from currently enabled scanners?
```

**After scanner health check:**
```
Would you like to:
1. Investigate specific scanners that aren't running?
2. Review scanner schedule configuration?
3. Check if scanners without notifications should have them?
```

**STOP**: Wait for user to indicate next action.

## Stopping Points

- Step 1: If user intent is unclear, ask for clarification
- Step 4: After presenting any analysis, wait for user's next action

## Output

- Summary of scanner packages and their status
- Optional: Scanner categorization by security domain
- Optional: List of important disabled scanners with recommendations
- Optional: Scanners running too infrequently with schedule recommendations
- Optional: Coverage gap analysis across security domains
- Optional: Notification recipients audit results
- Optional: Scanner health check (enabled but not running)

## Troubleshooting

**No results returned:**
- Trust Center may not be enabled on the account
- Check if the view is accessible: `DESCRIBE VIEW snowflake.trust_center.scanners;`

**Permission denied:**
- User needs `trust_center_admin` or `trust_center_viewer` application role to view scanners and scanner packages

**Scanner shows STATE=TRUE but LAST_SCAN_TIMESTAMP is NULL:**
- If `SCHEDULE` is also NULL: this is an **event-driven scanner** — no schedule and no last scan is normal. It triggers on relevant account events.
- If `SCHEDULE` has a value: the scanner was recently enabled and hasn't had its first scheduled run yet. Check the cron schedule to determine when the next run is expected.

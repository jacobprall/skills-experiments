---
name: trust-center-finding-remediation
description: "Help users understand and remediate Trust Center security findings. Use when users ask about: fixing a finding, remediating a vulnerability, understanding a specific finding, at-risk entities, suggested actions, how to fix a security issue detected by Trust Center, or want step-by-step remediation guidance."
---

# Trust Center Finding Remediation

Helps users understand specific Trust Center findings and guides them through actual remediation — making the correct configuration changes or account management actions to eliminate vulnerabilities or prevent detections/alerts.

**Important:** Remediation means fixing the underlying issue (e.g., altering a user, setting a parameter, creating a network policy). It is NOT the same as resolving/marking a finding as resolved in Trust Center, which is a separate Trust Center feature that only changes the finding's state without fixing the root cause.

## When to Use

- User asks how to fix or remediate a Trust Center finding
- User asks about a specific finding's details, at-risk entities, or suggested actions
- User wants to understand the impact of remediating a finding
- User asks "how do I fix this security issue?"
- User wants to prioritize which findings to remediate first
- User wants help generating remediation SQL for at-risk entities

## When NOT to Use

- User wants to mark/resolve a finding's state (use api-management skill)
- User wants a high-level summary of all findings (use findings-analysis skill)
- User wants to understand scanner configuration (use scanner-analysis skill)
- User wants to enable/disable scanners (use api-management skill)

## Data Source

All findings are in `snowflake.trust_center.findings`.

**Key columns for remediation:**

| Column | Type | Description |
|--------|------|-------------|
| `FINDING_IDENTIFIER` | varchar | Unique ID for the finding |
| `SCANNER_NAME` | varchar | Name of the scanner that detected the finding |
| `SCANNER_DESCRIPTION` | varchar | What the scanner checks for |
| `SCANNER_SHORT_DESCRIPTION` | varchar | Brief scanner description (useful for categorization) |
| `SCANNER_TYPE` | varchar | `Vulnerability` (config issues) or `Detection` (event-based threats) |
| `SCANNER_ID` | varchar | Unique identifier for the scanner |
| `SCANNER_PACKAGE_ID` | varchar | Unique identifier for the scanner package |
| `SCANNER_PACKAGE_NAME` | varchar | Package containing the scanner (e.g., Security Essentials, CIS Benchmarks) |
| `SEVERITY` | varchar | `Critical`, `High`, `Medium`, `Low` |
| `SUGGESTED_ACTION` | varchar | Detailed markdown remediation steps with SQL examples |
| `IMPACT` | varchar | Side effects and risks of applying the remediation |
| `AT_RISK_ENTITIES` | array | JSON array of affected entities with details |
| `TOTAL_AT_RISK_COUNT` | number | Count of affected entities (0 = no issues found) |
| `STATE` | varchar | NULL, Open, or Resolved (case may vary — always use `UPPER()` in comparisons) |
| `STATE_LAST_MODIFIED_ON` | timestamp | When finding state last changed |
| `CREATED_ON` | timestamp | When the finding was first detected |
| `START_TIMESTAMP` | timestamp | When the scanner run started |
| `END_TIMESTAMP` | timestamp | When the scanner run completed |
| `COMPLETION_STATUS` | varchar | `SUCCEEDED` if scanner completed successfully |
| `METADATA` | object | Optional custom metadata from the scanner |

**AT_RISK_ENTITIES structure:** Each element is a JSON object with:
- `entity_id` - Unique identifier for the entity
- `entity_name` - Human-readable name
- `entity_object_type` - Type (not exhaustive): `PARAMETER`, `USER`, `TASK`, `PROCEDURE`, `NETWORK_POLICY`, `ACCOUNT`
- `entity_detail` - Object with type-specific details (e.g., current parameter value, role assignments)

**Scanner types determine remediation approach:**
- **`Vulnerability`** — A persistent configuration issue in the account (e.g., a missing network policy, weak encryption setting). Remediation is a specific configuration change.
- **`Detection`** — A threat event or anomaly was detected in the account by a scanner (e.g., unusual login activity, admin privilege escalation). Remediation requires investigation to determine if the activity is legitimate or malicious. `Alert` and `Threat` are legacy names for the same concept — treat them identically to `Detection`.
- **`NULL`** — Type not set. Treat as unknown; inspect the scanner description for context.

**Required roles:**

- `trust_center_admin` or `trust_center_viewer` for viewing findings
- `ACCOUNTADMIN`, `SECURITYADMIN`, or roles with necessary privileges for executing remediation SQL

## Workflow

### Step 1: Identify the Finding

If the user specifies a finding, query it directly. Otherwise, show open findings prioritized by severity.

**Get open findings prioritized by severity and at-risk count:**

```sql
SELECT
    FINDING_IDENTIFIER,
    SCANNER_NAME,
    SCANNER_SHORT_DESCRIPTION,
    SCANNER_TYPE,
    SCANNER_PACKAGE_NAME,
    SEVERITY,
    TOTAL_AT_RISK_COUNT,
    STATE,
    CREATED_ON
FROM snowflake.trust_center.findings
WHERE UPPER(STATE) = 'OPEN'
  AND TOTAL_AT_RISK_COUNT > 0
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
LIMIT 20;
```

Present the results and ask the user which finding they want to remediate.

**STOP**: Wait for user to select a finding.

### Step 2: Get Full Finding Details

Once the user selects a finding, retrieve the complete details:

```sql
SELECT
    FINDING_IDENTIFIER,
    SCANNER_NAME,
    SCANNER_DESCRIPTION,
    SCANNER_SHORT_DESCRIPTION,
    SCANNER_TYPE,
    SCANNER_ID,
    SCANNER_PACKAGE_ID,
    SCANNER_PACKAGE_NAME,
    SEVERITY,
    SUGGESTED_ACTION,
    IMPACT,
    TOTAL_AT_RISK_COUNT,
    AT_RISK_ENTITIES,
    STATE,
    STATE_LAST_MODIFIED_ON,
    CREATED_ON,
    START_TIMESTAMP,
    END_TIMESTAMP,
    COMPLETION_STATUS,
    METADATA
FROM snowflake.trust_center.findings
WHERE FINDING_IDENTIFIER = '<finding_identifier>'
ORDER BY CREATED_ON DESC
LIMIT 1;
```

### Step 3: Present Finding Context

Present the finding in a structured format:

```
## Finding: <SCANNER_NAME>

**Severity:** <SEVERITY>
**Type:** <SCANNER_TYPE>
**Status:** <STATE>
**Detected:** <CREATED_ON>
**Number of At-Risk Entities:** <TOTAL_AT_RISK_COUNT>

### What This Scanner Checks
<SCANNER_DESCRIPTION>

### Affected Entities
<Parse AT_RISK_ENTITIES and display up to 20 entities with their details>
<If TOTAL_AT_RISK_COUNT > 20, add: "Showing 20 of <TOTAL_AT_RISK_COUNT> entities. <N> entities not displayed. Would you like to see more?">

### Remediation Impact
<IMPACT>
```

**Important guidance for presenting AT_RISK_ENTITIES:**

Based on `entity_object_type`, present details appropriately. Common types (not exhaustive — other types may appear):

- **PARAMETER**: Show parameter name and current value (`entity_detail.val`). Fix is typically `ALTER ACCOUNT SET <param> = <correct_value>;`
- **USER**: Show user name, email, relevant properties. Fix involves `ALTER USER` commands.
- **TASK**: Show task name, owning role. Fix involves `GRANT OWNERSHIP` to a custom role.
- **PROCEDURE**: Show procedure name, owning role. Fix involves `GRANT OWNERSHIP` to a custom role.
- **NETWORK_POLICY**: Show policy status. Fix involves `CREATE NETWORK POLICY` and `ALTER ACCOUNT SET`.
- **ACCOUNT**: Show account-level context. Fix depends on the specific finding.

For any other `entity_object_type`, inspect the `entity_detail` object and present relevant fields. Use the `SUGGESTED_ACTION` for remediation guidance.

### Step 4: Present Remediation Steps

Present the `SUGGESTED_ACTION` from the finding, which contains detailed markdown with SQL.

**For Vulnerability findings (actionable fixes):**

1. Present the SUGGESTED_ACTION content, and add context explaining **why** the action is needed and **what it actually does** so the user understands the purpose before taking action
2. If `AT_RISK_ENTITIES` contains specific entities, generate entity-specific SQL by substituting entity names into the template SQL from SUGGESTED_ACTION. **Cap at 20 examples** — if there are more, note how many remain and offer to show additional batches
3. **Present the generated SQL but DO NOT execute it without explicit user approval**

**Example: Generating entity-specific SQL**

If the finding is CIS 1.12 (users with ACCOUNTADMIN as default role) and AT_RISK_ENTITIES contains:
```json
{"entity_name": "ADMIN_TC", "entity_detail": {"default_role": "ACCOUNTADMIN"}}
```

Generate:
```sql
-- Fix for user ADMIN_TC (current default role: ACCOUNTADMIN)
ALTER USER ADMIN_TC SET DEFAULT_ROLE = '<appropriate_role>';
```

Ask the user what role to set for each user.

**For Detection findings (investigation needed):**

1. Present the SUGGESTED_ACTION which typically includes investigative queries
2. Help the user run the investigation queries
3. Help interpret the results
4. Only suggest remediation actions (like disabling a user) after the user confirms the activity is malicious

**STOP**: Present the remediation plan and wait for user approval before generating any executable SQL.

### Step 5: Generate Remediation SQL

After user approval, generate ready-to-execute SQL based on the finding type:

**Simple parameter fixes** (e.g., ALTER ACCOUNT SET):
```sql
-- Remediation for: <SCANNER_NAME>
-- Finding: <FINDING_IDENTIFIER>
<SQL from SUGGESTED_ACTION with actual values substituted>
```

**Per-entity fixes** (loop through AT_RISK_ENTITIES):
```sql
-- Remediation for: <SCANNER_NAME>
-- Entity: <entity_name> (<entity_object_type>)
<SQL from SUGGESTED_ACTION with entity name substituted>
```

**STOP**: Present the SQL and get explicit confirmation before the user executes it.

### Step 6: Verify Remediation

After the user executes the remediation:

1. Suggest re-running the scanner to verify the fix:
```sql
CALL snowflake.trust_center.execute_scanner('<SCANNER_PACKAGE_ID>', '<SCANNER_ID>');
```

2. After the scanner completes, check if the finding is resolved:
```sql
SELECT
    FINDING_IDENTIFIER,
    STATE,
    TOTAL_AT_RISK_COUNT,
    CREATED_ON
FROM snowflake.trust_center.findings
WHERE FINDING_IDENTIFIER = '<finding_identifier>'
ORDER BY CREATED_ON DESC
LIMIT 1;
```

3. If `TOTAL_AT_RISK_COUNT` drops to 0 or `STATE` changes to `RESOLVED`, the remediation was successful.

### Step 7: Summarize Actions for Audit

After remediation is complete (or the user finishes their session), present an action log summary:

```
## Remediation Action Log

**Finding:** <SCANNER_NAME> (<FINDING_IDENTIFIER>)
**Severity:** <SEVERITY>
**Date:** <current date>

### Actions Suggested
<List all remediation SQL or investigation steps that were presented to the user>

### Actions Taken
<List only the actions the user confirmed and executed>

### Actions Skipped
<List any suggested actions the user chose not to take, with their reason if provided>

### Result
- **Before:** <TOTAL_AT_RISK_COUNT> at-risk entities
- **After:** <new count after verification, or "pending re-scan">
```

This summary helps the user maintain an audit trail of what was reviewed, what was changed, and what remains outstanding.

## Stopping Points

- Step 1: After listing findings, wait for user to select one
- Step 4: After presenting remediation plan, wait for approval
- Step 5: After generating SQL, wait for user to execute
- Step 6: After verification, offer next steps

## Safety Rules

- **NEVER execute remediation SQL without explicit user approval**
- **ALWAYS present IMPACT before remediation** — some fixes can break existing workflows
- **For Detection findings, ALWAYS investigate before suggesting remediation** — unusual activity may be legitimate
- **For entity-level fixes with many entities (>10), suggest batching** — present first few, ask user to review before generating the rest
- **Warn about high-impact changes:** Network policy changes can lock users out. Role revocations can break workflows. Parameter changes affect the entire account.

## Output

- Finding details with severity, description, and affected entities
- Remediation steps from SUGGESTED_ACTION
- Ready-to-execute SQL with entity-specific values substituted
- Verification steps to confirm successful remediation

## Troubleshooting

**No open findings with at-risk entities:**
- All findings may already be resolved
- Try: `SELECT DISTINCT STATE, COUNT(*) FROM snowflake.trust_center.findings GROUP BY STATE;`

**SUGGESTED_ACTION is empty or NULL:**
- Some scanners (especially event-driven) may not provide structured remediation steps
- Guide the user based on the SCANNER_DESCRIPTION instead

**Permission denied:**
- User needs `trust_center_admin` or `trust_center_viewer` application role to view findings
- Remediation SQL typically requires `ACCOUNTADMIN`, `SECURITYADMIN` or equivalent privileges

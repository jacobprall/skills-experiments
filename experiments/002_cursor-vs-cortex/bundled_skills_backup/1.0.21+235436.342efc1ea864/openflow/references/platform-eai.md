---
name: openflow-platform-eai
description: Set up External Access Integrations (EAI) and Network Rules for Openflow SPCS deployments. Enables Openflow Runtimes to communicate with external data sources.
---

# External Access Integrations (EAI)

External Access Integrations allow Openflow Runtimes to communicate with external services (databases, APIs, etc.) through Snowflake's network security layer.

**Note:** These operations modify Snowflake account state. Apply the Check-Act-Check pattern (see `references/core-guidelines.md`).

## SPCS Only

**This reference applies to SPCS (Snowflake-managed) deployments only.**

BYOC (Bring Your Own Cloud) deployments run in the customer's cloud account and have direct network access. They do not require EAI configuration.

Check your deployment type in the cache:

```bash
cat ~/.snowflake/cortex/memory/openflow_infrastructure_*.json | jq '.deployments[].deployment_type'
```

## Scope

- Network Rules and External Access Integrations for SPCS
- Enabling external connectivity for connectors and custom flows
- Does NOT apply to BYOC (which has direct network access)

## Prerequisites

**Runtime role is required.** Check the cache for your runtime role:

```bash
cat ~/.snowflake/cortex/memory/openflow_infrastructure_*.json | jq '.deployments[].runtimes[] | {name: .runtime_name, role: .runtime_role}'
```

| Result | Action |
|--------|--------|
| Shows runtime roles | Continue with EAI setup |
| No cache or missing roles | Load `references/setup-main.md` to run discovery |

## Required Privileges

Creating External Access Integrations requires:

- **CREATE INTEGRATION** privilege on the account
- **USAGE** privilege on any secret the integration uses
- **USAGE** privilege on the secret's schema

Roles that typically have these privileges:
- **SECURITYADMIN** - Recommended for EAI/Network Rule management
- **ACCOUNTADMIN** - Also works, but broader than needed

### Granting CREATE INTEGRATION

If the admin role lacks CREATE INTEGRATION, an ACCOUNTADMIN can grant it:

```sql
-- Run as ACCOUNTADMIN
GRANT CREATE INTEGRATION ON ACCOUNT TO ROLE <openflow_admin_role>;
```

## Tool Hierarchy

| Operation | Tool | Notes |
|-----------|------|-------|
| Create Network Rule | SQL | Snowflake account level |
| Create EAI | SQL | Snowflake account level |
| Attach EAI to Runtime | **UI Only** | Openflow Control Plane |

## Required Domains Reference

**Always fetch current required domains from Snowflake documentation:**

**URL:** https://docs.snowflake.com/en/user-guide/data-integration/openflow/setup-openflow-spcs-sf-allow-list

The agent should:
1. Fetch that page
2. Find the section for the specific connector
3. Extract the required domains
4. Generate the SQL using the templates below

## Workflow: Create EAI

**Execute these steps in order. Do NOT run concurrently.**

### Step 1: Create Network Rule

```sql
USE ROLE SECURITYADMIN;

CREATE NETWORK RULE <connector>_openflow_network_rule
  TYPE = HOST_PORT
  MODE = EGRESS
  VALUE_LIST = ('<domain1>:<port>', '<domain2>:<port>');
```

### Step 2: Verify Network Rule

**Do not proceed until this succeeds:**

```sql
DESCRIBE NETWORK RULE <connector>_openflow_network_rule;
```

| Result | Action |
|--------|--------|
| Returns rule details | Continue to Step 3 |
| Error | Check for typos, verify privileges |

### Step 3: Create External Access Integration

```sql
USE ROLE SECURITYADMIN;

CREATE EXTERNAL ACCESS INTEGRATION <connector>_openflow_eai
  ALLOWED_NETWORK_RULES = (<connector>_openflow_network_rule)
  ENABLED = TRUE
  COMMENT = 'External Access Integration for Openflow <Connector> connectivity';
```

### Step 4: Verify EAI

```sql
DESCRIBE INTEGRATION <connector>_openflow_eai;
```

### Step 5: Grant USAGE to Runtime Role

```sql
GRANT USAGE ON INTEGRATION <connector>_openflow_eai TO ROLE <runtime_role>;
```

Replace `<runtime_role>` with your SPCS runtime role from the cache.

### Step 6: Attach EAI via UI

1. Navigate to the **Openflow Control Plane**
2. Find the Runtime in the list
3. Click the vertical **"..."** menu
4. Select **"External access integrations"**
5. Select the EAI from the dropdown
6. Click **Save**

**Note:** Restarting the runtime is NOT required - changes apply immediately.

## Common Patterns

### Database Connectors (HOST_PORT Specific)

Database connectors require exact host:port specifications. The Network Rule controls both DNS resolution and TCP connectivity:

```sql
CREATE NETWORK RULE my_postgres_network_rule
  TYPE = HOST_PORT
  MODE = EGRESS
  VALUE_LIST = ('<customer-database-host>:<port>');
```

Default ports:
- PostgreSQL: 5432
- MySQL: 3306
- SQL Server: 1433

**Important:** Network Rules are HOST:PORT specific. If you see:
- **UnknownHostException** → Host not in any Network Rule (DNS blocked)
- **SocketTimeoutException** (after DNS passes) → Port not in Network Rule (TCP blocked)

### SaaS Connectors (Multiple Rules)

SaaS connectors typically need multiple endpoints for authentication, APIs, and data access. These often require wildcards.

**Wildcard Limitation:** Snowflake wildcards only match a **single subdomain level**. For example:
- `*.example.com` matches `api.example.com` but NOT `api.v2.example.com`
- `*.sharepoint.com` matches `contoso.sharepoint.com` but NOT `files.contoso.sharepoint.com`

If you need to match deeper subdomains, only use a wildcard at the top most element.

**Example: SharePoint**

```sql
-- Single rule with all required endpoints
CREATE NETWORK RULE sharepoint_network_rule
  TYPE = HOST_PORT
  MODE = EGRESS
  VALUE_LIST = (
    'login.microsoftonline.com:443',
    'login.microsoft.com:443',
    'graph.microsoft.com:443',
    '*.sharepoint.com:443'
  );

CREATE EXTERNAL ACCESS INTEGRATION sharepoint_eai
  ALLOWED_NETWORK_RULES = (sharepoint_network_rule)
  ENABLED = TRUE;
```

**Key Pattern:** Some connectors need multiple endpoint types, preferably in a single rule:
- **Authentication endpoints** - OAuth, login services
- **API endpoints** - Graph API, REST APIs
- **Data endpoints** - The actual service hosting user data

## SQL Reference

### Alter Existing Network Rule

```sql
USE ROLE SECURITYADMIN;

ALTER NETWORK RULE <existing_rule> SET
  VALUE_LIST = ('<existing_domain>', '<new_domain>');
```

### View Existing Rules

```sql
SHOW NETWORK RULES;
DESCRIBE NETWORK RULE <rule_name>;
```

## Troubleshooting

### "UnknownHostException" Error

**Cause:** Network Rule is missing the required domain, EAI not created, EAI not granted to the Runtime Role, or EAI not attached to Runtime.

**Resolution:**
1. Check the connector's required domains in the docs
2. Create/update the network rule
3. Create the EAI if missing
4. Grant USAGE to runtime role
5. Attach EAI to Runtime via UI

### UnknownHostException Despite Wildcard

**Symptom:** You have a wildcard like `*.example.com` but still get UnknownHostException for a host like `api.v2.example.com`.

**Cause:** Snowflake wildcards usually only match a single subdomain level. `*.example.com` matches `api.example.com` but NOT `api.v2.example.com` (two levels deep).

**Resolution:**
- Add explicit entries for deeper subdomains: `api.v2.example.com:443`
- Or add wildcards only at the top level: `*.v2.example.com:443`
- Check the actual hostname in the error message and add it explicitly if the pattern is unclear

### SQL Execution Fails with 404

**Cause:** Snowflake account identifier format may be incorrect.

- **Correct format:** `ORG-ACCOUNT` (e.g., `SFPSCOGS-MIGRATION_AWS_EAST`)
- **Probably incorrect:** Full URL format (e.g., `PTA96169.us-east-1.snowflakecomputing.com`)

### Verify EAI is Attached

Currently there's no CLI to check attached EAIs - use the Openflow Control Plane UI.

## Workflow Example

For a PostgreSQL connector at `aurora-postgres.example.com:5432`:

```sql
-- Step 1: Create Network Rule
USE ROLE SECURITYADMIN;
CREATE NETWORK RULE postgres_cdc_network_rule
  TYPE = HOST_PORT
  MODE = EGRESS
  VALUE_LIST = ('aurora-postgres.example.com:5432');

-- Step 2: Verify (run separately)
DESCRIBE NETWORK RULE postgres_cdc_network_rule;

-- Step 3: Create EAI (only after Step 2 succeeds)
CREATE EXTERNAL ACCESS INTEGRATION postgres_cdc_eai
  ALLOWED_NETWORK_RULES = (postgres_cdc_network_rule)
  ENABLED = TRUE;

-- Step 4: Verify
DESCRIBE INTEGRATION postgres_cdc_eai;

-- Step 5: Grant to runtime role
GRANT USAGE ON INTEGRATION postgres_cdc_eai TO ROLE <runtime_role>;

-- Step 6: Attach via UI (see above)
```

## Related References

- `references/setup-main.md` - Find runtime role via discovery
- `references/core-guidelines.md` - Deployment types (SPCS vs BYOC)

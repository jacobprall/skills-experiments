---
name: unitycatalog-catalog-integration-setup
description: "Setup and verify catalog integration for Unity Catalog. Triggers: create unity catalog integration, connect snowflake to databricks, setup unity catalog, configure databricks catalog integration, unity catalog iceberg, oauth unity catalog, bearer token unity catalog, PAT databricks snowflake, troubleshoot unity catalog integration, verify unity catalog connection, fix databricks connection, debug unity catalog iceberg."
---

# Unity Catalog Catalog Integration

Setup, verify, or troubleshoot a Snowflake catalog integration for Databricks Unity Catalog.

## Intent Routing (FIRST)

**Ask the user**:
```
What would you like to do?

A: Create a new catalog integration for Unity Catalog
   → Setup Snowflake to connect to Databricks Unity Catalog

B: Verify an existing catalog integration
   → Test connection and list namespaces/tables

C: Troubleshoot a catalog integration
   → Diagnose and fix connection issues
```

**Route based on response**:
- **A (Create)** → **Load** `setup/SKILL.md` then follow [Create Workflow](#create-workflow)
- **B (Verify)** → **Load** `verify/SKILL.md` then follow [Verify Workflow](#verify-workflow)
- **C (Troubleshoot)** → **Load** `references/troubleshooting.md` then follow [Troubleshoot Workflow](#troubleshoot-workflow)

---

## Create Workflow

> **⚠️ REQUIRED**: Load `setup/SKILL.md` FIRST before proceeding with this workflow.

Create a new catalog integration to connect Snowflake to Unity Catalog.

### Step 1: Prerequisites

Follow `setup/SKILL.md` to collect:

Collect one-by-one:
1. Confirm Unity Catalog setup exists
2. Authentication method (OAuth vs Bearer token/PAT)
3. Databricks workspace URL
4. Unity Catalog name
5. OAuth credentials OR Bearer token
6. Access delegation mode
7. External volume (if needed)
8. Connectivity type
9. Integration name

**⚠️ STOP**: Confirm prerequisites before proceeding

### Step 2: Create Integration

**Load** `create/SKILL.md` and follow its workflow:

1. Generate CREATE CATALOG INTEGRATION SQL
2. **⚠️ STOP**: Review SQL with user
3. Execute creation

### Step 3: Verify

→ Continue to [Verify Workflow](#verify-workflow)

---

## Verify Workflow

> **⚠️ REQUIRED**: Load `verify/SKILL.md` FIRST before proceeding with this workflow.

Verify an existing catalog integration is working correctly.

### Step V1: Get Integration Name

**Ask**: "What is the name of your catalog integration?"

If user doesn't know:
```sql
SHOW CATALOG INTEGRATIONS;
```

### Step V2: Check Integration Status

Follow `verify/SKILL.md` which loads the shared verification workflow.

Run verification checks:
```sql
-- Check integration exists and is enabled
SHOW CATALOG INTEGRATIONS LIKE '<integration_name>';

-- Verify connection
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('<integration_name>');

-- List namespaces (Unity Catalog schemas)
SELECT SYSTEM$LIST_NAMESPACES_FROM_CATALOG('<integration_name>');

-- List tables in a namespace
SELECT SYSTEM$LIST_ICEBERG_TABLES_FROM_CATALOG('<integration_name>', '<namespace>');
```

### Step V3: Report Results

**If all checks pass**:
```
✅ Integration verified successfully
- Status: ENABLED
- Connection: Working
- Namespaces: <count> discovered
- Tables: Accessible
```

**If any check fails** → Continue to [Troubleshoot Workflow](#troubleshoot-workflow)

### Step V4: Next Steps

**If verification succeeded**:

**Load** `shared/next-steps/SKILL.md` (path: `../shared/next-steps/SKILL.md`)

Guide user through options for accessing catalog tables:
- Option A: Create individual Iceberg tables
- Option B: Create catalog-linked database (recommended)

---

## Troubleshoot Workflow

> **⚠️ REQUIRED**: Load `references/troubleshooting.md` to have error patterns and solutions available.

Diagnose and fix issues with an existing catalog integration.

### Step T1: Get Integration Name

**Ask**: "What is the name of your catalog integration?"

### Step T2: Gather Error Information

**Ask**: "What error or issue are you experiencing?"

Common symptoms:
- Integration creation failed
- Verification returns error
- Cannot list namespaces
- Cannot see tables
- OAuth/authentication errors
- Token expired

### Step T3: Diagnose

Use error patterns from `references/troubleshooting.md` to diagnose.

Run diagnostics:
```sql
-- Check integration details
DESC CATALOG INTEGRATION <integration_name>;

-- Test connection
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('<integration_name>');
```

### Step T4: Match Error Pattern

Common issues and solutions in `references/troubleshooting.md`:
1. OAuth authentication failures
2. Bearer token expiration
3. Invalid client credentials
4. Catalog not found
5. Network connectivity issues
6. Service principal permissions
7. PrivateLink configuration

**⚠️ STOP**: Present diagnosis and wait for user direction before applying fixes.

---

## Scope

This skill focuses on **Snowflake-side setup**:
- ✅ Creating catalog integrations for Unity Catalog
- ✅ OAuth and Bearer token authentication configuration
- ✅ Databricks service principal setup guidance
- ✅ Verification
- ✅ Troubleshooting

**Out of scope** (separate resources):
- ❌ Unity Catalog setup in Databricks → [Unity Catalog Documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- ❌ External volume creation
- ❌ Creating tables or catalog-linked databases (use shared `next-steps` skill)

---

## Quick Reference

**Catalog Integration SQL (OAuth)**:
```sql
CREATE OR REPLACE CATALOG INTEGRATION <name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<catalog_name>'
  REST_CONFIG = (
    CATALOG_URI = 'https://<workspace>.cloud.databricks.com/api/2.1/unity-catalog/iceberg'
    WAREHOUSE = '<catalog_name>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = OAUTH
    OAUTH_CLIENT_ID = '<client_id>'
    OAUTH_CLIENT_SECRET = '<client_secret>'
    OAUTH_TOKEN_URI = 'https://<workspace>.cloud.databricks.com/oidc/v1/token'
    OAUTH_ALLOWED_SCOPES = ('all-apis')
  )
  ENABLED = TRUE;
```

**Catalog Integration SQL (Bearer Token)**:
```sql
CREATE OR REPLACE CATALOG INTEGRATION <name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<catalog_name>'
  REST_CONFIG = (
    CATALOG_URI = 'https://<workspace>.cloud.databricks.com/api/2.1/unity-catalog/iceberg'
    WAREHOUSE = '<catalog_name>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = BEARER
    BEARER_TOKEN = '<personal_access_token>'
  )
  ENABLED = TRUE;
```

**Diagnostic Commands**:
```sql
SHOW CATALOG INTEGRATIONS LIKE '<name>';
DESC CATALOG INTEGRATION <name>;
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('<name>');
SELECT SYSTEM$LIST_NAMESPACES_FROM_CATALOG('<name>');
SELECT SYSTEM$LIST_ICEBERG_TABLES_FROM_CATALOG('<name>', '<namespace>');
```

---

## Success Criteria

- ✅ Integration shows `ENABLED=TRUE`
- ✅ `SYSTEM$VERIFY_CATALOG_INTEGRATION()` returns success
- ✅ Namespaces discoverable
- ✅ Tables visible

---

## Documentation

- [Configure Catalog Integration for Unity Catalog](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-unity)
- [Snowflake Iceberg Tables](https://docs.snowflake.com/user-guide/tables-iceberg)
- [Unity Catalog Documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)

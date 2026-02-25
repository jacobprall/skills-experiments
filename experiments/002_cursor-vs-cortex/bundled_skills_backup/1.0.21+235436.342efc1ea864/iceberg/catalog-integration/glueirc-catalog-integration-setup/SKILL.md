---
name: glueirc-catalog-integration-setup
description: "Setup and verify catalog integration for AWS Glue Iceberg REST Catalog. Triggers: create glue catalog integration, connect snowflake to glue, setup glue irc, configure glue iceberg rest, glue data catalog integration, AWS glue iceberg, sigv4 authentication glue, glue lake formation snowflake, query glue tables from snowflake, iceberg rest api glue, troubleshoot glue integration, verify glue catalog integration, glue vended credentials, glue external volume credentials, fix glue connection, debug glue iceberg."
---

# AWS Glue Iceberg REST Catalog Integration

Setup, verify, or troubleshoot a Snowflake catalog integration for AWS Glue Data Catalog.

## Intent Routing (FIRST)

**Ask the user**:
```
What would you like to do?

A: Create a new catalog integration for Glue IRC
   → Setup Snowflake to connect to AWS Glue Data Catalog

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

Create a new catalog integration to connect Snowflake to AWS Glue Data Catalog.

### Step 1: Prerequisites

Follow `setup/SKILL.md` to collect:

Collect one-by-one:
1. Confirm AWS Glue setup exists
2. Access delegation mode (vended credentials vs external volume)
3. Lake Formation setup (if vended credentials)
4. AWS Account ID
5. AWS Region
6. Glue Database (optional)
7. IAM Role ARN
8. Connectivity type
9. Integration name

**⚠️ STOP**: Confirm prerequisites before proceeding

### Step 2: Create Integration

**Load** `create/SKILL.md` and follow its workflow:

1. Generate CREATE CATALOG INTEGRATION SQL
2. **⚠️ STOP**: Review SQL with user
3. Execute creation
4. Retrieve Snowflake IAM user ARN and external ID
5. **⚠️ STOP**: Guide user to update AWS trust policy
6. Confirm trust policy updated

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

-- List namespaces (Glue databases)
SELECT SYSTEM$LIST_NAMESPACES_FROM_CATALOG('<integration_name>');

-- List tables in a namespace
SELECT SYSTEM$LIST_ICEBERG_TABLES_FROM_CATALOG('<integration_name>', '<database>');
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
- Access denied errors

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
1. Trust relationship not configured
2. External ID mismatch
3. IAM permissions missing
4. Lake Formation access denied
5. Region mismatch
6. KMS encryption issues
7. VPC endpoint connectivity

**⚠️ STOP**: Present diagnosis and wait for user direction before applying fixes.

---

## Scope

This skill focuses on **Snowflake-side setup**:
- ✅ Creating catalog integrations for Glue IRC
- ✅ IAM role and policy configuration
- ✅ AWS trust relationship establishment
- ✅ Verification
- ✅ Troubleshooting

**Out of scope** (separate resources):
- ❌ Lake Formation setup → [Snowflake + AWS Glue Guide](https://www.snowflake.com/en/developers/guides/data-lake-using-apache-iceberg-with-snowflake-and-aws-glue/)
- ❌ External volume creation
- ❌ Creating tables or catalog-linked databases (use shared `next-steps` skill)
- ❌ Glue Data Catalog setup in AWS

---

## Quick Reference

**Catalog Integration SQL**:
```sql
CREATE OR REPLACE CATALOG INTEGRATION <name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  REST_CONFIG = (
    CATALOG_URI = 'https://glue.<region>.amazonaws.com/iceberg'
    CATALOG_API_TYPE = AWS_GLUE
    CATALOG_NAME = '<aws_account_id>'  -- ALWAYS 12-digit AWS Account ID
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = SIGV4
    SIGV4_IAM_ROLE = '<iam_role_arn>'
    SIGV4_SIGNING_REGION = '<region>'
  )
  ENABLED = TRUE;
```

> **⚠️ CATALOG_NAME**: For Glue IRC, this is ALWAYS the **12-digit AWS Account ID** (e.g., `'631484165566'`), NOT a catalog name string.

**Diagnostic Commands**:
```sql
SHOW CATALOG INTEGRATIONS LIKE '<name>';
DESC CATALOG INTEGRATION <name>;
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('<name>');
SELECT SYSTEM$LIST_NAMESPACES_FROM_CATALOG('<name>');
SELECT SYSTEM$LIST_ICEBERG_TABLES_FROM_CATALOG('<name>', '<database>');
```

---

## Success Criteria

- ✅ Integration shows `ENABLED=TRUE`
- ✅ AWS trust policy configured with Snowflake IAM user and external ID
- ✅ `SYSTEM$VERIFY_CATALOG_INTEGRATION()` returns success
- ✅ Namespaces discoverable
- ✅ Tables visible

---

## Documentation

- [Configure Catalog Integration for AWS Glue IRC](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue)
- [Snowflake Iceberg Tables](https://docs.snowflake.com/user-guide/tables-iceberg)
- [AWS Glue Data Catalog](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html)
- [Lake Formation + Glue Setup Guide](https://www.snowflake.com/en/developers/guides/data-lake-using-apache-iceberg-with-snowflake-and-aws-glue/) (for vended credentials)

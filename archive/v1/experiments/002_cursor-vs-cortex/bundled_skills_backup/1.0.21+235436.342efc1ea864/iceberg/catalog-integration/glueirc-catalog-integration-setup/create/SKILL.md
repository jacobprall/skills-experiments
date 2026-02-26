---
name: glueirc-create-integration
description: "Create and execute catalog integration for AWS Glue IRC"
parent_skill: glueirc-catalog-integration-setup
---

# Configuration & Creation

Build and execute the SQL to create your AWS Glue Iceberg REST catalog integration, then configure the AWS trust relationship.

## When to Load

From main skill Step 2: After prerequisites have been gathered and confirmed

## Prerequisites

Must have from setup phase:
- IAM role ARN with Glue permissions
- Access delegation mode choice
- Connectivity type (Public/Private)
- AWS account ID and region
- Glue database name (optional)
- Integration name

## Workflow

### Step 2.1: Generate Catalog Integration SQL

Based on connectivity type and access delegation mode, generate appropriate SQL statement.

#### For Public Connectivity

```sql
CREATE OR REPLACE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<glue_database>'  -- Optional, omit if not provided
  REST_CONFIG = (
    CATALOG_URI = 'https://glue.<region>.amazonaws.com/iceberg'
    CATALOG_API_TYPE = AWS_GLUE
    CATALOG_NAME = '<aws_account_id>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = SIGV4
    SIGV4_IAM_ROLE = '<iam_role_arn>'
    SIGV4_SIGNING_REGION = '<region>'
  )
  ENABLED = TRUE;
```

#### For Private Connectivity

```sql
CREATE OR REPLACE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<glue_database>'  -- Optional
  REST_CONFIG = (
    CATALOG_URI = 'https://<vpc_endpoint_dns>/iceberg'
    CATALOG_API_TYPE = PRIVATE
    CATALOG_NAME = '<aws_account_id>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = SIGV4
    SIGV4_IAM_ROLE = '<iam_role_arn>'
    SIGV4_SIGNING_REGION = '<region>'
  )
  ENABLED = TRUE;
```

**Parameter Explanation**:
- `CATALOG_SOURCE = ICEBERG_REST`: Generic REST catalog (Glue uses Iceberg REST API)
- `TABLE_FORMAT = ICEBERG`: Apache Iceberg table format
- `CATALOG_NAMESPACE`: Optional default namespace (Glue database name)
- `CATALOG_URI`: Glue Iceberg REST endpoint
- `CATALOG_API_TYPE`: `AWS_GLUE` for public, `PRIVATE` for VPC endpoint
- `ACCESS_DELEGATION_MODE`:
  - `VENDED_CREDENTIALS`: Glue generates temporary credentials (no external volume needed)
  - `EXTERNAL_VOLUME_CREDENTIALS`: Use external volume for data access (default)
- `TYPE = SIGV4`: AWS Signature Version 4 authentication
- `SIGV4_IAM_ROLE`: ARN of IAM role Snowflake should assume
- `SIGV4_SIGNING_REGION`: AWS region for signing (must match Glue region)

> **⚠️ IMPORTANT: CATALOG_NAME for Glue IRC**
> 
> For AWS Glue IRC, **CATALOG_NAME is ALWAYS the 12-digit AWS Account ID** (e.g., `'631484165566'`), NOT a descriptive catalog name string.
> 
> This is different from other catalog types (OpenCatalog, Unity Catalog) which use a logical catalog name.

### Step 2.2: Review & Approval

**Present generated SQL to user**:

```
Generated Catalog Integration SQL:
═══════════════════════════════════════════════════════════
[The complete SQL with actual values filled in]
═══════════════════════════════════════════════════════════

This will create a catalog integration named '<integration_name>' 
connecting to AWS Glue Data Catalog in account '<aws_account_id>' 
and region '<region>' using SigV4 authentication.

IMPORTANT: After creation, you'll need to update the AWS IAM role 
trust policy with Snowflake-generated credentials.
```

**⚠️ MANDATORY STOPPING POINT**: Ask user: "Please review the SQL above. Ready to execute and create the catalog integration?"

**Wait for explicit approval**:
- "Yes", "Approved", "Looks good", "Proceed" → Continue to Step 2.3
- "No" or "Wait" → Ask: "What changes would you like to make?"

### Step 2.3: Execute Creation

**Execute approved SQL**:
```sql
[The approved CREATE CATALOG INTEGRATION statement]
```

**Expected Success Result**: 
```
Integration <integration_name> successfully created.
```

**If Success**: ✓ Integration created → Continue to Step 2.4

**If Error**: Present error → Load `references/troubleshooting.md` → Wait for direction

### Step 2.4: Retrieve Snowflake IAM Credentials

Now retrieve the Snowflake-generated IAM user ARN and external ID needed for AWS trust policy.

**Execute**:
```sql
DESCRIBE CATALOG INTEGRATION <integration_name>;
```

**Extract these values from output**:

| Property | Description | Example |
|----------|-------------|---------|
| `GLUE_AWS_IAM_USER_ARN` | Snowflake IAM user ARN | `arn:aws:iam::123456789001:user/abc1-b-self1234` |
| `GLUE_AWS_EXTERNAL_ID` | External ID for trust relationship | `ABC12345_SFCRole=1_abcdefgh` |

**Present to user**:
```
Snowflake IAM Credentials:
─────────────────────────────────────────
IAM User ARN: <GLUE_AWS_IAM_USER_ARN>
External ID:  <GLUE_AWS_EXTERNAL_ID>
─────────────────────────────────────────

These values are needed in the next step to configure the 
AWS IAM role trust policy.
```

**INFO**: Snowflake provisions a single IAM user for your entire Snowflake account. All Glue catalog integrations use the same IAM user but have unique external IDs.

### Step 2.5: Configure AWS Trust Policy

**Present trust policy template to user**:

```
AWS IAM Role Trust Policy Configuration:
═══════════════════════════════════════════════════════════

1. Go to AWS IAM Console → Roles → <your_iam_role>
2. Click "Trust relationships" tab
3. Click "Edit trust policy"
4. Add the following to the trust policy:

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "<GLUE_AWS_IAM_USER_ARN>"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "<GLUE_AWS_EXTERNAL_ID>"
        }
      }
    }
  ]
}

Replace:
- <GLUE_AWS_IAM_USER_ARN> with: <actual_value>
- <GLUE_AWS_EXTERNAL_ID> with: <actual_value>

5. Click "Update policy"

═══════════════════════════════════════════════════════════
```

**⚠️ MANDATORY STOPPING POINT**: Ask user: "Have you updated the AWS IAM role trust policy?"

**Wait for confirmation**: "Yes", "Done", "Updated" → Continue to Step 2.6

### Step 2.6: Verify Trust Relationship

**Explain**:
```
The trust relationship is now configured. In the next step 
(Verification), we'll test the connection to ensure:
- Trust policy is correct
- IAM role has Glue permissions
- Connection is working
```

**Output**: Catalog integration created with trust relationship configured

**Next**: Return to main skill → Proceed to Step 3 (Verification)

## Error Handling

**Common errors during creation**:
- **Invalid IAM role ARN**: Check format and role exists
- **Invalid region**: Verify region name spelling
- **Permission denied**: Check Snowflake privileges for creating integrations

**Common errors during trust setup**:
- **Copy-paste errors**: Verify no extra spaces or line breaks in trust policy
- **Wrong role updated**: Ensure updating the same role specified in SIGV4_IAM_ROLE
- **JSON syntax errors**: Validate trust policy JSON format

**For all errors**: Present error message clearly and load troubleshooting guide if needed.

## Output

Successfully created catalog integration in Snowflake with AWS trust relationship configured, ready for verification.

## Next Steps

After successful creation and trust configuration:
- Return to main skill
- Proceed to Step 3: Verification
- Load `verify/SKILL.md`

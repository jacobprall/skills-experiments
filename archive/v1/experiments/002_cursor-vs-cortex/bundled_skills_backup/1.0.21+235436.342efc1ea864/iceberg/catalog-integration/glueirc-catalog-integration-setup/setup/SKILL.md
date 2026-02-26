---
name: glueirc-setup-prerequisites
description: "Gather prerequisites for AWS Glue IRC catalog integration setup"
parent_skill: glueirc-catalog-integration-setup
---

# Prerequisites Gathering

Collect all required information to create your AWS Glue Iceberg REST catalog integration.

## When to Load

From main skill Step 1: Prerequisites gathering phase

## Prerequisites

User should have:
- AWS account with Glue Data Catalog configured
- Iceberg tables registered in Glue Data Catalog
- Admin access to Snowflake to create catalog integrations
- AWS IAM permissions to create/modify roles and policies

## Workflow

Collect prerequisites **one at a time** in the following order. Wait for user response before proceeding to next question.

---

### Step 1.1: Confirm AWS Glue Setup (FIRST)

**Ask**:
```
Before we begin, let's confirm your AWS setup:

Do you have an AWS account with:
✓ Glue Data Catalog configured
✓ Iceberg tables registered in Glue

(If you need to set up Glue Data Catalog first, see: 
https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html)
```

**If Yes** → Continue to Step 1.2

**If No** → 
```
This skill helps connect Snowflake to an EXISTING Glue Data Catalog 
with Iceberg tables. 

Please set up your Glue Data Catalog and register Iceberg tables first, 
then return to create the catalog integration.

Resources:
- AWS Glue Data Catalog: https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html
- Creating Iceberg tables in Glue: https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-format-iceberg.html
```

**STOP** - Cannot proceed without existing Glue setup

---

### Step 1.2: Access Delegation Mode

**Ask**:
```
How should Snowflake access the Iceberg data files in S3?

A: Vended Credentials (Recommended)
   ✓ Glue/Lake Formation generates temporary S3 credentials
   ✓ No external volume needed
   ✓ Simpler setup
   ⚠ Requires Lake Formation to be enabled

B: External Volume Credentials
   ✓ Works without Lake Formation
   ✗ Requires separate external volume setup
   ✗ More configuration steps
```

**Record user choice** → Continue based on selection

---

### Step 1.3: Lake Formation Setup (VENDED_CREDENTIALS only)

**If user chose Vended Credentials (A)**:

**Ask**:
```
Vended credentials require AWS Lake Formation to be enabled and configured.

Is Lake Formation already enabled in your AWS account for this Glue Data Catalog?

A: Yes, Lake Formation is enabled and configured
B: No, I need help setting up Lake Formation
C: Switch to External Volume Credentials instead
```

**If Yes (A)** → Continue to Step 1.4

**If No/Need help (B)** → Provide Lake Formation setup guide:

```
Lake Formation Setup Guide
═══════════════════════════════════════════════════════════

This skill focuses on the Snowflake side of the integration 
(catalog integration + IAM role/policy + trust relationship).

For Lake Formation setup, please follow this comprehensive guide:

📖 https://www.snowflake.com/en/developers/guides/data-lake-using-apache-iceberg-with-snowflake-and-aws-glue/

The guide covers:
- Enabling Lake Formation
- Registering S3 locations
- Granting Lake Formation permissions
- Creating Iceberg tables in Glue

Once Lake Formation is configured, return here to continue 
with the catalog integration setup.

═══════════════════════════════════════════════════════════
```

**STOP** - Wait for user to complete Lake Formation setup

**If Switch (C)** → Record `EXTERNAL_VOLUME_CREDENTIALS` and continue to Step 1.4

---

### Step 1.4: AWS Account ID

**Ask**:
```
What is your AWS Account ID?

(12-digit number, find it at: AWS Console → Account menu → Account ID)
Example: 123456789012
```

**Record**: AWS Account ID

---

### Step 1.5: AWS Region

**Ask**:
```
What AWS region is your Glue Data Catalog in?

(Find at: AWS Console → top-right dropdown)
Example: us-east-1, us-west-2, eu-west-1
```

**Record**: AWS Region

**Derive**: Catalog URI = `https://glue.<region>.amazonaws.com/iceberg`

---

### Step 1.6: Glue Database (Optional)

**Ask**:
```
Would you like to set a default Glue database (namespace)?

- If yes: Provide the database name (case-sensitive)
- If no: Leave blank (you can specify per-table later)

(Find databases at: AWS Console → Glue → Databases)
```

**Record**: Glue database name (or blank)

---

### Step 1.7: IAM Role

**Ask**:
```
Do you have an existing IAM role for Snowflake to use, or should we help create one?

A: I have an existing IAM role
   → Provide the role ARN (format: arn:aws:iam::<account_id>:role/<role_name>)

B: I need to create a new IAM role
   → We'll guide you through creation
```

**If existing role (A)**:
- **Record**: IAM Role ARN
- **Ask**: "Does this role already have Glue permissions attached?"
  - If yes → Continue to Step 1.7
  - If no → Provide policy template (see below)

**If new role (B)** → Provide IAM role creation guidance:

```
IAM Role Creation Guide
═══════════════════════════════════════════════════════════

1. Go to AWS Console → IAM → Roles → Create role

2. Select trusted entity:
   - Type: AWS account
   - Account: Another AWS account
   - Account ID: (we'll provide Snowflake's after integration creation)
   - ✓ Check "Require external ID"
   - External ID: (we'll provide after integration creation)

   NOTE: For now, use your own account ID as placeholder.
   We'll update the trust policy after creating the integration.

3. Role name: snowflake-glue-access (or your preferred name)

4. Create the role, then note the ARN

═══════════════════════════════════════════════════════════
```

**Record**: IAM Role ARN after user creates it

**Required IAM Permissions**:

| Mode | Required Permissions |
|------|---------------------|
| **Vended Credentials** | `glue:GetCatalog`, `glue:GetDatabase`, `glue:GetDatabases`, `glue:GetTable`, `glue:GetTables`, `lakeformation:GetDataAccess` |
| **External Volume** | `glue:GetCatalog`, `glue:GetDatabase`, `glue:GetDatabases`, `glue:GetTable`, `glue:GetTables` |

**Resources**: `arn:aws:glue:*:<account_id>:catalog`, `arn:aws:glue:*:<account_id>:database/*`, `arn:aws:glue:*:<account_id>:table/*/*`

**Ask**: "Have you attached the IAM policy with these permissions to your role?"

---

### Step 1.8: Connectivity Type

**Ask**:
```
How should Snowflake connect to Glue?

A: Public (Default) - Connect over public internet
B: Private - Connect via VPC endpoint (PrivateLink)

Most users choose Public unless you have specific security requirements.
```

**Record**: Connectivity type

**If Private** → Note: User will need VPC endpoint DNS for the integration

---

### Step 1.9: Integration Name

**Ask**:
```
What would you like to name your catalog integration?

Guidelines:
- Alphanumeric characters and underscores only
- Must be unique in your Snowflake account

Default suggestion: glue_catalog_int
```

**Record**: Integration name

---

### Step 1.10: Prerequisites Summary

**Present complete checklist**:

```
Prerequisites Checklist
═══════════════════════════════════════════════════════════

✓ Access Delegation Mode: <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
✓ Lake Formation: <Enabled|Not required>
✓ AWS Account ID: <account_id>
✓ AWS Region: <region>
✓ Catalog URI: https://glue.<region>.amazonaws.com/iceberg
✓ Glue Database: <database_name|Not specified>
✓ IAM Role ARN: <iam_role_arn>
✓ IAM Policy: Attached to role
✓ Connectivity: <Public|Private>
✓ Integration Name: <integration_name>

═══════════════════════════════════════════════════════════

Note: Trust relationship will be configured AFTER integration 
creation when Snowflake provides IAM user ARN and external ID.
```

**⚠️ STOPPING POINT**: "Does everything look correct? Ready to proceed with creating the catalog integration?"

- If yes → Return to main skill → Step 2 (Create)
- If changes needed → Ask what to update

---

## Output

Complete validated prerequisites checklist ready for catalog integration creation.

## Next Steps

After user confirms prerequisites:
- Return to main skill
- Proceed to Step 2: Configuration & Creation
- Load `create/SKILL.md`

---
name: unitycatalog-setup-prerequisites
description: "Gather prerequisites for Unity Catalog catalog integration setup"
parent_skill: unitycatalog-catalog-integration-setup
---

# Prerequisites Gathering

Collect all required information to create your Unity Catalog catalog integration.

This skill focuses on **Snowflake-side setup** only. Unity Catalog setup in Databricks should be completed beforehand.

## When to Load

From main skill Step 1: Prerequisites gathering phase

## Prerequisites

User should have:
- Access to a Databricks workspace with Unity Catalog enabled
- Iceberg tables registered in Unity Catalog
- Admin access to Snowflake to create catalog integrations
- Service principal or personal access token (PAT) for authentication

> **Note**: If you need help setting up Unity Catalog, see: [Unity Catalog Documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)

## Workflow

Collect prerequisites **one at a time** in the following order. Wait for user response before proceeding to next question.

---

### Step 1.1: Confirm Unity Catalog Setup (FIRST)

**Ask**:
```
Before we begin, let's confirm your Databricks setup:

Do you have a Databricks workspace with:
✓ Unity Catalog enabled
✓ Iceberg tables registered

(If you need to set up Unity Catalog first, see:
https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
```

**If Yes** → Continue to Step 1.2

**If No** → 
```
This skill helps connect Snowflake to an EXISTING Unity Catalog.

Please set up Unity Catalog and register Iceberg tables first,
then return to create the catalog integration.
```

**STOP** - Cannot proceed without existing Unity Catalog setup

---

### Step 1.2: Authentication Method

**Ask**:
```
Which authentication method would you like to use?

A: OAuth (Recommended for Production)
   ✓ Service principal with OAuth credentials
   ✓ More secure, supports credential rotation
   ✓ No token expiration concerns

B: Bearer Token / PAT (Simpler for Testing)
   ✓ Quick setup with personal access token
   ✓ Good for development/testing
   ⚠ Token expires (default 90 days)
```

**Record user choice** → Continue based on selection

---

### Step 1.3: Access Delegation Mode

**Ask**:
```
How should Snowflake access the Iceberg data files?

A: Vended Credentials (Recommended)
   ✓ Unity Catalog generates temporary credentials
   ✓ No external volume needed
   ✓ Simpler setup

B: External Volume Credentials
   ✓ Works with all configurations
   ✗ Requires separate external volume setup
```

**Record user choice** → Continue to Step 1.4

---

### Step 1.4: Connectivity Type

**Ask**:
```
How should Snowflake connect to Databricks?

A: Public (Default) - Connect over public internet
B: Private - Connect via PrivateLink

Most users choose Public unless you have specific security requirements.
Private requires Snowflake Business Critical edition.
```

**Record**: Connectivity type

---

### Step 1.5: Databricks Workspace Host

**Ask**:
```
What is your Databricks workspace host?

(Find at: Your Databricks URL, e.g., the part after https://)

Example: dbc-b6a22903-2e25.cloud.databricks.com
```

**Record**: Databricks workspace host

**Derive**: Catalog URI = `https://<host>/api/2.1/unity-catalog/iceberg`

---

### Step 1.6: Unity Catalog Name

**Ask**:
```
What is the name of your Unity Catalog?

(Find at: Databricks → Data → Catalogs, or run SHOW CATALOGS)
This is case-sensitive.

Common examples: main, unity_catalog, prod_catalog
```

**Record**: Catalog name

---

### Step 1.7: Catalog Namespace (Optional)

**Ask**:
```
Would you like to set a default namespace (schema)?

- If yes: Provide the schema name (case-sensitive)
- If no: Type "skip" (you can specify per-table later)

(Find schemas at: Databricks → Data → Your Catalog → Schemas)
```

**Record**: Namespace (or blank)

---

### Step 1.8A: OAuth Credentials (If OAuth selected)

**If user chose OAuth in Step 1.2**:

**Ask**:
```
Do you have OAuth credentials from a Databricks service principal?

You'll need:
- OAuth Client ID
- OAuth Client Secret
- OAuth Token URI

How to get credentials:
1. Databricks → User menu → Settings → Identity and Access → Service Principals
2. Create or select a service principal
3. Generate OAuth secret
4. Note Client ID and Secret

The service principal needs Unity Catalog privileges:
- USE CATALOG on the catalog
- USE SCHEMA on schemas
- SELECT on tables
```

**If Yes** → Ask for each credential:

**Ask**: "What is your OAuth Client ID?"
**Record**: OAuth Client ID

**Ask**: "What is your OAuth Client Secret?"
**Record**: OAuth Client Secret

**Derive**: OAuth Token URI = `https://<databricks_host>/oidc/v1/token`

**If No** → 
```
You need a service principal with OAuth credentials to proceed.

Please create one in Databricks:
1. Admin Console → Service Principals → Add
2. Generate OAuth secret
3. Grant Unity Catalog privileges

Then return with the Client ID and Secret.
```

**STOP** - Cannot proceed without OAuth credentials

---

### Step 1.8B: Bearer Token (If Bearer selected)

**If user chose Bearer Token in Step 1.2**:

**Ask**:
```
Do you have a Databricks Personal Access Token (PAT)?

How to get a PAT:
1. Databricks → Settings → User Settings → Access Tokens
2. Generate new token
3. Copy and securely store it

Note: Default token lifetime is 90 days. The user/service account
needs Unity Catalog privileges on the catalog/schemas/tables.
```

**If Yes** → 

**Ask**: "What is your Bearer Token (PAT)?"
**Record**: Bearer Token

**If No** → 
```
You need a Personal Access Token to proceed.

Please create one in Databricks:
1. Settings → User Settings → Access Tokens
2. Generate new token
3. Set appropriate lifetime

Then return with the token.
```

**STOP** - Cannot proceed without Bearer Token

---

### Step 1.9: Integration Name

**Ask**:
```
What would you like to name your catalog integration?

Guidelines:
- Alphanumeric characters and underscores only
- Must be unique in your Snowflake account

Default suggestion: unity_catalog_int
```

**Record**: Integration name

---

### Step 1.10: Prerequisites Summary

**Present complete checklist based on authentication method**:

**For OAuth**:
```
Prerequisites Checklist
═══════════════════════════════════════════════════════════

✓ Databricks Host: <databricks_host>
✓ Catalog URI: https://<host>/api/2.1/unity-catalog/iceberg
✓ Catalog Name: <catalog_name>
✓ Catalog Namespace: <namespace|Not specified>
✓ Access Delegation Mode: <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
✓ Connectivity: <Public|Private>
✓ Authentication: OAuth
✓ OAuth Client ID: <client_id>
✓ OAuth Client Secret: ********
✓ OAuth Token URI: https://<host>/oidc/v1/token
✓ Integration Name: <integration_name>

═══════════════════════════════════════════════════════════
```

**For Bearer Token**:
```
Prerequisites Checklist
═══════════════════════════════════════════════════════════

✓ Databricks Host: <databricks_host>
✓ Catalog URI: https://<host>/api/2.1/unity-catalog/iceberg
✓ Catalog Name: <catalog_name>
✓ Catalog Namespace: <namespace|Not specified>
✓ Access Delegation Mode: <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
✓ Connectivity: <Public|Private>
✓ Authentication: Bearer Token (PAT)
✓ Bearer Token: ********
✓ Integration Name: <integration_name>

═══════════════════════════════════════════════════════════
```

**Add note**:
```
Note: If using EXTERNAL_VOLUME_CREDENTIALS, you'll need an
external volume when creating tables or catalog-linked databases.
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

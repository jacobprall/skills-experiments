---
name: opencatalog-setup-prerequisites
description: "Gather prerequisites for OpenCatalog catalog integration setup"
parent_skill: opencatalog-catalog-integration-setup
---

# Prerequisites Gathering

Collect all required information to create your OpenCatalog catalog integration.

This skill focuses on **Snowflake-side setup** only. OpenCatalog account and catalog setup should be completed beforehand.

## When to Load

From main skill Step 1: Prerequisites gathering phase

## Prerequisites

User should have:
- Access to an OpenCatalog account with an internal catalog
- Iceberg tables registered in OpenCatalog
- Admin access to Snowflake to create catalog integrations

> **Note**: If you need help setting up OpenCatalog, see: [OpenCatalog Documentation](https://other-docs.snowflake.com/en/opencatalog/overview)

## Workflow

Collect prerequisites **one at a time** in the following order. Wait for user response before proceeding to next question.

---

### Step 1.1: Confirm OpenCatalog Setup (FIRST)

**Ask**:
```
Before we begin, let's confirm your OpenCatalog setup:

Do you have an OpenCatalog account with:
✓ An internal catalog configured
✓ Iceberg tables registered

(If you need to set up OpenCatalog first, see:
https://other-docs.snowflake.com/en/opencatalog/overview)
```

**If Yes** → Continue to Step 1.2

**If No** → 
```
This skill helps connect Snowflake to an EXISTING OpenCatalog catalog.

Please set up your OpenCatalog account and register Iceberg tables first,
then return to create the catalog integration.
```

**STOP** - Cannot proceed without existing OpenCatalog setup

---

### Step 1.2: Access Delegation Mode

**Ask**:
```
How should Snowflake access the Iceberg data files?

A: Vended Credentials (Recommended)
   ✓ OpenCatalog generates temporary credentials
   ✓ No external volume needed
   ✓ Simpler setup

B: External Volume Credentials
   ✓ Works with all configurations
   ✗ Requires separate external volume setup
```

**Record user choice** → Continue to Step 1.3

---

### Step 1.3: Connectivity Type

**Ask**:
```
How should Snowflake connect to OpenCatalog?

A: Public (Default) - Connect over public internet
B: Private - Connect via PrivateLink

Most users choose Public unless you have specific security requirements.
```

**Record**: Connectivity type

---

### Step 1.4: OpenCatalog Account URL

**Ask**:
```
What is your OpenCatalog account URL?

Format: https://<orgname>-<account_name>.snowflakecomputing.com

How to find:
- OpenCatalog UI → Account settings
- Or see: https://other-docs.snowflake.com/en/opencatalog/find-account-name

Example: https://myorg-myaccount.snowflakecomputing.com
```

**Record**: OpenCatalog account URL

**Derive**: Catalog URI = `<account_url>/polaris/api/catalog`

---

### Step 1.5: Catalog Name

**Ask**:
```
What is the name of your OpenCatalog catalog?

(Find at: OpenCatalog UI → Catalogs)
This is case-sensitive.

Example: my_catalog
```

**Record**: Catalog name

---

### Step 1.6: Catalog Namespace (Optional)

**Ask**:
```
Would you like to set a default namespace?

- If yes: Provide the namespace name (case-sensitive)
- If no: Type "skip" (you can specify per-table later)

(Find namespaces at: OpenCatalog UI → Catalog → Namespaces)
```

**Record**: Namespace (or blank)

---

### Step 1.7: OAuth Credentials

**Ask**:
```
Do you have OAuth credentials from an OpenCatalog service connection?

You'll need:
- OAuth Client ID
- OAuth Client Secret

How to get credentials:
1. OpenCatalog UI → Service Connections
2. Create or select a service connection
3. Note the Client ID and Secret

The service connection must have a catalog role with privileges:
- CATALOG_LIST_PROPERTIES
- NAMESPACE_LIST  
- TABLE_LIST
```

**If Yes** → Ask for Client ID and Client Secret separately:

**Ask**: "What is your OAuth Client ID?"
**Record**: OAuth Client ID

**Ask**: "What is your OAuth Client Secret?"
**Record**: OAuth Client Secret

**If No** → 
```
You need a service connection with OAuth credentials to proceed.

Please create one in OpenCatalog:
1. OpenCatalog UI → Service Connections → Create
2. Assign a principal role with catalog access
3. Generate credentials

Then return with the Client ID and Secret.
```

**STOP** - Cannot proceed without OAuth credentials

---

### Step 1.8: Integration Name

**Ask**:
```
What would you like to name your catalog integration?

Guidelines:
- Alphanumeric characters and underscores only
- Must be unique in your Snowflake account

Default suggestion: opencatalog_int
```

**Record**: Integration name

---

### Step 1.9: Prerequisites Summary

**Present complete checklist**:

```
Prerequisites Checklist
═══════════════════════════════════════════════════════════

✓ OpenCatalog Account URL: <account_url>
✓ Catalog URI: <account_url>/polaris/api/catalog
✓ Catalog Name: <catalog_name>
✓ Catalog Namespace: <namespace|Not specified>
✓ Access Delegation Mode: <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
✓ Connectivity: <Public|Private>
✓ OAuth Client ID: <client_id>
✓ OAuth Client Secret: ********
✓ Integration Name: <integration_name>

═══════════════════════════════════════════════════════════

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

---
name: opencatalog-create-integration
description: "Create and execute catalog integration for OpenCatalog"
parent_skill: opencatalog-catalog-integration-setup
---

# Configuration & Creation

Build and execute the SQL to create your OpenCatalog catalog integration.

## When to Load

From main skill Step 2: After prerequisites have been gathered and confirmed

## Prerequisites

Must have from setup phase:
- OAuth credentials (Client ID, Secret, Scopes)
- Access delegation mode choice
- Connectivity type (Public/Private)
- Catalog name
- Catalog namespace (optional)
- OpenCatalog URL
- Integration name

## Workflow

### Step 2.1: Generate Catalog Integration SQL

Based on connectivity type and access delegation mode, generate appropriate SQL statement.

**For Public Connectivity**:
```sql
CREATE OR REPLACE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = POLARIS
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<namespace>'  -- Optional, omit if not provided
  REST_CONFIG = (
    CATALOG_URI = '<opencatalog_url>'
    CATALOG_API_TYPE = PUBLIC
    CATALOG_NAME = '<catalog_name>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = OAUTH
    OAUTH_CLIENT_ID = '<client_id>'
    OAUTH_CLIENT_SECRET = '<client_secret>'
    OAUTH_ALLOWED_SCOPES = ('<scopes>')
  )
  ENABLED = TRUE;
```

**For Private Connectivity**:
```sql
CREATE OR REPLACE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = POLARIS
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<namespace>'  -- Optional, omit if not provided
  REST_CONFIG = (
    CATALOG_URI = '<privatelink_url>/polaris/api/catalog'
    CATALOG_API_TYPE = PRIVATE
    CATALOG_NAME = '<catalog_name>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = OAUTH
    OAUTH_CLIENT_ID = '<client_id>'
    OAUTH_CLIENT_SECRET = '<client_secret>'
    OAUTH_ALLOWED_SCOPES = ('<scopes>')
  )
  ENABLED = TRUE;
```

**Parameter Explanation**:
- `CATALOG_SOURCE = POLARIS`: Specifies OpenCatalog/Polaris as catalog type
- `TABLE_FORMAT = ICEBERG`: Apache Iceberg table format
- `CATALOG_NAMESPACE`: Optional default namespace for tables
- `CATALOG_URI`: OpenCatalog API endpoint
- `CATALOG_API_TYPE`: PUBLIC (internet) or PRIVATE (PrivateLink)
- `CATALOG_NAME`: Catalog name in OpenCatalog
- `ACCESS_DELEGATION_MODE`:
  - `VENDED_CREDENTIALS`: OpenCatalog generates temporary credentials (no external volume needed for tables/CLDs)
  - `EXTERNAL_VOLUME_CREDENTIALS`: Use external volume for data access (default, requires external volume when creating tables/CLDs)
- `TYPE = OAUTH`: OAuth2 authentication
- `OAUTH_ALLOWED_SCOPES`: Permissions granted (typically PRINCIPAL_ROLE:ALL)

**INFO**: Both `CATALOG_SOURCE = POLARIS` and `CATALOG_SOURCE = ICEBERG_REST` work for OpenCatalog. We use POLARIS as it's the OpenCatalog-specific option.

### Step 2.2: Review & Approval

**Present generated SQL to user**:

```
Generated Catalog Integration SQL:
═══════════════════════════════════════════════════════════
[The complete SQL with actual values filled in]
═══════════════════════════════════════════════════════════

This will create a catalog integration named '<integration_name>' 
connecting to OpenCatalog catalog '<catalog_name>' using OAuth 
authentication via <connectivity_type> connectivity.
```

**⚠️ MANDATORY STOPPING POINT**: Ask user: "Please review the SQL above. Ready to execute and create the catalog integration?"

**Wait for explicit approval**:
- "Yes", "Approved", "Looks good", "Proceed" → Continue to Step 2.4
- "No" or "Wait" → Ask: "What changes would you like to make?"
- "Edit" → Ask for specific modifications

### Step 2.4: Execute Creation

**Execute approved SQL**:
```sql
[The approved CREATE CATALOG INTEGRATION statement]
```

**Expected Success Result**: 
```
Catalog integration <integration_name> successfully created.
```

**If Success**: ✓ Integration created → Return to main skill → Step 3

**If Error**: Present error → Load `references/troubleshooting.md` → Wait for direction

## Output

Successfully created catalog integration in Snowflake, ready for verification.

## Error Handling

**Common errors**:
- **OAuth authentication failure**: Check credentials, load troubleshooting
- **Catalog name invalid**: Verify catalog name spelling with user
- **Permission denied**: Check Snowflake privileges for creating integrations

**For all errors**: Present error message clearly and load troubleshooting guide before attempting fixes.

## Next Steps

After successful creation:
- Return to main skill
- Proceed to Step 3: Verification
- Load `verify/SKILL.md`

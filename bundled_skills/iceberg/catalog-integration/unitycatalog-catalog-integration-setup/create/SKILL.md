---
name: unitycatalog-create-integration
description: "Create and execute catalog integration for Unity Catalog"
parent_skill: unitycatalog-catalog-integration-setup
---

# Configuration & Creation

Build and execute the SQL to create your Unity Catalog catalog integration.

## When to Load

From main skill Step 2: After prerequisites have been gathered and confirmed

## Prerequisites

Must have from setup phase:
- Authentication choice (OAuth or Bearer Token)
- If OAuth: Client ID, Secret, Token URI, Scopes
- If Bearer: Personal Access Token (PAT)
- Access delegation mode choice
- Connectivity type (Public/Private)
- Catalog name and REST endpoint
- Integration name

## Workflow

### Step 2.1: Generate Catalog Integration SQL

Based on authentication method and connectivity type, generate appropriate SQL statement.

#### Option A: OAuth Authentication

**For Public Connectivity**:
```sql
CREATE OR REPLACE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<namespace>'  -- Optional, omit if not provided
  REST_CONFIG = (
    CATALOG_URI = 'https://<databricks-host>/api/2.1/unity-catalog/iceberg-rest'
    CATALOG_NAME = '<catalog_name>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = OAUTH
    OAUTH_TOKEN_URI = 'https://<databricks-host>/oidc/v1/token'
    OAUTH_CLIENT_ID = '<client_id>'
    OAUTH_CLIENT_SECRET = '<client_secret>'
    OAUTH_ALLOWED_SCOPES = ('all-apis', 'sql')
  )
  ENABLED = TRUE;
```

**For Private Connectivity** (Business Critical Edition):
```sql
CREATE OR REPLACE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<namespace>'  -- Optional
  REST_CONFIG = (
    CATALOG_URI = 'https://<privatelink-endpoint>/api/2.1/unity-catalog/iceberg-rest'
    CATALOG_API_TYPE = PRIVATE
    CATALOG_NAME = '<catalog_name>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = OAUTH
    OAUTH_TOKEN_URI = 'https://<databricks-host>/oidc/v1/token'
    OAUTH_CLIENT_ID = '<client_id>'
    OAUTH_CLIENT_SECRET = '<client_secret>'
    OAUTH_ALLOWED_SCOPES = ('all-apis', 'sql')
  )
  ENABLED = TRUE;
```

#### Option B: Bearer Token Authentication

**For Public Connectivity**:
```sql
CREATE OR REPLACE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<namespace>'  -- Optional
  REST_CONFIG = (
    CATALOG_URI = 'https://<databricks-host>/api/2.1/unity-catalog/iceberg-rest'
    CATALOG_NAME = '<catalog_name>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = BEARER
    BEARER_TOKEN = '<personal_access_token>'
  )
  ENABLED = TRUE;
```

**For Private Connectivity**:
```sql
CREATE OR REPLACE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<namespace>'  -- Optional
  REST_CONFIG = (
    CATALOG_URI = 'https://<privatelink-endpoint>/api/2.1/unity-catalog/iceberg-rest'
    CATALOG_API_TYPE = PRIVATE
    CATALOG_NAME = '<catalog_name>'
    ACCESS_DELEGATION_MODE = <VENDED_CREDENTIALS|EXTERNAL_VOLUME_CREDENTIALS>
  )
  REST_AUTHENTICATION = (
    TYPE = BEARER
    BEARER_TOKEN = '<personal_access_token>'
  )
  ENABLED = TRUE;
```

**Parameter Explanation**:
- `CATALOG_SOURCE = ICEBERG_REST`: Generic REST catalog (Unity Catalog uses standard Iceberg REST)
- `TABLE_FORMAT = ICEBERG`: Apache Iceberg table format
- `CATALOG_NAMESPACE`: Optional default namespace (Unity Catalog schema)
- `CATALOG_URI`: Unity Catalog Iceberg REST endpoint
- `CATALOG_API_TYPE`: PUBLIC (internet) or PRIVATE (PrivateLink) - omit for public
- `CATALOG_NAME`: Catalog name in Unity Catalog
- `ACCESS_DELEGATION_MODE`:
  - `VENDED_CREDENTIALS`: Unity Catalog generates temporary credentials
  - `EXTERNAL_VOLUME_CREDENTIALS`: Use external volume for data access (default)
- **OAuth Parameters**:
  - `TYPE = OAUTH`: OAuth2 authentication
  - `OAUTH_TOKEN_URI`: Databricks OAuth token endpoint
  - `OAUTH_ALLOWED_SCOPES`: Permissions (e.g., `all-apis`, `sql`, `catalog`)
- **Bearer Parameters**:
  - `TYPE = BEARER`: Bearer token authentication
  - `BEARER_TOKEN`: Personal Access Token from Databricks

**INFO**: Unity Catalog uses `CATALOG_SOURCE = ICEBERG_REST` (generic REST), not `POLARIS` like OpenCatalog.

### Step 2.2: Review & Approval

**Present generated SQL to user**:

```
Generated Catalog Integration SQL:
═══════════════════════════════════════════════════════════
[The complete SQL with actual values filled in]
═══════════════════════════════════════════════════════════

This will create a catalog integration named '<integration_name>' 
connecting to Unity Catalog '<catalog_name>' using <OAuth|Bearer Token> 
authentication via <Public|Private> connectivity.
```

**⚠️ MANDATORY STOPPING POINT**: Ask user: "Please review the SQL above. Ready to execute and create the catalog integration?"

**Wait for explicit approval**:
- "Yes", "Approved", "Looks good", "Proceed" → Continue to Step 2.3
- "No" or "Wait" → Ask: "What changes would you like to make?"
- "Edit" → Ask for specific modifications

### Step 2.3: Execute Creation

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
- **OAuth authentication failure**: Check credentials, token URI, load troubleshooting
- **Bearer token invalid**: Check token is valid and not expired
- **Catalog name invalid**: Verify catalog name spelling with user
- **Permission denied**: Check Snowflake privileges for creating integrations
- **Network connectivity**: Verify Databricks workspace URL is accessible

**For all errors**: Present error message clearly and load troubleshooting guide before attempting fixes.

## Next Steps

After successful creation:
- Return to main skill
- Proceed to Step 3: Verification
- Load `verify/SKILL.md`

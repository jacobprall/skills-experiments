# Troubleshooting Unity Catalog Catalog Integration

Comprehensive guide for diagnosing and fixing issues with Unity Catalog catalog integrations.

## When to Load

Load this reference when:
- `SYSTEM$VERIFY_CATALOG_INTEGRATION()` returns failure
- Namespace or table discovery fails
- Connection or authentication errors occur
- Unexpected behavior during verification

## Important: ALTER CATALOG INTEGRATION Limitations

**Only these parameters can be altered:**
```sql
-- For OAuth authentication
ALTER CATALOG INTEGRATION <name> SET
  OAUTH_CLIENT_SECRET = '<new_secret>';

-- For Bearer token authentication
ALTER CATALOG INTEGRATION <name> SET
  BEARER_TOKEN = '<new_token>';

-- Refresh interval
ALTER CATALOG INTEGRATION <name> SET
  REFRESH_INTERVAL_SECONDS = <seconds>;
```

**REST_CONFIG cannot be altered.** If you need to change catalog URI, catalog name, warehouse, or access delegation mode, you must **recreate the integration**:
```sql
DROP CATALOG INTEGRATION <integration_name>;
CREATE CATALOG INTEGRATION <integration_name> ...;
```

---

## Common Issues

### 1. OAuth Authentication Failures

**Error Pattern**: 
```
Failed to perform OAuth client credential flow
OAuth token request failed
unauthorized_client
```

**Common Causes**:
- Incorrect OAuth Client ID or Secret
- Wrong OAuth Token URI
- Invalid OAuth scopes
- Service principal doesn't exist or is disabled in Databricks

#### Debug Step 1: Verify OAuth Credentials

**Check in Databricks**:
1. Navigate to Admin Console → Service Principals
2. Verify service principal exists and is active
3. Confirm OAuth secret is correct
4. Check Token URI format: `https://<databricks-host>/oidc/v1/token`

**Test OAuth Token Acquisition**:
```bash
curl -X POST https://<databricks-host>/oidc/v1/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "scope=all-apis" \
  -d "client_id=<client_id>" \
  -d "client_secret=<client_secret>"
```

**Expected Success Response**:
```json
{
  "access_token": "ey...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**If Failure**:
- `invalid_client`: Client ID or Secret is incorrect
- `invalid_scope`: Scope not allowed for service principal

#### Fix OAuth Issues

**If only the client secret changed**, you can alter it:
```sql
ALTER CATALOG INTEGRATION <integration_name>
  SET OAUTH_CLIENT_SECRET = '<new_client_secret>';
```

**If client ID, token URI, or scopes need to change**, recreate the integration:
```sql
DROP CATALOG INTEGRATION <integration_name>;

CREATE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<catalog_name>'
  REST_CONFIG = (
    CATALOG_URI = 'https://<workspace>.cloud.databricks.com/api/2.1/unity-catalog/iceberg'
    WAREHOUSE = '<catalog_name>'
    ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS
  )
  REST_AUTHENTICATION = (
    TYPE = OAUTH
    OAUTH_CLIENT_ID = '<corrected_client_id>'
    OAUTH_CLIENT_SECRET = '<client_secret>'
    OAUTH_TOKEN_URI = 'https://<workspace>.cloud.databricks.com/oidc/v1/token'
    OAUTH_ALLOWED_SCOPES = ('all-apis')
  )
  ENABLED = TRUE;
```

---

### 2. Bearer Token (PAT) Failures

**Error Pattern**:
```
Authentication failed
Invalid bearer token
Token expired
401 Unauthorized
```

**Common Causes**:
- Token expired (default 90-day lifetime)
- Token revoked or deleted in Databricks
- Incorrect token copied

#### Debug Bearer Token

**Check Token Validity**:
```bash
curl -H "Authorization: Bearer <token>" \
  https://<databricks-host>/api/2.0/clusters/list
```

**Expected**: 200 OK response (even if empty cluster list)
**If Failure**: 401 Unauthorized indicates invalid/expired token

#### Fix Bearer Token Issues

**Generate New Token**:
1. Databricks UI → Settings → User Settings → Access Tokens
2. Generate new token
3. Update integration:

```sql
ALTER CATALOG INTEGRATION <integration_name>
  SET BEARER_TOKEN = '<new_token>';
```

**Best Practice**: Set reminder to rotate token before expiration (e.g., every 60 days for 90-day tokens)

---

### 3. Unity Catalog Privilege Issues

**Error Pattern**:
```
Catalog not found
Permission denied
Forbidden
403 Forbidden
```

**Common Causes**:
- Service principal/user lacks Unity Catalog privileges
- Catalog doesn't exist
- Missing `USE CATALOG` or `USE SCHEMA` grants

#### Debug Privileges

**Check in Databricks SQL Editor**:
```sql
-- As admin, check grants for service principal
SHOW GRANTS ON CATALOG <catalog_name>;
SHOW GRANTS ON SCHEMA <catalog_name>.<schema_name>;
```

**Required Privileges**:
- `USE CATALOG` on catalog
- `USE SCHEMA` on schemas
- `SELECT` on tables

#### Fix Privilege Issues

**Grant Required Privileges** (as Unity Catalog admin):
```sql
-- Grant catalog access
GRANT USE CATALOG ON CATALOG <catalog_name> 
  TO SERVICE_PRINCIPAL `<service_principal_id>`;

-- Grant schema access
GRANT USE SCHEMA ON SCHEMA <catalog_name>.<schema_name>
  TO SERVICE_PRINCIPAL `<service_principal_id>`;

-- Grant table access
GRANT SELECT ON SCHEMA <catalog_name>.<schema_name>
  TO SERVICE_PRINCIPAL `<service_principal_id>`;
```

**For PAT/User**:
```sql
GRANT USE CATALOG ON CATALOG <catalog_name> TO `<user_email>`;
GRANT USE SCHEMA ON SCHEMA <catalog_name>.<schema_name> TO `<user_email>`;
GRANT SELECT ON SCHEMA <catalog_name>.<schema_name> TO `<user_email>`;
```

---

### 4. Catalog Not Found

**Error Pattern**:
```
Catalog '<catalog_name>' not found
Unable to access catalog
```

**Solutions**:

1. **Verify Catalog Exists in Unity Catalog**:
   ```sql
   -- In Databricks SQL Editor
   SHOW CATALOGS;
   ```

2. **Check Catalog Name Spelling**:
   - Case-sensitive in Unity Catalog
   - Common names: `main`, `hive_metastore` (legacy)

3. **Recreate Integration if Name Incorrect**:
   
   Since REST_CONFIG cannot be altered, recreate the integration:
   ```sql
   DROP CATALOG INTEGRATION <integration_name>;
   CREATE CATALOG INTEGRATION <integration_name> ...;
   ```

---

### 5. Network Connectivity Issues

**Error Pattern**:
```
Connection timeout
Failed to connect to catalog
Could not reach Unity Catalog endpoint
```

#### For Public Connectivity

**Verify URL Format**: 
```
Correct: https://<workspace-host>/api/2.1/unity-catalog/iceberg
Example: https://dbc-b6a22903-2e25.cloud.databricks.com/api/2.1/unity-catalog/iceberg
```

**Test Reachability**:
```bash
curl -I https://<databricks-host>/api/2.1/unity-catalog/iceberg
```

**Solutions**:
1. Verify Databricks workspace host is correct
2. Check Snowflake network policies don't block Databricks domain
3. Ensure workspace is accessible from public internet

#### For Private Connectivity

**Requirements**:
- Snowflake Business Critical edition
- AWS PrivateLink configured between Snowflake and Databricks
- Private endpoint URL configured

**Verify PrivateLink Configuration**:
1. Check PrivateLink endpoint exists
2. Verify security groups allow traffic
3. Confirm DNS resolution for private endpoint

**If connectivity type needs to change**, recreate the integration with correct settings.

---

### 6. External Volume Issues

**Error Pattern**:
```
External volume not found
Access denied to storage location
Cannot read from external volume
```

**Solutions**:

1. **Verify External Volume Exists**:
   ```sql
   SHOW EXTERNAL VOLUMES LIKE '<volume_name>';
   DESC EXTERNAL VOLUME <volume_name>;
   ```

2. **Check Storage Location Matches Unity Catalog**:
   - Unity Catalog stores data in configured cloud storage
   - External volume must point to same location
   - Check metastore storage configuration in Unity Catalog

3. **Validate Cloud Permissions**:
   
   **AWS S3**:
   - IAM role needs `s3:GetObject`, `s3:GetObjectVersion`, `s3:ListBucket`
   - Trust relationship configured for Snowflake external ID
   - Bucket policy allows access
   
   **Azure ADLS**:
   - Storage account has read permissions
   - Proper role assignments configured
   
   **GCS**:
   - Service account has storage permissions
   - IAM bindings configured correctly

4. **Consider Vended Credentials** (Alternative):
   - Requires recreating integration with `ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS`
   - Unity Catalog generates temporary credentials for Snowflake

---

### 7. Namespace/Table Discovery Issues

**Error Pattern**:
```
No namespaces found
Tables not visible
Empty result from LIST operations
```

**Solutions**:

1. **Verify Tables Exist in Unity Catalog**:
   ```sql
   -- In Databricks SQL Editor
   SHOW SCHEMAS IN CATALOG <catalog_name>;
   SHOW TABLES IN <catalog_name>.<schema_name>;
   ```

2. **Check Table Format**:
   - Unity Catalog must have **Iceberg tables**
   - Delta Lake tables won't be visible through Iceberg REST API
   - Check table type: `DESCRIBE TABLE EXTENDED <table_name>`

3. **Verify Privileges**:
   - Service principal needs `USE SCHEMA` on schema
   - Service principal needs `SELECT` on tables
   - Grant privileges as shown in section 3

4. **Case Sensitivity**:
   - Schema names are case-sensitive
   - Use exact spelling from Unity Catalog
   - List all namespaces first:
     ```sql
     SELECT SYSTEM$LIST_NAMESPACES_FROM_CATALOG('<integration_name>');
     ```

---

### 8. Table Query Failures

**Error Pattern**:
```
Table not found
Cannot read Iceberg metadata
Metadata file not accessible
```

**Solutions**:

1. **Verify Table is Iceberg Format**:
   ```sql
   -- In Databricks
   DESCRIBE TABLE EXTENDED <catalog>.<schema>.<table>;
   ```
   Look for `Provider: iceberg` or `Type: ICEBERG`

2. **Check Metadata Access**:
   - External volume must access metadata files
   - Metadata location in Unity Catalog storage
   - Verify IAM permissions for metadata paths

3. **Refresh Metadata** (for catalog-linked databases):
   ```sql
   ALTER DATABASE <database_name> REFRESH;
   ```

---

## Diagnostic Workflow

Follow this sequence when troubleshooting:

1. **Check Integration Status**:
   ```sql
   SHOW CATALOG INTEGRATIONS LIKE '<integration_name>';
   DESC CATALOG INTEGRATION <integration_name>;
   ```

2. **Test Connection**:
   ```sql
   SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('<integration_name>');
   ```

3. **Review Snowflake Query History**:
   ```sql
   SELECT * FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
   WHERE QUERY_TEXT ILIKE '%<integration_name>%'
   ORDER BY START_TIME DESC LIMIT 10;
   ```

4. **Check Unity Catalog Audit Logs** (in Databricks):
   - System Tables → Audit Logs
   - Look for failed authentication or authorization events

5. **Test Authentication Separately** (OAuth or Bearer token methods above)

---

## Getting Additional Help

**Documentation Resources**:
- [Unity Catalog Integration](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-unity)
- [Iceberg REST Catalog Troubleshooting](https://docs.snowflake.com/user-guide/tables-iceberg-configure-catalog-integration-rest-check-config)
- [Unity Catalog Privileges](https://docs.databricks.com/en/data-governance/unity-catalog/manage-privileges/index.html)
- [Databricks Service Principals](https://docs.databricks.com/en/admin/users-groups/service-principals.html)
- [ALTER CATALOG INTEGRATION](https://docs.snowflake.com/en/sql-reference/sql/alter-catalog-integration)

**Common Resolution Paths**:
- OAuth secret changed → Use ALTER to update secret
- Bearer token expired → Use ALTER to update token
- OAuth client ID or config changed → Recreate integration
- Privileges → Grant Unity Catalog access in Databricks
- Network → Check connectivity and URL format
- External volume → Validate cloud permissions and storage paths
- Discovery → Ensure tables are Iceberg format, check privileges

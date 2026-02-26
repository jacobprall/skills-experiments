# Troubleshooting OpenCatalog Catalog Integration

Comprehensive guide for diagnosing and fixing issues with OpenCatalog catalog integrations.

## When to Load

Load this reference when:
- `SYSTEM$VERIFY_CATALOG_INTEGRATION()` returns failure
- Namespace or table discovery fails
- Connection or authentication errors occur
- Unexpected behavior during verification

## Important: ALTER CATALOG INTEGRATION Limitations

**Only these parameters can be altered:**
```sql
-- To change OAuth secret:
ALTER CATALOG INTEGRATION <name> SET
  REST_AUTHENTICATION = (
    OAUTH_CLIENT_SECRET = '<new_secret>'
  );

-- To change refresh interval:
ALTER CATALOG INTEGRATION <name> SET
  REFRESH_INTERVAL_SECONDS = <seconds>;

-- To enable/disable:
ALTER CATALOG INTEGRATION <name> SET
  ENABLED = TRUE;  -- or FALSE
```

**REST_CONFIG cannot be altered.** If you need to change catalog URI, catalog name, or access delegation mode, you must **recreate the integration**:
```sql
DROP CATALOG INTEGRATION <integration_name>;
CREATE CATALOG INTEGRATION <integration_name> ...;
```

---

## Common Issues

### 1. OAuth Authentication Failures

**Error Pattern**: 
```
OAuth2 Access token request failed with error 'unauthorized_client'
Failed to perform OAuth client credential flow
```

**Common Causes**:
- Incorrect OAuth Client ID or Secret
- Wrong OAuth scopes
- Service connection doesn't exist or is disabled

#### Debug Step 1: Test OAuth Token Acquisition

Test OAuth authentication directly with curl:

```bash
curl -X POST https://<account>/polaris/api/catalog/v1/oauth/tokens \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "scope=PRINCIPAL_ROLE:ALL" \
  --data-urlencode "client_id=<client_id>" \
  --data-urlencode "client_secret=<client_secret>"
```

**Expected Success Response**:
```json
{
  "access_token": "ey...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**If Success**: OAuth credentials are valid. Issue may be with scopes or catalog access.

**If Failure**:
```json
{
  "error": "invalid_client",
  "error_description": "Client authentication failed"
}
```

**Solutions by Error Type**:

- **invalid_client**: Client ID or Secret is incorrect
  - Verify credentials from OpenCatalog service connection
  - Regenerate credentials if needed
  - Ensure no extra spaces or hidden characters

- **invalid_scope**: Scope is not allowed
  - Check service connection has proper principal role
  - Try `PRINCIPAL_ROLE:ALL` or specific role names
  - Verify principal role is attached to catalog role

#### Debug Step 2: Test Catalog Access

If OAuth token obtained successfully, test catalog access:

```bash
curl -X GET "https://<account>/polaris/api/catalog/v1/config?warehouse=<catalog_name>" \
  -H "Authorization: Bearer <access_token>"
```

**Expected Response**:
```json
{
  "defaults": {
    "default-base-location": "s3://my-bucket/path/"
  },
  "overrides": {
    "prefix": "my-catalog"
  }
}
```

**If Failure**:
- **403 Forbidden**: Service connection lacks catalog access
  - Check catalog role privileges in OpenCatalog
  - Verify principal role is attached to catalog role
  - Required privileges: `CATALOG_LIST_PROPERTIES`, `NAMESPACE_LIST`, `TABLE_LIST`

- **404 Not Found**: Catalog name doesn't exist
  - Verify `CATALOG_NAME` spelling (case-sensitive)
  - Check catalog exists in OpenCatalog UI

#### Fix OAuth Issues

**If only the client secret changed**, you can alter it:
```sql
ALTER CATALOG INTEGRATION <integration_name> SET
  REST_AUTHENTICATION = (
    OAUTH_CLIENT_SECRET = '<new_client_secret>'
  );
```

**If client ID or other config needs to change**, recreate the integration:
```sql
DROP CATALOG INTEGRATION <integration_name>;

CREATE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = POLARIS
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<namespace>'
  REST_CONFIG = (
    CATALOG_URI = 'https://<account>.snowflakecomputing.com/polaris/api/catalog'
    CATALOG_NAME = '<catalog_name>'
    ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS
  )
  REST_AUTHENTICATION = (
    TYPE = OAUTH
    OAUTH_CLIENT_ID = '<corrected_client_id>'
    OAUTH_CLIENT_SECRET = '<client_secret>'
    OAUTH_ALLOWED_SCOPES = ('PRINCIPAL_ROLE:ALL')
  )
  ENABLED = TRUE;
```

---

### 2. Catalog Not Found

**Error Pattern**:
```
Catalog '<catalog_name>' not found
Unable to access catalog
```

**Solutions**:

1. **Verify Catalog Name**: 
   - Log into OpenCatalog UI
   - Confirm exact catalog name (case-sensitive)
   - Check for typos or extra characters

2. **Recreate Integration if Name Incorrect**:
   
   Since REST_CONFIG cannot be altered, recreate the integration:
   ```sql
   DROP CATALOG INTEGRATION <integration_name>;
   CREATE CATALOG INTEGRATION <integration_name> ...;
   ```

3. **Check Service Connection Access**:
   - Ensure service connection has a catalog role
   - Catalog role must have privileges on the catalog
   - Grant required privileges in OpenCatalog:
     - `CATALOG_LIST_PROPERTIES`
     - `NAMESPACE_LIST`
     - `TABLE_LIST`

4. **Verify Catalog Type**:
   - This skill is for **internal catalogs** in OpenCatalog
   - If you have an **external catalog**, different setup required

---

### 3. Network Connectivity Issues

**Error Pattern**:
```
Connection timeout
Failed to connect to catalog
Could not reach OpenCatalog endpoint
```

#### For Public Connectivity

**Verify URL Format**: 
```
Correct: https://<orgname>-<account>.snowflakecomputing.com/polaris/api/catalog
```

**Test URL Reachability**:
```bash
curl -I https://<opencatalog_url>/v1/config
```

**Solutions**:

1. **Check URL Spelling**: Verify organization name and account name
2. **Test Network Access**: Ensure Snowflake can reach public internet
3. **Check Network Policies**: Verify no Snowflake network policies block OpenCatalog domain
4. **Verify Account URL**: Confirm URL from OpenCatalog settings

#### For Private Connectivity

**Verify PrivateLink Configuration**:

1. **Confirm PrivateLink Setup in OpenCatalog**: Must be configured first
2. **Check CATALOG_API_TYPE**: Must be `PRIVATE` for PrivateLink
3. **Verify PrivateLink URL Format**: Use PrivateLink-specific endpoint
4. **Validate Private Endpoint Access**: Ensure Snowflake account has access

**If connectivity type needs to change**, recreate the integration with correct settings.

---

### 4. External Volume Issues

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

2. **Check Storage Location Match**:
   - External volume storage location must match where OpenCatalog stores table data
   - Review `STORAGE_LOCATIONS` in external volume description
   - Verify with OpenCatalog's `default-base-location`
   - Storage paths must align (same bucket/container)

3. **Validate Cloud Permissions**:
   
   **AWS S3**:
   - IAM role has `s3:GetObject`, `s3:GetObjectVersion`, `s3:ListBucket`
   - Trust relationship configured for Snowflake
   
   **Google Cloud Storage**:
   - Service account has `storage.objects.get`, `storage.objects.list`
   - Proper IAM bindings configured
   
   **Azure Blob Storage**:
   - Storage account has read permissions
   - SAS token valid (if used)

4. **Consider Vended Credentials** (Alternative):
   - If external volume setup is complex
   - Requires recreating integration with `ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS`
   - Requires OpenCatalog catalog configured for credential vending

---

### 5. Namespace/Table Discovery Issues

**Error Pattern**:
```
No namespaces found
Tables not visible
Empty result from LIST operations
```

**Solutions**:

1. **Verify Tables Exist in OpenCatalog**:
   - Log into OpenCatalog UI
   - Navigate to your catalog
   - Confirm namespaces and tables are registered
   - Check that tables have data files

2. **Check Catalog Role Privileges**:
   - Principal role needs `NAMESPACE_LIST` privilege
   - Principal role needs `TABLE_LIST` privilege on namespace
   - Grant via OpenCatalog UI or API

3. **Case Sensitivity**:
   - Namespace names are case-sensitive
   - Use exact spelling from OpenCatalog
   - Try listing all namespaces first:
     ```sql
     SELECT SYSTEM$LIST_NAMESPACES_FROM_CATALOG('<integration_name>');
     ```

4. **Nested Namespaces**:
   - OpenCatalog supports nested namespaces (e.g., `parent.child`)
   - Use exact namespace path when listing tables
   - Check full namespace hierarchy in OpenCatalog

5. **Service Connection Privileges**:
   - Verify service connection's principal role
   - Check principal role is attached to catalog role
   - Confirm catalog role has grants on specific namespaces/tables

---

### 6. Table Query Failures

**Error Pattern**:
```
Table not found
Cannot read Iceberg metadata
Metadata file not accessible
Unsupported data type
Data type mismatch
```

**Solutions**:

1. **Verify Table Registration**:
   - Confirm table appears in `SYSTEM$LIST_ICEBERG_TABLES_FROM_CATALOG()`
   - Check table exists in Snowflake: `SHOW TABLES LIKE '<table_name>';`

2. **Check Metadata Access**:
   - External volume must have access to metadata files
   - Metadata stored in same location as data
   - Verify IAM/permissions for metadata directory

3. **Validate Table Schema**:
   ```sql
   DESC TABLE <database>.<schema>.<table_name>;
   ```
   - Should show columns from Iceberg schema
   - If error, metadata may be corrupted or inaccessible

4. **Check Data Type Compatibility**:
   - Snowflake may not support all Iceberg data types
   - See [Iceberg Data Types](https://docs.snowflake.com/en/user-guide/tables-iceberg-data-types#other-data-types) for supported mappings

5. **Refresh Table Metadata** (for catalog-linked databases):
   ```sql
   ALTER DATABASE <database_name> REFRESH;
   ```

---

## Diagnostic Workflow

When troubleshooting, follow this sequence:

1. **Check Integration Status**:
   ```sql
   SHOW CATALOG INTEGRATIONS LIKE '<integration_name>';
   DESC CATALOG INTEGRATION <integration_name>;
   ```

2. **Test Connection**:
   ```sql
   SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('<integration_name>');
   ```

3. **Review Query History** for detailed errors:
   ```sql
   SELECT * FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY())
   WHERE QUERY_TEXT ILIKE '%<integration_name>%'
   ORDER BY START_TIME DESC LIMIT 10;
   ```

4. **Check OpenCatalog Logs**:
   - Access OpenCatalog UI
   - View service connection activity logs
   - Look for authentication or authorization failures

5. **Test OAuth Separately** (see OAuth section above)

---

## Getting Additional Help

**Documentation Resources**:
- [Snowflake Iceberg REST Catalog Troubleshooting](https://docs.snowflake.com/user-guide/tables-iceberg-configure-catalog-integration-rest-check-config)
- [OpenCatalog Access Control](https://other-docs.snowflake.com/en/opencatalog/access-control)
- [OpenCatalog Service Connections](https://other-docs.snowflake.com/en/opencatalog/configure-service-connection)
- [ALTER CATALOG INTEGRATION](https://docs.snowflake.com/en/sql-reference/sql/alter-catalog-integration)

**Common Resolution Paths**:
- OAuth secret changed → Use ALTER to update secret
- OAuth client ID or config changed → Recreate integration
- Catalog not found → Verify catalog name, recreate if needed
- Network issues → Check connectivity type and URLs
- External volume → Validate cloud permissions and storage paths
- Discovery issues → Grant proper catalog role privileges

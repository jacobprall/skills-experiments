# Troubleshooting AWS Glue IRC Catalog Integration

Comprehensive guide for diagnosing and fixing issues with AWS Glue Iceberg REST catalog integrations.

## When to Load

Load this reference when:
- `SYSTEM$VERIFY_CATALOG_INTEGRATION()` returns failure
- Namespace or table discovery fails
- Trust relationship or IAM authentication errors occur
- Unexpected behavior during verification

## Important: ALTER CATALOG INTEGRATION Limitations

**Only these parameters can be altered:**
```sql
ALTER CATALOG INTEGRATION <name> SET
  REFRESH_INTERVAL_SECONDS = <seconds>;
```

> Note: For Glue IRC (SigV4 authentication), there is no secret to rotate via ALTER. 
> The IAM role credentials are managed through AWS trust relationships.

**REST_CONFIG and REST_AUTHENTICATION cannot be altered.**

If you need to change IAM role, region, catalog URI, or access delegation mode, you must **recreate the integration**:
```sql
DROP CATALOG INTEGRATION <integration_name>;
CREATE CATALOG INTEGRATION <integration_name> ...;
```

> **Note**: Recreating the integration generates a new external ID, requiring AWS trust policy update.

---

## Common Issues

### 1. Trust Relationship Not Configured

**Error Pattern**: 
```
User: <arn> is not authorized to perform: sts:AssumeRole on resource: <role_arn>
Failed to assume role
```

**Cause**: AWS IAM role trust policy doesn't allow Snowflake IAM user to assume the role.

**Debug Steps**:

1. Verify trust policy exists:
   - AWS Console → IAM → Roles → Your Role → Trust relationships
   
2. Check trust policy format:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {"AWS": "<snowflake_iam_user_arn>"},
       "Action": "sts:AssumeRole",
       "Condition": {
         "StringEquals": {"sts:ExternalId": "<external_id>"}
       }
     }]
   }
   ```

3. Retrieve current values:
   ```sql
   DESC CATALOG INTEGRATION <integration_name>;
   ```
   Extract: `API_AWS_IAM_USER_ARN` and `API_AWS_EXTERNAL_ID`

4. Verify trust policy matches:
   - Principal.AWS = API_AWS_IAM_USER_ARN (exact match)
   - Condition.StringEquals.sts:ExternalId = API_AWS_EXTERNAL_ID (exact match)

**Solutions**:
- Add trust policy if missing
- Update values if mismatched
- Check for typos, extra spaces, or line breaks
- Ensure editing correct IAM role (matches SIGV4_IAM_ROLE in integration)

---

### 2. External ID Mismatch

**Error Pattern**:
```
ExternalId in the request does not match the expected value
Access denied
```

**Cause**: External ID in AWS trust policy doesn't match current Snowflake-generated external ID.

**Common Scenarios**:
- Integration was recreated with `CREATE OR REPLACE`
- Trust policy copied from old integration
- Manual typo in trust policy

**Solution**:

1. Get current external ID:
   ```sql
   DESC CATALOG INTEGRATION <integration_name>;
   ```
   
2. Update AWS trust policy with new `API_AWS_EXTERNAL_ID` value

3. Verify update in AWS Console

**Security Note**: Each catalog integration has a unique external ID. `CREATE OR REPLACE` generates a new external ID and breaks the trust relationship until updated.

---

### 3. IAM Policy Missing Permissions

**Error Pattern**:
```
Access Denied
User: <arn> is not authorized to perform: glue:GetDatabase
```

**Cause**: IAM role lacks required Glue permissions.

**Required Permissions** (minimum for read-only):
```json
{
  "Effect": "Allow",
  "Action": [
    "glue:GetCatalog",
    "glue:GetDatabase",
    "glue:GetDatabases",
    "glue:GetTable",
    "glue:GetTables"
  ],
  "Resource": [
    "arn:aws:glue:*:<account_id>:catalog",
    "arn:aws:glue:*:<account_id>:database/*",
    "arn:aws:glue:*:<account_id>:table/*/*"
  ]
}
```

**Debug Steps**:

1. Check IAM role policies:
   - AWS Console → IAM → Roles → Your Role → Permissions
   
2. Verify policy includes required actions

3. Check resource restrictions (wildcards vs specific databases)

**Solutions**:
- Add missing permissions to IAM policy
- Broaden resource scope if too restrictive
- For write access, add: `CreateTable`, `UpdateTable`, `DeleteTable`, `CreateDatabase`, `DeleteDatabase`
- For S3 data access (read-write), add: `s3:GetObject`, `s3:PutObject` on table locations

---

### 4. Lake Formation Access Denied

**Error Pattern**:
```
Access denied by Lake Formation
Insufficient permissions to access database/table
```

**Cause**: AWS Lake Formation is enabled and IAM role lacks Lake Formation data permissions.

**Debug Steps**:

1. Check if Lake Formation is enabled:
   - AWS Console → Lake Formation → Data catalog settings
   
2. Verify IAM role has `lakeformation:GetDataAccess` permission:
   ```json
   {
     "Effect": "Allow",
     "Action": "lakeformation:GetDataAccess",
     "Resource": "*"
   }
   ```

3. Check Lake Formation data permissions:
   - AWS Console → Lake Formation → Permissions → Data permissions
   - Verify IAM role has grants for databases, tables, columns

**Solutions**:
- Add `lakeformation:GetDataAccess` to IAM policy
- Grant Lake Formation data permissions to IAM role:
  - Database-level: Describe database
  - Table-level: Select, Describe table
  - Column-level: Select on specific columns (if using column-level security)
- Use AWS CLI:
  ```bash
  aws lakeformation grant-permissions \
    --principal DataLakePrincipalIdentifier=<iam_role_arn> \
    --resource '{"Table":{"DatabaseName":"<db>","Name":"<table>"}}' \
    --permissions SELECT DESCRIBE
  ```

**Note**: Lake Formation takes precedence over IAM policies. Both must grant access.

**For Lake Formation setup help**: See [Snowflake + AWS Glue Guide](https://www.snowflake.com/en/developers/guides/data-lake-using-apache-iceberg-with-snowflake-and-aws-glue/)

---

### 5. Database/Table Not Found

**Error Pattern**:
```
Database '<name>' not found
Table '<name>' not found
```

**Causes**:
- Database/table name is case-sensitive
- IAM policy resource scope excludes the database/table
- Database/table doesn't exist in Glue Data Catalog

**Debug Steps**:

1. Check exact database name in Glue:
   - AWS Console → Glue → Databases
   
2. Verify case-sensitive match:
   ```sql
   SELECT SYSTEM$LIST_NAMESPACES_FROM_CATALOG('<integration_name>');
   ```

3. Check IAM policy resource scope:
   ```json
   "Resource": [
     "arn:aws:glue:*:<account>:database/<specific_db>",  // Too restrictive?
     "arn:aws:glue:*:<account>:database/*"                // Better for discovery
   ]
   ```

**Solutions**:
- Use exact casing from Glue Data Catalog
- Broaden IAM policy resource scope for discovery
- Verify database/table exists in Glue Console

---

### 6. Region Mismatch

**Error Pattern**:
```
Connection timeout
Unable to reach catalog endpoint
SignatureDoesNotMatch
```

**Cause**: SIGV4_SIGNING_REGION doesn't match the region where Glue Data Catalog resides.

**Debug Steps**:

1. Check integration configuration:
   ```sql
   DESC CATALOG INTEGRATION <integration_name>;
   ```
   Look for: `SIGV4_SIGNING_REGION` in REST_AUTHENTICATION

2. Verify Glue region:
   - Check CATALOG_URI: `https://glue.<region>.amazonaws.com/iceberg`
   - Ensure regions match

**Solution**:

Since REST_AUTHENTICATION cannot be altered, you must **recreate the integration** with the correct region:

```sql
DROP CATALOG INTEGRATION <integration_name>;

CREATE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  REST_CONFIG = (
    CATALOG_URI = 'https://glue.<correct_region>.amazonaws.com/iceberg'
    CATALOG_API_TYPE = AWS_GLUE
    CATALOG_NAME = '<aws_account_id>'
    ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS
  )
  REST_AUTHENTICATION = (
    TYPE = SIGV4
    SIGV4_IAM_ROLE = '<iam_role_arn>'
    SIGV4_SIGNING_REGION = '<correct_region>'
  )
  ENABLED = TRUE;
```

> **Note**: After recreating, update AWS trust policy with the new external ID.

---

## Diagnostic Commands

**Check integration status**:
```sql
SHOW CATALOG INTEGRATIONS LIKE '<integration_name>';
DESC CATALOG INTEGRATION <integration_name>;
```

**Test connection**:
```sql
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('<integration_name>');
```

**List namespaces**:
```sql
SELECT SYSTEM$LIST_NAMESPACES_FROM_CATALOG('<integration_name>');
```

**List tables**:
```sql
SELECT SYSTEM$LIST_ICEBERG_TABLES_FROM_CATALOG('<integration_name>', '<database_name>');
```

**AWS CLI diagnostics**:
```bash
# Verify IAM role trust policy
aws iam get-role --role-name <role_name>

# List Glue databases
aws glue get-databases --catalog-id <account_id> --region <region>

# List tables in database
aws glue get-tables --database-name <db_name> --region <region>

# Test assume role
aws sts assume-role --role-arn <role_arn> --role-session-name test --external-id <external_id>
```

## General Troubleshooting Tips

1. **Start with trust relationship**: Most issues are trust policy or external ID mismatches
2. **Check IAM permissions**: Verify both IAM policies and Lake Formation grants
3. **Verify regions match**: Signing region = Glue region
4. **Use exact casing**: Glue database/table names are case-sensitive
5. **Check AWS CloudTrail**: See detailed logs of AssumeRole and Glue API calls
6. **Test with AWS CLI**: Validate IAM role can access Glue independently
7. **Recreate if config changes needed**: REST_CONFIG and REST_AUTHENTICATION cannot be altered

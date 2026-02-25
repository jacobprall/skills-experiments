---
type: primitive
name: data-classification
domain: data-security
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/sql/call-system-classify"
---

# Data Classification

Discover and classify sensitive data (PII, PHI, financial) in Snowflake tables using built-in classification or custom classifiers.

## Syntax

### Manual classification

```sql
CALL SYSTEM$CLASSIFY('<database>.<schema>.<table>');

CALL SYSTEM$CLASSIFY('<database>.<schema>.<table>',
  {'auto_tag': true, 'sample_count': 10000});
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `table_name` | string | Yes | — | Fully qualified table name (quoted string) |
| `auto_tag` | boolean | No | `false` | Automatically apply semantic category tags |
| `sample_count` | integer | No | system default | Number of rows to sample for classification |

**Important:** Use `CALL`, not `SELECT`. There is no `CLASSIFY_TABLE`, `CLASSIFY_SCHEMA`, or similar function.

### Classification profile (automatic)

```sql
CREATE OR REPLACE SNOWFLAKE.DATA_PRIVACY.CLASSIFICATION_PROFILE <name>(
  'minimum_object_age_for_classification_days': 1,
  'maximum_classification_validity_days': 90,
  'auto_tag': FALSE
);
```

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `minimum_object_age_for_classification_days` | integer | 1 | Days a table must exist before classification |
| `maximum_classification_validity_days` | integer | 90 | Days before classification results expire |
| `auto_tag` | boolean | `FALSE` | Auto-apply system tags after classification |

### Custom classifier

```sql
CREATE OR REPLACE SNOWFLAKE.DATA_PRIVACY.CUSTOM_CLASSIFIER <name>();

CALL <classifier_name>!ADD_REGEX(
  '<semantic_category>',
  '<privacy_category>',
  '<regex_pattern>',
  '<description>'
);
```

| Parameter | Values | Description |
|-----------|--------|-------------|
| `semantic_category` | Any string (e.g., `'EMPLOYEE_ID'`) | Business meaning of the data |
| `privacy_category` | `'IDENTIFIER'`, `'QUASI_IDENTIFIER'`, `'SENSITIVE'` | Privacy classification level |
| `regex_pattern` | Valid regex | Pattern to match column values |

### Attach profile to database

```sql
ALTER DATABASE <database> SET CLASSIFICATION_PROFILE = '<profile_name>';
```

## Parameters

### Built-in semantic categories

Snowflake recognizes these categories automatically:

`NAME`, `EMAIL`, `PHONE_NUMBER`, `ADDRESS`, `US_SSN`, `DATE_OF_BIRTH`, `GENDER`, `AGE`, `PAYMENT_CARD`, `BANK_ACCOUNT`, `IBAN`

System tags are applied as `SNOWFLAKE.CORE.SEMANTIC_CATEGORY:<category>`.

### Privilege requirements

| Action | Required Privileges |
|--------|-------------------|
| `SYSTEM$CLASSIFY` | `SELECT` on table + `SNOWFLAKE.CORE_VIEWER` database role |
| `SYSTEM$CLASSIFY` with `auto_tag: true` | `OWNERSHIP` on schema |
| Create classification profile | `CREATE SNOWFLAKE.DATA_PRIVACY.CLASSIFICATION_PROFILE` + `SNOWFLAKE.CLASSIFICATION_ADMIN` |
| Set profile on database | `EXECUTE AUTO CLASSIFICATION` + `APPLY TAG` |

## Constraints

- `SYSTEM$CLASSIFY` works on tables and views, not stages or external tables.
- Classification results are returned as JSON — parse with `LATERAL FLATTEN`.
- Automatic classification runs on a schedule determined by the profile; it is not instant.
- Custom classifiers only match against string/varchar columns.

## Examples

### Classify a table and parse results

```sql
CALL SYSTEM$CLASSIFY('mydb.myschema.customers');

SELECT
  f.value:column_name::STRING AS column_name,
  f.value:semantic_category::STRING AS category,
  f.value:privacy_category::STRING AS privacy,
  f.value:confidence::STRING AS confidence
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) r,
     LATERAL FLATTEN(input => PARSE_JSON(r."classify")) f
WHERE f.value:confidence::STRING = 'HIGH';
```

### Create a custom classifier for employee IDs

```sql
CREATE OR REPLACE SNOWFLAKE.DATA_PRIVACY.CUSTOM_CLASSIFIER my_classifiers();

CALL my_classifiers!ADD_REGEX(
  'EMPLOYEE_ID',
  'IDENTIFIER',
  '^EMP-[0-9]{5}$',
  'Detects employee IDs in format EMP-XXXXX'
);
```

### Set up automatic classification

```sql
CREATE OR REPLACE SNOWFLAKE.DATA_PRIVACY.CLASSIFICATION_PROFILE prod_profile(
  'minimum_object_age_for_classification_days': 1,
  'maximum_classification_validity_days': 30,
  'auto_tag': TRUE
);

ALTER DATABASE production SET CLASSIFICATION_PROFILE = 'prod_profile';
```

### Query classification results

```sql
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_CLASSIFICATION_LATEST
WHERE DATABASE_NAME = 'PRODUCTION'
ORDER BY LAST_CLASSIFIED_ON DESC;
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using `SELECT SYSTEM$CLASSIFY(...)` | Wrong syntax — must use `CALL` | `CALL SYSTEM$CLASSIFY('db.schema.table')` |
| Guessing classification syntax | No `CLASSIFY_TABLE` or `CLASSIFY_SCHEMA` function exists | Always use `SYSTEM$CLASSIFY` with the exact syntax above |
| Skipping verification after profile creation | Profile may not have correct privileges or scope | Run `SHOW SNOWFLAKE.DATA_PRIVACY.CLASSIFICATION_PROFILE` and test with manual classify |
| Setting `auto_tag: TRUE` without reviewing results first | May apply incorrect tags that are hard to undo at scale | Test with manual classification first, then enable auto-tag |

## References

- `primitives/masking-policies`
- `primitives/account-usage-views`
- [Snowflake Docs: SYSTEM$CLASSIFY](https://docs.snowflake.com/en/sql-reference/sql/call-system-classify)

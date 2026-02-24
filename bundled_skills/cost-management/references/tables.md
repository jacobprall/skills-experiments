# Cost Management Tables Reference

## Query Index

| Intent | Table | Schema |
|--------|-------|--------|
| Overall spending (credits) | METERING_HISTORY | ACCOUNT_USAGE |
| Warehouse costs | WAREHOUSE_METERING_HISTORY | ACCOUNT_USAGE |
| Query-level attribution | QUERY_ATTRIBUTION_HISTORY | ACCOUNT_USAGE |
| Cost anomalies | ANOMALIES_DAILY | ACCOUNT_USAGE |
| Budget tracking | BUDGETS, BUDGET_DETAILS | ACCOUNT_USAGE |
| Resource monitors | RESOURCE_MONITORS | ACCOUNT_USAGE |
| Storage costs | STORAGE_USAGE, DATABASE_STORAGE_USAGE_HISTORY | ACCOUNT_USAGE |
| Serverless tasks | METERING_HISTORY (filtered) | ACCOUNT_USAGE |
| Cortex Analyst | CORTEX_ANALYST_USAGE_HISTORY | ACCOUNT_USAGE |
| Cortex Search | CORTEX_SEARCH_DAILY_USAGE_HISTORY | ACCOUNT_USAGE |
| Tags | TAG_REFERENCES | ACCOUNT_USAGE |

---

## ACCOUNT_USAGE Schema

### METERING_HISTORY

**Synonyms:** credit usage, metering, service costs, compute credits

**Description:** Credit consumption by service type at the account level.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY`

**Latency:** Up to 3 hours

| Column | Type | Description |
|--------|------|-------------|
| SERVICE_TYPE | VARCHAR | Service type |
| START_TIME | TIMESTAMP_LTZ | Start of metering period |
| END_TIME | TIMESTAMP_LTZ | End of metering period |
| ENTITY_ID | NUMBER | Entity identifier |
| NAME | VARCHAR | Entity name |
| CREDITS_USED | FLOAT | Credits consumed |
| CREDITS_USED_COMPUTE | FLOAT | Compute credits |
| CREDITS_USED_CLOUD_SERVICES | FLOAT | Cloud services credits |

**Common Service Types:**
- WAREHOUSE_METERING
- SERVERLESS_TASK
- SNOWPIPE
- AUTO_CLUSTERING
- MATERIALIZED_VIEW
- SEARCH_OPTIMIZATION
- REPLICATION
- QUERY_ACCELERATION

---

### WAREHOUSE_METERING_HISTORY

**Synonyms:** warehouse costs, warehouse credits, warehouse usage, compute costs

**Description:** Credit consumption by warehouse.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY`

**Latency:** Up to 3 hours

| Column | Type | Description |
|--------|------|-------------|
| START_TIME | TIMESTAMP_LTZ | Start of metering period |
| END_TIME | TIMESTAMP_LTZ | End of metering period |
| WAREHOUSE_ID | NUMBER | Warehouse ID |
| WAREHOUSE_NAME | VARCHAR | Warehouse name |
| CREDITS_USED | FLOAT | Total credits |
| CREDITS_USED_COMPUTE | FLOAT | Compute credits |
| CREDITS_USED_CLOUD_SERVICES | FLOAT | Cloud services credits |

---

### QUERY_ATTRIBUTION_HISTORY

**Synonyms:** query costs, query credits, which queries cost the most, expensive queries

**Description:** Credit attribution at the query level. Essential for understanding which queries drive costs.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY`

**Latency:** Up to 3 hours

| Column | Type | Description |
|--------|------|-------------|
| QUERY_ID | VARCHAR | Query identifier |
| QUERY_TEXT | VARCHAR | SQL text |
| START_TIME | TIMESTAMP_LTZ | Query start |
| END_TIME | TIMESTAMP_LTZ | Query end |
| WAREHOUSE_NAME | VARCHAR | Warehouse used |
| USER_NAME | VARCHAR | User who ran query |
| ROLE_NAME | VARCHAR | Role used |
| DATABASE_NAME | VARCHAR | Database context |
| SCHEMA_NAME | VARCHAR | Schema context |
| CREDITS_ATTRIBUTED_COMPUTE | FLOAT | Compute credits |
| QUERY_TAG | VARCHAR | Query tag if set |

---

### ANOMALIES_DAILY

**Synonyms:** cost anomalies, cost spikes, unexpected costs, anomaly detection

**Description:** ML-detected cost anomalies by warehouse and day.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY`

| Column | Type | Description |
|--------|------|-------------|
| MEASUREMENT_DATE | DATE | Date of anomaly |
| WAREHOUSE_NAME | VARCHAR | Warehouse name |
| CREDITS_USED_COMPUTE | FLOAT | Actual compute credits |
| CREDITS_PREDICTED | FLOAT | Expected credits |
| CREDITS_ANOMALY_LOWER_BOUND | FLOAT | Lower bound of normal |
| CREDITS_ANOMALY_UPPER_BOUND | FLOAT | Upper bound of normal |
| COMPOSITE_SCORE | FLOAT | Anomaly score (higher = more anomalous) |

**Common Query:**
```sql
-- Find significant anomalies in the past week
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.ANOMALIES_DAILY
WHERE measurement_date >= DATEADD(day, -7, CURRENT_DATE())
  AND composite_score > 0.7
ORDER BY composite_score DESC;
```

---

### BUDGETS

**Synonyms:** budget list, budget configuration, spending limits

**Description:** Budget definitions.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.BUDGETS`

| Column | Type | Description |
|--------|------|-------------|
| BUDGET_ID | NUMBER | Budget identifier |
| BUDGET_NAME | VARCHAR | Budget name |
| ACCOUNT_LOCATOR | VARCHAR | Account locator |
| CREDIT_QUOTA | FLOAT | Credit limit |
| FREQUENCY | VARCHAR | MONTHLY, WEEKLY, etc. |
| START_DATE | DATE | Budget start |
| END_DATE | DATE | Budget end |

---

### BUDGET_DETAILS

**Synonyms:** budget spending, budget status, budget usage

**Description:** Budget spending details and status.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.BUDGET_DETAILS`

| Column | Type | Description |
|--------|------|-------------|
| BUDGET_NAME | VARCHAR | Budget name |
| BUDGET_ID | NUMBER | Budget ID |
| SPENDING_LIMIT | FLOAT | Credit limit |
| SPENT_CREDITS | FLOAT | Credits spent |
| REMAINING_CREDITS | FLOAT | Credits remaining |
| BUDGET_STATUS | VARCHAR | Status |

---

### RESOURCE_MONITORS

**Synonyms:** resource monitor, credit monitor, warehouse limits

**Description:** Resource monitor configurations.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.RESOURCE_MONITORS`

| Column | Type | Description |
|--------|------|-------------|
| NAME | VARCHAR | Monitor name |
| CREDIT_QUOTA | FLOAT | Credit quota |
| USED_CREDITS | FLOAT | Credits used |
| REMAINING_CREDITS | FLOAT | Credits remaining |
| FREQUENCY | VARCHAR | Reset frequency |
| START_TIME | TIMESTAMP_LTZ | Monitor start |
| END_TIME | TIMESTAMP_LTZ | Monitor end |
| NOTIFY_AT | VARIANT | Notification thresholds |
| SUSPEND_AT | NUMBER | Suspend threshold |
| SUSPEND_IMMEDIATELY_AT | NUMBER | Immediate suspend threshold |

---

### STORAGE_USAGE

**Synonyms:** storage costs, data storage, storage credits

**Description:** Account-level storage usage.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.STORAGE_USAGE`

| Column | Type | Description |
|--------|------|-------------|
| USAGE_DATE | DATE | Date |
| STORAGE_BYTES | NUMBER | Total storage bytes |
| STAGE_BYTES | NUMBER | Stage storage |
| FAILSAFE_BYTES | NUMBER | Failsafe storage |

---

### DATABASE_STORAGE_USAGE_HISTORY

**Synonyms:** database storage, storage by database

**Description:** Storage usage by database.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY`

| Column | Type | Description |
|--------|------|-------------|
| USAGE_DATE | DATE | Date |
| DATABASE_ID | NUMBER | Database ID |
| DATABASE_NAME | VARCHAR | Database name |
| AVERAGE_DATABASE_BYTES | NUMBER | Average bytes |
| AVERAGE_FAILSAFE_BYTES | NUMBER | Failsafe bytes |

---

### TAG_REFERENCES

**Synonyms:** tags, object tags, cost allocation tags, tagging

**Description:** Tag assignments to objects for cost attribution.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES`

| Column | Type | Description |
|--------|------|-------------|
| TAG_DATABASE | VARCHAR | Database containing tag |
| TAG_SCHEMA | VARCHAR | Schema containing tag |
| TAG_NAME | VARCHAR | Tag name |
| TAG_VALUE | VARCHAR | Tag value |
| OBJECT_DATABASE | VARCHAR | Tagged object database |
| OBJECT_SCHEMA | VARCHAR | Tagged object schema |
| OBJECT_NAME | VARCHAR | Tagged object name |
| DOMAIN | VARCHAR | Object type (TABLE, WAREHOUSE, etc.) |

---

### CORTEX_ANALYST_USAGE_HISTORY

**Synonyms:** cortex analyst costs, analyst credits, semantic layer costs

**Description:** Cortex Analyst usage and credits.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY`

| Column | Type | Description |
|--------|------|-------------|
| START_TIME | TIMESTAMP_LTZ | Period start |
| END_TIME | TIMESTAMP_LTZ | Period end |
| USERNAME | VARCHAR | User |
| CREDITS | FLOAT | Credits consumed |
| REQUEST_COUNT | NUMBER | Number of requests |

---

### CORTEX_SEARCH_DAILY_USAGE_HISTORY

**Synonyms:** cortex search costs, search credits, vector search costs

**Description:** Cortex Search service usage.

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_SEARCH_DAILY_USAGE_HISTORY`

| Column | Type | Description |
|--------|------|-------------|
| USAGE_DATE | DATE | Date |
| SERVICE_NAME | VARCHAR | Search service name |
| CREDITS_USED | FLOAT | Credits consumed |
| QUERIES | NUMBER | Number of queries |

---

### CORTEX_FUNCTIONS_USAGE_HISTORY

**Synonyms:** cortex function costs, LLM costs, AI function credits

**Description:** Cortex LLM function usage (COMPLETE, SUMMARIZE, etc.).

**Base Table:** `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY`

| Column | Type | Description |
|--------|------|-------------|
| START_TIME | TIMESTAMP_LTZ | Period start |
| END_TIME | TIMESTAMP_LTZ | Period end |
| FUNCTION_NAME | VARCHAR | Function (COMPLETE, SUMMARIZE, etc.) |
| MODEL_NAME | VARCHAR | Model used |
| WAREHOUSE_ID | NUMBER | Warehouse ID |
| TOKEN_CREDITS | FLOAT | Credits from tokens |
| TOKENS | NUMBER | Tokens consumed |

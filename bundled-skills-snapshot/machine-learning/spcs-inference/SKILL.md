---
name: spcs-inference
description: "Deploy models from Snowflake Model Registry to Snowpark Container Services for real-time inference. Use when: creating inference services, SPCS deployment, REST endpoints for models, GPU inference. Triggers: create inference service, SPCS inference, inference endpoint, serve model, deploy to SPCS, model endpoint."
parent_skill: model-registry
---

# SPCS Inference Service Deployment

Deploy a registered model to Snowpark Container Services for real-time inference.

## ⚠️ CRITICAL: Environment Guide Check

**Before proceeding, check if you already have the environment guide (from `machine-learning/SKILL.md` → Step 0) in memory.** If you do NOT have it or are unsure, go back and load it now. The guide contains essential surface-specific instructions for session setup, code execution, and package management that you must follow.

---

## Prerequisites

- Model already registered in Snowflake Model Registry (see `../model-registry/SKILL.md`)
- Access to a compute pool (GPU or CPU)
- `BIND SERVICE ENDPOINT` privilege for HTTP endpoints

---

## Workflow: Create Inference Service

### Step 1: Identify the Model

If coming from model registration, use that model reference. Otherwise ask for:
- Model name and version
- Database/Schema where the model is registered

**⚠️ STOP**: Wait for response if not already known.

### Step 2: Choose Service Database and Schema

**Ask user:**
```
Which database and schema would you like to deploy the inference service in?

Note: This can be different from where the model is registered.
```

**⚠️ STOP**: Wait for user response.

### Step 3: Select Compute Pool

```sql
SHOW COMPUTE POOLS;
```

Present available compute pools to the user, indicating GPU vs CPU, nodes, and services running:

**Ask user:**
```
Available compute pools:

| Pool Name | Instance Family | GPUs/Node | Min/Max Nodes | Active Nodes | State | Services |
|-----------|-----------------|-----------|---------------|--------------|-------|----------|
| POOL_A    | GPU_NV_M        | 4 x A10G  | 1 / 4         | 2            | ACTIVE | 2        |
| POOL_B    | CPU_X64_M       | None      | 1 / 2         | 0            | SUSPENDED | 0      |
| ...       | ...             | ...       | ...           | ...          | ... | ...      |

Which compute pool would you like to use?

Recommendation: Use a GPU compute pool for models that require GPU inference 
(e.g., deep learning, transformers, large embeddings).
```

**⚠️ STOP**: Wait for user response.

**GPU Reference:**

| Instance Family | GPUs per Node | GPU Type |
|-----------------|---------------|----------|
| GPU_NV_S        | 1             | A10G     |
| GPU_NV_M        | 4             | A10G     |
| GPU_NV_L        | 8             | A100     |

If no suitable pool exists, offer to create one:

```sql
CREATE COMPUTE POOL IF NOT EXISTS <POOL_NAME>
    MIN_NODES = 1 MAX_NODES = <N>
    INSTANCE_FAMILY = '<INSTANCE_FAMILY>'
    AUTO_RESUME = TRUE;
```

### Step 4: Configure Max Instances

**Ask user:**
```
How many max instances would you like for the service?

Max instances controls horizontal scaling - each instance is a separate container 
replica that can handle inference requests in parallel. More instances = higher 
throughput for concurrent requests.

- 1 instance: Suitable for development/testing or low traffic
- 2+ instances: Recommended for production workloads expecting higher concurrent load

The service will automatically scale between min_instances and max_instances based on demand.

Enter max_instances (default: 1):
```

**⚠️ STOP**: Wait for user response.

### Step 5: Check Existing Service

```sql
SHOW SERVICES LIKE '<SERVICE_NAME>' IN SCHEMA <DATABASE>.<SCHEMA>;
```

If exists, ask user: rename, delete & recreate, or keep existing.

### Step 6: Create Service

**⚠️ MANDATORY:** Present summary and get user confirmation before executing:

```
Summary:
- Model: <MODEL_DATABASE>.<MODEL_SCHEMA>.<MODEL_NAME> (version <VERSION>)
- Service: <SERVICE_DATABASE>.<SERVICE_SCHEMA>.<SERVICE_NAME>
- Compute Pool: <COMPUTE_POOL> (GPU/CPU)
- Max Instances: <MAX_INSTANCES>
- GPU Requests: <VALUE or N/A>

Proceed? (Yes/No)
```

**⚠️ STOP**: Wait for user confirmation before proceeding.

---

#### Service Creation Code

Set up the session following your loaded environment guide, then generate the service creation code.Service creation takes 5-15 minutes. You MUST:

Use `snowpark_session.py` from parent skill (`machine-learning/SKILL.md` → Session Setup Patterns). Copy the helper script to the working directory and import it.

**DO NOT** combine service creation with model registration in the same script.
**DO NOT** run service creation inline - it will timeout.
**For GPU compute pool:**

```python
from snowflake.ml.registry import Registry

# Session setup per environment guide
session = <SESSION_SETUP>
session.use_database("<SERVICE_DATABASE>")
session.use_schema("<SERVICE_SCHEMA>")

reg = Registry(session=session, database_name="<MODEL_DATABASE>", schema_name="<MODEL_SCHEMA>")
mv = reg.get_model("<MODEL_NAME>").version("<VERSION>")

print("Creating service...")

mv.create_service(
    service_name="<SERVICE_NAME>",
    service_compute_pool="<COMPUTE_POOL>",
    ingress_enabled=True,
    gpu_requests="<MAX_GPUS_FOR_NODE>",
    max_instances=<MAX_INSTANCES>,
)

print("Service created successfully.")
```

**For CPU compute pool:**

```python
from snowflake.ml.registry import Registry

# Session setup per environment guide
session = <SESSION_SETUP>
session.use_database("<SERVICE_DATABASE>")
session.use_schema("<SERVICE_SCHEMA>")

reg = Registry(session=session, database_name="<MODEL_DATABASE>", schema_name="<MODEL_SCHEMA>")
mv = reg.get_model("<MODEL_NAME>").version("<VERSION>")

print("Creating service...")

mv.create_service(
    service_name="<SERVICE_NAME>",
    service_compute_pool="<COMPUTE_POOL>",
    ingress_enabled=True,
    max_instances=<MAX_INSTANCES>,
)

print("Service created successfully.")
```

---

#### Execution: CLI

**⚠️ CRITICAL - MUST FOLLOW THIS PATTERN for CLI:**

Service creation takes 5-15 minutes. You MUST:
1. Write the code to a **separate Python script file** (e.g., `/path/to/create_service.py`)
2. Execute it in **background mode**
3. Monitor via **SQL** while it runs (Step 7)

**DO NOT** combine service creation with model registration in the same script.
**DO NOT** run service creation inline - it will timeout.

Execute the script using the Bash tool with `run_in_background=true`:

```
Tool: Bash
Command: SNOWFLAKE_CONNECTION_NAME=<connection> python /absolute/path/to/create_service.py
run_in_background: true
```

This returns a `shell_id` immediately. Use `bash_output` tool with that `shell_id` to check progress.

#### Execution: Snowsight (Notebook)

Run the service creation code in a notebook cell. Service creation takes 5-15 minutes. Wait for the cell execution to finish

---

### Step 7: Monitor Service Status (CLI Only)

**⚠️ CRITICAL:** While the service creation runs:

1. **Check script progress** (CLI: use `bash_output` tool with the `shell_id`)
2. **Monitor service status** using SQL

Service creation typically takes 5-15 minutes. Poll every 60 seconds.

---

**Check service status (SQL):**

```sql
DESCRIBE SERVICE <SERVICE_DATABASE>.<SERVICE_SCHEMA>.<SERVICE_NAME>;
```

**Or use pattern matching for multiple services:**

```sql
SHOW SERVICES LIKE '<SERVICE_NAME>' IN SCHEMA <SERVICE_DATABASE>.<SERVICE_SCHEMA>;
```

**Service Status Reference:**

| Status | Meaning | Action |
|--------|---------|--------|
| `PENDING` | Service registered, waiting for resources | Wait 60s, poll again |
| `STARTING` | Containers being pulled and started | Wait 60s, poll again |
| `RUNNING` | Service is ready for inference | Success - proceed to Step 8 |
| `FAILED` | Deployment failed | Fetch logs (see below) |
| `SUSPENDED` | Service suspended | Run `ALTER SERVICE <SERVICE_NAME> RESUME;` |

---

**When status is RUNNING, get endpoint URL:**

```sql
SHOW ENDPOINTS IN SERVICE <SERVICE_DATABASE>.<SERVICE_SCHEMA>.<SERVICE_NAME>;
```

Report the `ingress_url` to user.

---

**Check instance-level status (optional, more detail):**

```sql
SELECT SYSTEM$GET_SERVICE_STATUS('<SERVICE_DATABASE>.<SERVICE_SCHEMA>.<SERVICE_NAME>');
```

Returns JSON with each container's status. Look for `"status":"READY"` and `"message":"Running"` on all instances before testing.

---

**If status is FAILED, fetch logs for debugging:**

```sql
CALL SYSTEM$GET_SERVICE_LOGS('<SERVICE_DATABASE>.<SERVICE_SCHEMA>.<SERVICE_NAME>', 0, 'model-inference');
```

---

**Timeout:** If service hasn't reached RUNNING after ~20 minutes, inform user and provide manual check command.

### Step 8: Validate and Test Service

**⚠️ CRITICAL: Only test inference when service is fully ready**

Before testing or validating the inference endpoint:
1. Service status must be **RUNNING** (not PENDING or STARTING)
2. All instances must be ready - check with `SYSTEM$GET_SERVICE_STATUS()`:
   ```sql
   SELECT SYSTEM$GET_SERVICE_STATUS('<DATABASE>.<SCHEMA>.<SERVICE_NAME>');
   ```
   Verify all containers show `"status":"READY"` and `"message":"Running"`
3. If some instances show `"status":"PENDING"`, wait for them to become READY

**Why this matters:** Testing with partial instances can cause timeouts or inconsistent results. The service load balancer may route requests to instances that are still starting up.

---

#### Step 8a: Confirm Model Version and Functions

**If coming from a continuous workflow** (Steps 1-8 in this session):
- Model name, version, and functions are already known from earlier steps
- Skip to Step 8b using the known values

**If validating an existing service without prior context:**

First, identify which model version the service is using:
```sql
DESCRIBE SERVICE <DATABASE>.<SCHEMA>.<SERVICE_NAME>;
```

Look at `managing_object_name` column to find the model (e.g., `SSARDANA_DB.NEW_EXP.MY_MODEL`).

Then verify the model exists and discover available functions:

**SQL:**
```sql
-- 1. Verify model exists (returns empty list if not found — safe, never errors)
SHOW MODELS LIKE '<MODEL_NAME>' IN SCHEMA <DATABASE>.<SCHEMA>;

-- 2. Discover available functions (only run after confirming model exists above — errors if model not found)
-- Include VERSION = '<VERSION>' if version is known; omit to use the default version
SHOW FUNCTIONS IN MODEL <DATABASE>.<SCHEMA>.<MODEL_NAME> VERSION '<VERSION>';
```

Look at the output from Step 2 for available function names (e.g., `PREDICT`, `PREDICT_PROBA`). Use one of these function names in all subsequent queries.

**Python:**
```python
mv = reg.get_model("<MODEL_NAME>").version("<VERSION>")
print(mv.show_functions())
```

This returns a list of available functions with their input/output signatures.

**Reference:** [ModelVersion API Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-ml/reference/latest/api/model/snowflake.ml.model.ModelVersion) for additional methods like `mv.get_model_signature()`.

**⚠️ IMPORTANT:** Do NOT assume `PREDICT` exists. Different models expose different inference methods.

---

#### Step 8b: Test Inference

**Use the function name discovered in Step 8a for all paths:**

**SQL:**
```sql
-- Replace <FUNCTION_NAME> with actual function from Step 8a
SELECT <SERVICE_NAME>!<FUNCTION_NAME>(col1, col2, ...) FROM input_table;
```

**Python (mv.run):**
```python
# function_name must match one from show_functions() (lowercase)
result = mv.run(test_data, function_name="<function_name>", service_name="<SERVICE_NAME>")
```

**REST API:**

There are two ways to call the REST API depending on where you're calling from:

| Calling From | Endpoint Type | Authentication Required |
|--------------|---------------|------------------------|
| **Snowsight Notebook** | Internal endpoint | No (session context) |
| **External (CLI, apps)** | Public ingress URL | Yes (PAT token) |

---

**REST API from Snowsight Notebook (No Auth Required):**

When calling from a Snowsight Notebook, use the **internal endpoint** which requires no authentication.

First, get the internal endpoint using `mv.list_services()`:

```python
# Get all services for this model version
services_df = mv.list_services()
print(services_df)
```

**`list_services()` returns a DataFrame with these columns:**
- `name`: The name of the service
- `status`: The status of the service
- `inference_endpoint`: The public endpoint (gives privatelink endpoint if session uses privatelink connection)
- `internal_endpoint`: The internal endpoint of the service (use this from notebooks!)
- `autocapture_enabled`: Whether service has autocapture enabled

**Reference:** [ModelVersion.list_services() API Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-ml/reference/latest/api/model/snowflake.ml.model.ModelVersion)

Then make REST calls using the `internal_endpoint`:

```python
import requests

# Get the internal endpoint from list_services() output
services_df = mv.list_services()
internal_endpoint = services_df[services_df['name'] == '<SERVICE_NAME>']['internal_endpoint'].iloc[0]

# Internal endpoint format: http://<service-name>.<namespace>.svc.spcs.internal:5000
# Call the endpoint - NO authorization header needed!
url = f"{internal_endpoint}/<function_name>"  # e.g., /predict or /predict-proba
payload = {"data": [[0, val1, val2, val3]]}

response = requests.post(url, json=payload)
print(response.json())
```

**Key points for Snowsight Notebook:**
- Use `mv.list_services()` to get the `internal_endpoint` column value
- Internal endpoints use HTTP (not HTTPS) on port 5000
- **No `Authorization` header needed** - the notebook session context handles authentication
- This only works from within Snowflake (notebooks, stored procedures, UDFs)

---

**REST API from External Clients (Auth Required):**

Requires: network policy allowing client IP, PAT token, service role grant.

See [REST API Access Setup](#rest-api-access-setup) for full setup instructions.

**⚠️ IMPORTANT: URL Path Transformation**

In REST URLs, underscores (`_`) in method names are replaced by dashes (`-`).

| Python Method | REST Endpoint |
|---------------|---------------|
| `predict()` | `/predict` |
| `predict_proba()` | `/predict-proba` |
| `predict_log_proba()` | `/predict-log-proba` |
| `my_custom_method()` | `/my-custom-method` |

```python
import requests

url = "https://<endpoint-url>/<function_name>"  # Use function from Step 8a (with dashes)
headers = {"Authorization": "Snowflake Token=\"<PAT>\""}
response = requests.post(url, json={"data": [[0, val1, val2]]}, headers=headers)
```

**Note:** When calling from within Snowflake (e.g., a Snowflake notebook), no authentication headers are needed — the request is already authenticated by the session context.

See [REST API Access Setup](#rest-api-access-setup) for details.

### Step 9: Setup REST API Access

**Ask user:**
```
Would you like to set up REST API access to call this service from outside Snowflake?

This is needed if you want to call the inference endpoint from external apps, 
scripts, or services (not via SQL or Python SDK).
```

**⚠️ STOP**: Wait for user response.

**If yes:** Continue with the REST API Access Setup flow below.

**If no:** Deployment complete.

### Next Steps

Ask user:
```
Your inference service is running! What would you like to do next?

1. Set up model monitoring - Track drift and performance
2. Done - Finish here
```

**If monitoring:** Load `../model-monitor/SKILL.md`

**If done:** Skip to Service Management Reference.

---

## REST API Access Setup

To access the inference endpoint from outside Snowflake (e.g., external apps, services, or local scripts), you need proper authentication and network access configured.

### Network Policy (Required)

**Ask user:**
```
Do you have a network policy that allows your client IP to access Snowflake?
```

**⚠️ STOP**: Wait for user response.

**If yes:** Skip to [Service Role Grant](#service-role-grant).

**If no or unsure:** Users calling the endpoint need a network policy allowing their client IP. If user has ACCOUNTADMIN/SECURITYADMIN, help them create one:

```sql
-- Create network rule for client IP
CREATE NETWORK RULE <RULE_NAME> MODE = INGRESS TYPE = IPV4 VALUE_LIST = ('<CLIENT_IP>/32');

-- Create and apply policy
CREATE NETWORK POLICY <POLICY_NAME> ALLOWED_NETWORK_RULE_LIST = ('<RULE_NAME>');
ALTER USER <USERNAME> SET NETWORK_POLICY = <POLICY_NAME>;
```

### Service Role Grant

```sql
GRANT SERVICE ROLE <SERVICE_NAME>!ALL_ENDPOINTS_USAGE TO ROLE <ROLE_NAME>;
```

### Authentication (CLI Only)

**⚠️ CRITICAL: Always use PAT (Programmatic Access Token) for REST API authentication from CLI. Snowsight Notebooks do not require PAT - use the internal endpoint instead (see Step 8b).**

PAT tokens are the standard authentication method for SPCS REST endpoints. Create one in Snowsight under User Menu > Settings > Authentication.

**Do NOT attempt other authentication methods** (JWT, session tokens, etc.) - always ask the user for their PAT token first.

### Test with PAT

**⚠️ MANDATORY: Always ask for PAT token FIRST before any REST endpoint testing.**

**Step 1: Get the endpoint URL:**
```sql
SHOW ENDPOINTS IN SERVICE <SERVICE_NAME>;
```

**Step 2: Understand the model signature:**

Before testing, check the model's input/output signature to understand expected columns and data types:

```python
mv = reg.get_model("<MODEL_NAME>").version("<VERSION>")
print(mv.show_functions())
```

This returns the function signatures showing input columns, output columns, and their data types. See [ModelVersion API Documentation](https://docs.snowflake.com/en/developer-guide/snowpark-ml/reference/latest/api/model/snowflake.ml.model.ModelVersion) for details.

**Step 3: Ask user for PAT token:**
```
To test the REST endpoint, I need a PAT (Programmatic Access Token).

Please provide your PAT token. If you don't have one:
1. Go to Snowsight
2. Click your username (bottom left)
3. Go to Settings > Authentication
4. Create a new Programmatic Access Token

Please paste your PAT token:
```

**⚠️ STOP**: Wait for user to provide PAT token. Do NOT proceed without it.

**Step 4: Generate test script:**

```python
import requests
import json

url = "<ENDPOINT_URL>/<FUNCTION_NAME>"
pat = "<PAT_TOKEN>"

headers = {
    "Authorization": f'Snowflake Token="{pat}"',
    "Content-Type": "application/json"
}
payload = {"data": [[0, <SAMPLE_INPUT>]]}

response = requests.post(url, json=payload, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
```

### REST API Request Format

**⚠️ CRITICAL: The request payload format is specific and must be followed exactly.**

The SPCS inference REST API follows Snowflake's [External Functions Data Format](https://docs.snowflake.com/en/sql-reference/external-functions-data-format).

Each row is a JSON array where the **first element** is the row number (0-based index within the batch). The remaining elements contain the input data, which can be in one of two formats:

**Flat format** - Arguments as separate array elements:
```python
# Single row with 3 input columns (e.g., integer, string, timestamp)
payload = {"data": [[0, 10, "Alex", "2024-01-01 16:00:00"]]}

# Multiple rows
payload = {"data": [
    [0, 10, "Alex", "2024-01-01 16:00:00"],
    [1, 20, "Steve", "2024-02-01 16:00:00"],
    [2, 30, "Alice", "2024-03-01 16:00:00"]
]}
```

**Wide format** - Arguments as a single dict object:
```python
# Single row with named columns
payload = {"data": [[0, {"col1": value1, "col2": value2, "col3": value3}]]}

# Multiple rows
payload = {"data": [
    [0, {"feature1": 5.1, "feature2": 3.5, "feature3": 1.4}],
    [1, {"feature1": 4.9, "feature2": 3.0, "feature3": 1.4}],
    [2, {"feature1": 4.7, "feature2": 3.2, "feature3": 1.3}]
]}
```

**Common mistakes to avoid:**
```python
# WRONG - missing row index
payload = {"data": [[value1, value2, value3]]}
# Error: row index missing

# WRONG - data as dict instead of array of arrays
payload = {"data": {"col1": value1, "col2": value2}}
# Error: various parsing errors

# CORRECT - flat format
payload = {"data": [[0, value1, value2, value3]]}

# CORRECT - wide format
payload = {"data": [[0, {"col1": value1, "col2": value2}]]}
```

The row index (first element) is returned in the response, allowing you to match requests with responses when sending batches.

### REST API Response Format

**⚠️ CRITICAL: Responses are always in wide format (dict), regardless of request format.**

The SPCS inference REST API always returns responses in wide format. Each row contains the row index followed by a dict with the output values. The output column names and types are determined by the model signature (use `mv.show_functions()` to inspect).

**Standard response structure (always wide format):**
```json
{
  "data": [
    [0, {"output_feature_0": <value>, "output_feature_1": <value>}],
    [1, {"output_feature_0": <value>, "output_feature_1": <value>}]
  ]
}
```

- `data[0][0]` = row index (matches the first element in your request)
- `data[0][1]` = dict containing output features

**Correct parsing pattern:**
```python
result = response.json()
data = result.get('data', [[]])[0]

# Output is always a dict at data[1]
if len(data) >= 2 and isinstance(data[1], dict):
    output = data[1]
    # Access specific output features based on model signature
    value_0 = output.get('output_feature_0', 0.0)
    value_1 = output.get('output_feature_1', 0.0)
```

**Common mistake to avoid:**
```python
# WRONG - data[1] is a dict, not a float!
result = float(data[1])  # TypeError: float() argument must be a string or real number, not 'dict'

# CORRECT - access the dict key
result = data[1].get('output_feature_0', 0.0)
```

**Debugging tip:** If you encounter parsing errors, first inspect the raw response:
```python
print(json.dumps(response.json(), indent=2))
```

**⚠️ STOP**: Wait for user response before proceeding.

---

## Common Issues

- **Testing before service ready**: Only test inference when service status is RUNNING and all instances show READY in `SYSTEM$GET_SERVICE_STATUS()`. Testing with PENDING instances causes timeouts.
- **Compute pool not ready**: Resuming a suspended pool can take a few minutes. Tell the user and offer to check status with `SHOW COMPUTE POOLS`
- **Service fails**: Check logs with `CALL SYSTEM$GET_SERVICE_LOGS('<SERVICE_NAME>', 0, 'model-inference')`
- **Missing privileges**: Need `USAGE` on compute pool, `BIND SERVICE ENDPOINT` for HTTP
- **GPU memory issues**: Reduce num_workers if model doesn't fit in GPU memory

---

## Anti-Patterns to Avoid

**Do NOT use `CREATE SERVICE` SQL syntax for model inference** - always use the Python SDK:
```sql
-- WRONG - bypasses model registry integration
CREATE SERVICE my_service IN COMPUTE POOL my_pool ...
```

**Instead:** Use `mv.create_service()` from the model version object - this properly links the service to the registered model.

**Do NOT use `block=False` in `create_service()`** - run the script in background instead:
```python
# WRONG - async mode can cause issues with status tracking
mv.create_service(..., block=False)
```

**Instead:** Run the entire script as a background process and monitor via SQL.

**Do NOT use `RESULT_SCAN(LAST_QUERY_ID())` to filter SHOW results** - column name casing issues cause failures:
```sql
-- WRONG - fragile, causes "invalid identifier" errors
SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE name = 'X'
```

**Do NOT use SHOW as a subquery** - invalid SQL syntax:
```sql
-- WRONG - syntax error
SELECT * FROM (SHOW SERVICES) WHERE name = 'X'
```

**Instead:** Run `DESCRIBE SERVICE` or `SHOW` commands directly and read the output.

**Do NOT attempt JWT or session token authentication for REST endpoints** - these approaches waste time and don't work reliably:
```python
# WRONG - JWT requires keypair setup that users rarely have
token = snow_connection.generate_jwt()

# WRONG - session tokens are for internal Snowflake use
token = conn.rest.token
```

**Instead:** Always ask the user for their PAT (Programmatic Access Token) first. PAT is the standard, supported method for SPCS REST authentication.

---

## Debugging Service Issues

When service is failing or experiencing issues (OOM, crashes, errors), use platform metrics and logs.

### Step 1: Check Platform Metrics

```sql
-- Memory and CPU usage (look for OOM patterns)
SELECT timestamp, metric_name, value, unit, container_name
FROM TABLE(<SERVICE_NAME>!SPCS_GET_METRICS())
WHERE metric_name IN ('container.memory.usage', 'container.cpu.usage', 'container.memory.max_usage')
ORDER BY timestamp DESC
LIMIT 50;

-- GPU metrics (if applicable)
SELECT timestamp, metric_name, value, container_name
FROM TABLE(<SERVICE_NAME>!SPCS_GET_METRICS())
WHERE metric_name LIKE '%gpu%'
ORDER BY timestamp DESC;
```

### Step 2: Check Container Logs

**Model inference container:**
```sql
SELECT * FROM TABLE(<SERVICE_NAME>!SPCS_GET_LOGS())
WHERE container_name = 'model-inference'
ORDER BY timestamp DESC
LIMIT 100;
```

**Proxy container:**
```sql
SELECT * FROM TABLE(<SERVICE_NAME>!SPCS_GET_LOGS())
WHERE container_name = 'proxy'
ORDER BY timestamp DESC
LIMIT 100;
```

**Live logs (current container):**
```sql
CALL SYSTEM$GET_SERVICE_LOGS('<SERVICE_NAME>', 0, 'model-inference');
CALL SYSTEM$GET_SERVICE_LOGS('<SERVICE_NAME>', 0, 'proxy');
```

### Common OOM Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `container.memory.max_usage` near limit | Model too large | Use larger instance or reduce num_workers |
| Repeated container restarts | OOM kills | Check logs for "OOMKilled", reduce batch size |
| GPU memory errors in logs | Model doesn't fit | Reduce num_workers or use instance with more GPU memory |

### Step 3: Event Table (if service is dead)

If service is terminated, use event table directly:

```sql
-- Find your event table
SHOW PARAMETERS LIKE 'event_table' IN ACCOUNT;

-- Logs from event table
SELECT timestamp, value, resource_attributes
FROM <EVENT_TABLE>
WHERE resource_attributes:"snow.service.name" = '<SERVICE_NAME>'
  AND record_type = 'LOG'
ORDER BY timestamp DESC
LIMIT 100;

-- Metrics from event table
SELECT timestamp, record:metric_name::string as metric, record:value as value
FROM <EVENT_TABLE>
WHERE resource_attributes:"snow.service.name" = '<SERVICE_NAME>'
  AND record_type = 'METRIC'
ORDER BY timestamp DESC
LIMIT 100;
```

---

## Service Management Reference

**Suspend/Resume:**
```sql
ALTER SERVICE <SERVICE_NAME> SUSPEND;
ALTER SERVICE <SERVICE_NAME> RESUME;
```

**Auto-suspend (default 30 min):**
```sql
ALTER SERVICE <SERVICE_NAME> SET AUTO_SUSPEND_SECS = <seconds>;
```

**Delete service:**
```sql
DROP SERVICE <SERVICE_NAME>;
```

**Scale service:**
```sql
ALTER SERVICE <SERVICE_NAME> SET MIN_INSTANCES =

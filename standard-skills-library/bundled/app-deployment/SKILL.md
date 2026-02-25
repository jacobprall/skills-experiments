---
name: app-deployment
description: "**[REQUIRED]** for building and deploying applications on Snowflake data. Covers Streamlit in Snowflake (native dashboards using get_active_session()), Snowpark Container Services (SPCS) for Docker-based apps (React, Next.js, custom containers), and end-to-end React/Next.js app builds with SPCS deployment. Routes based on app type: Streamlit for dashboards with standard packages, SPCS for containerized apps or custom requirements. Triggers: dashboard, Streamlit, deploy app, SPCS, container, React, Next.js, web app, UI, frontend, data app, build app, streamlit deploy, compute pool, image repository, service."
---

# App Deployment

Routes application deployment requests to Streamlit in Snowflake (native) or SPCS (containerized).

## Routing Logic

```
Start
  ├─ User wants to BUILD A FULL APP end to end (React/Next.js)?
  │   └─ YES → Use the Build React App playbook below
  │
  ├─ App is Streamlit or user said "dashboard"?
  │   ├─ Standard packages, Snowflake data access only?
  │   │   └─ YES → Use the Streamlit in Snowflake reference below
  │   │
  │   └─ Needs custom packages, external access, or GPU?
  │       └─ YES → Use SPCS Deployment reference below (containerized Streamlit)
  │
  └─ User has an existing Docker app to deploy?
      └─ YES → Use SPCS Deployment reference below
```

**IMPORTANT: When the user says "dashboard" without specifying a technology, default to Streamlit in Snowflake — it's the simplest path for data dashboards.**

## Anti-patterns

| Mis-routing | Why It Happens | Correct Route |
|-------------|----------------|---------------|
| Deploying React to Streamlit in Snowflake | Streamlit in Snowflake only supports Streamlit apps | Use SPCS for React/Next.js |
| Using SPCS for a simple Streamlit dashboard | SPCS adds container management overhead | Use native Streamlit in Snowflake |

---

# Primitive: Streamlit in Snowflake

Build and deploy Streamlit apps that run natively in Snowflake. No Docker, no containers — just Python code.

## Deployment

### Via SQL (recommended for programmatic deployment)

```sql
CREATE OR REPLACE STREAMLIT <db>.<schema>.<app_name>
  ROOT_LOCATION = '@<db>.<schema>.<stage>/<path>'
  MAIN_FILE = 'app.py'
  QUERY_WAREHOUSE = '<warehouse>';
```

Upload files to stage first:

```sql
CREATE STAGE IF NOT EXISTS <db>.<schema>.<stage>;
-- Upload app.py and any supporting files to the stage
PUT file:///path/to/app.py @<db>.<schema>.<stage>/<path>/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
```

### Via snow CLI

```bash
snow streamlit deploy <app_name> \
  --database <db> \
  --schema <schema> \
  --replace
```

Requires a `snowflake.yml` in the project root:

```yaml
definition_version: "2"
entities:
  my_app:
    type: streamlit
    identifier:
      name: <app_name>
    title: "<App Title>"
    main_file: app.py
    pages_dir: pages/
    stage: <stage_name>
```

## Snowflake Connection in App Code

```python
import streamlit as st
from snowflake.snowpark.context import get_active_session

# When deployed in Snowflake — session is pre-configured, no credentials needed
session = get_active_session()

# Query data
df = session.sql("SELECT * FROM my_table LIMIT 100").to_pandas()
st.dataframe(df)
```

### Dual-mode pattern (works locally and deployed)

```python
import streamlit as st

try:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
except Exception:
    conn = st.connection("snowflake")
    session = conn.session()
```

## Constraints

- Deployed apps use the owning role's privileges
- External network access requires an External Access Integration (EAI)
- Packages limited to the Snowflake Anaconda channel
- `st.secrets` is NOT available when deployed in Snowflake — use `get_active_session()`
- File uploads/downloads use a temporary stage

## Example: Minimal Dashboard

```python
import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()

st.title("Revenue Dashboard")
df = session.sql("""
    SELECT segment, order_day, total_revenue
    FROM analytics.daily_revenue
    ORDER BY order_day
""").to_pandas()

st.dataframe(df)
st.line_chart(df.set_index("ORDER_DAY")["TOTAL_REVENUE"])
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using `st.secrets` for credentials | Not available in Snowflake runtime | Use `get_active_session()` |
| Installing pip packages at runtime | Not supported in deployed apps | Use Anaconda channel packages |
| Loading entire large tables into pandas | Memory limits in hosted apps | Filter and aggregate with Snowpark before `.to_pandas()` |

---

# Primitive: SPCS Deployment

Deploy containerized applications to Snowpark Container Services. Works with any Docker-based app.

## Workflow

### 1. Create compute pool

```sql
CREATE COMPUTE POOL <pool_name>
  MIN_NODES = 1
  MAX_NODES = <n>
  INSTANCE_FAMILY = <family>;
```

Instance families:

| Family | Use Case |
|--------|----------|
| `CPU_X64_XS` | Small web apps, APIs |
| `CPU_X64_S` | Medium workloads |
| `CPU_X64_M` | Larger apps, multiple containers |
| `GPU_NV_S` | GPU workloads (1x A10G) |

### 2. Create image repository

```sql
CREATE IMAGE REPOSITORY <db>.<schema>.<repo_name>;
```

### 3. Build and push image

```bash
snow spcs image-registry login --connection <conn>
docker build --platform linux/amd64 -t <image>:latest .
docker tag <image>:latest <registry_url>/<db>/<schema>/<repo>/<image>:latest
docker push <registry_url>/<db>/<schema>/<repo>/<image>:latest
```

Registry URL: `<account>.registry.snowflakecomputing.com`

### 4. Create service

```sql
CREATE SERVICE <service_name>
  IN COMPUTE POOL <pool_name>
  FROM SPECIFICATION $$
  spec:
    containers:
    - name: <app-name>
      image: /<db>/<schema>/<repo>/<image>:latest
      env:
        PORT: "8080"
      resources:
        requests:
          memory: 1Gi
          cpu: 500m
        limits:
          memory: 2Gi
          cpu: 1000m
      readinessProbe:
        port: 8080
        path: /
    endpoints:
    - name: <endpoint-name>
      port: 8080
      public: true
  $$
  MIN_INSTANCES = 1
  MAX_INSTANCES = 1;
```

### 5. Monitor service

```sql
SELECT SYSTEM$GET_SERVICE_STATUS('<service_name>');
SHOW ENDPOINTS IN SERVICE <service_name>;
SELECT SYSTEM$GET_SERVICE_LOGS('<service_name>', 0, '<container_name>');
```

### 6. Update service (preserves URL)

```sql
ALTER SERVICE <service_name> FROM SPECIFICATION $$
<full yaml spec>
$$;
```

## Port alignment

Three ports must match:
- `readinessProbe.port`
- The `PORT` env var (what the app listens on)
- `endpoints[].port`

Mismatches cause failed readiness checks.

## Constraints

- Images must be built for `linux/amd64` platform
- Image path in spec must include leading slash and be case-sensitive
- `DROP SERVICE` + `CREATE SERVICE` changes the URL — use `ALTER SERVICE` for updates
- The service-owning role needs SELECT on tables the app queries

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| `DROP SERVICE` + `CREATE SERVICE` for updates | Changes the ingress URL | Use `ALTER SERVICE ... FROM SPECIFICATION` |
| Building image for `arm64` (Apple Silicon default) | SPCS runs `amd64` only | Always use `--platform linux/amd64` |
| Missing leading slash in image path | Image not found error | `/<db>/<schema>/<repo>/<image>:latest` |

---

# Playbook: Build a React App

End-to-end workflow for building and deploying a React/Next.js app on Snowflake data via SPCS.

## Prerequisites

- Docker installed locally
- `snow` CLI configured
- SPCS privileges (CREATE COMPUTE POOL, CREATE SERVICE)

## Steps

1. **Verify data sources exist** — confirm tables/views the app will query
2. **Scaffold the app** — create Next.js project with Snowflake connection
3. **Build the UI** — create pages, components, data fetching
4. **Containerize** — create Dockerfile for `linux/amd64`
5. **Create SPCS infrastructure** — compute pool, image repository
6. **Push and deploy** — build, tag, push image; create service
7. **Verify** — check service status, test endpoints
8. **Grant access** — grant service roles to consumer roles

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Deploying React to Streamlit in Snowflake | Won't work — SiS only supports Streamlit | Use SPCS |
| Hardcoding Snowflake credentials in app | Security risk, breaks in SPCS | Use service-to-Snowflake auth |
| Skipping readiness probe | Service appears unhealthy | Always configure readinessProbe |

---

## Related Skills

If the user's request also involves these concerns, invoke the corresponding skill:

| Concern | Skill to Invoke | Example |
|---------|----------------|---------|
| Building pipelines or dynamic tables first | `data-transformation` | "Build a pipeline and then create a dashboard" |
| Classifying PII or creating masking policies | `data-security` | "Secure the data and build a dashboard" |
| Multi-domain workflow (2+ concerns) | `standard-router` | "Pipeline + masking + dashboard" — invoke router first for correct ordering |

**Execution order for multi-domain workflows:** data-transformation → data-security → app-deployment

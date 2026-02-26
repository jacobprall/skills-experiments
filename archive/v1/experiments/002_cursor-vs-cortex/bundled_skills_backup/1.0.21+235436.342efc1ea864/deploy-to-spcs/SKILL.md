---
name: deploy-to-spcs
description: "Deploy containerized apps to Snowpark Container Services. Use when: deploying Docker apps, creating SPCS services, pushing images to Snowflake registry."
---

# Deploy to Snowpark Container Services (SPCS)

## Overview
Deploy any containerized application to Snowflake using Snowpark Container Services. Works with any Docker-based app (Next.js, Python, Go, etc.).

## When to Use
- User has a containerized app (Docker) ready to deploy
- User wants to host an app on Snowflake infrastructure
- User mentions SPCS, Snowpark Container Services, or deploying to Snowflake

## Tools Used
- `bash` - Run docker commands, snow CLI
- `snowflake_sql_execute` - Create compute pools, repos, services
- `cortex browser` - Verify deployed apps

## Stopping Points
- ⚠️ Step 1: Confirm app is ready for deployment
- ⚠️ Step 2: Confirm SPCS prerequisites exist
- ⚠️ Step 5: Confirm deployment success
- ⚠️ Step 6: Confirm consumer role access

---

## Workflow

### Step 1: Verify App Readiness

Before deploying, confirm:
- App has a working `Dockerfile`
- App builds successfully locally (`docker build`)
- App exposes a port (default: 8080)

```bash
docker build --platform linux/amd64 -t <image-name>:latest .
```

**⚠️ STOP:** Confirm app builds successfully before proceeding.

---

### Step 2: SPCS Prerequisites

#### Check Current Role
```sql
SELECT CURRENT_ROLE(), CURRENT_USER();
```

#### Check/Create Compute Pool
```sql
SHOW COMPUTE POOLS;

-- If no accessible pool exists:
CREATE COMPUTE POOL <pool_name>
  MIN_NODES = 1
  MAX_NODES = 1
  INSTANCE_FAMILY = CPU_X64_XS;
```

#### Check/Create Image Repository
```sql
SHOW IMAGE REPOSITORIES;

-- If needed:
CREATE IMAGE REPOSITORY <db>.<schema>.<repo_name>;
```

#### Login to Registry
```bash
snow spcs image-registry login --connection <conn>
```

**⚠️ STOP:** Confirm compute pool and image repository exist before proceeding.

---

### Step 3: Create Service Specification

Create `service-spec.yaml`:

```yaml
spec:
  containers:
  - name: <app-name>
    image: /<db>/<schema>/<repo>/<image>:latest
    env:
      HOSTNAME: "0.0.0.0"
      PORT: "8080"
      NODE_ENV: production
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
```

Adjust `resources`, `port`, and `env` based on app requirements.

---

### Step 4: Build and Push Image

```bash
docker build --platform linux/amd64 -t <image-name>:latest .
docker tag <image-name>:latest <registry-url>/<db>/<schema>/<repo>/<image-name>:latest
docker push <registry-url>/<db>/<schema>/<repo>/<image-name>:latest
```

Registry URL format: `<account>.registry.snowflakecomputing.com`

---

### Step 5: Deploy Service

```sql
CREATE SERVICE <service_name>
  IN COMPUTE POOL <pool_name>
  FROM SPECIFICATION $$
  <contents of service-spec.yaml>
  $$
  MIN_INSTANCES = 1
  MAX_INSTANCES = 1;
```

#### Monitor and Get URL
```sql
SELECT SYSTEM$GET_SERVICE_STATUS('<service_name>');
SHOW ENDPOINTS IN SERVICE <service_name>;
```

**IMPORTANT:** Extract the `ingress_url` from SHOW ENDPOINTS and display it to the user.

#### Verify Deployment
```bash
cortex browser open "https://<ingress_url>"
cortex browser snapshot -i  # Verify app loads correctly
```

**⚠️ STOP:** Confirm deployment success with user.

---

### Step 6: Grant Consumer Access

Ask the user: **"What role will consume this service?"**

#### 1. Check Data Access
```sql
SHOW GRANTS TO ROLE <consumer_role>;
```
If required privileges on tables are missing, grant what the service needs:
```sql
GRANT USAGE ON DATABASE <db> TO ROLE <consumer_role>;
GRANT USAGE ON SCHEMA <db>.<schema> TO ROLE <consumer_role>;
-- Grant privileges the service requires (SELECT, INSERT, UPDATE, DELETE, etc.)
GRANT <privileges> ON TABLE <db>.<schema>.<table> TO ROLE <consumer_role>;
```

#### 2. Check Service Endpoint Access
```sql
SHOW GRANTS TO ROLE <consumer_role>;
```
If service role grant is missing:
```sql
GRANT SERVICE ROLE <service_name>!ALL_ENDPOINTS_USAGE TO ROLE <consumer_role>;
```

**⚠️ STOP:** Confirm consumer role can access the service.

---

## Updating a Service

**⚠️ CAUTION:** Always use `ALTER SERVICE` to update an existing service. Never drop and recreate—this changes the service URL and breaks existing integrations.

```bash
docker build --platform linux/amd64 -t <image-name>:latest .
docker tag <image-name>:latest <registry-url>/<db>/<schema>/<repo>/<image-name>:latest
docker push <registry-url>/<db>/<schema>/<repo>/<image-name>:latest
```

```sql
ALTER SERVICE <service_name> FROM SPECIFICATION $$
<full yaml spec>
$$;
```

---

## Troubleshooting

#### Service not starting
```sql
SELECT SYSTEM$GET_SERVICE_LOGS('<service_name>', 0, '<container_name>');
```

#### Service Won't Start
- **Image not found**: The image path in your spec must exactly match the repository structure. Format: `/<db>/<schema>/<repo>/<image>:latest`. Case-sensitive and must include leading slash.
- **Port mismatch**: Three ports must align: `readinessProbe.port` (health check), `PORT` env var (app listens on), and `endpoints.port` (external access). If any differ, the service fails readiness checks.
- **Auth errors**: Registry login expires. Re-run `snow spcs image-registry login --connection <conn>` before pushing images.

#### Permission Errors
- **Missing privileges**: The role that owns the service needs access to any tables/views the app queries. Common issue when app works locally but fails in SPCS.
  ```sql
  GRANT SELECT ON TABLE <db>.<schema>.<table> TO ROLE <role>;
  GRANT DELETE ON TABLE <db>.<schema>.<table> TO ROLE <role>;  -- if app deletes data
  ```

## Output
- Deployed SPCS service URL
- Service status confirmation
- Consumer role access configured

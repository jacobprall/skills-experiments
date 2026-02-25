---
type: primitive
name: spcs-deployment
domain: app-development
snowflake_docs: "https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview"
---

# SPCS Deployment

Deploy containerized applications to Snowpark Container Services. Works with any Docker-based app (Next.js, Python, Go, etc.).

## Syntax

### Create compute pool

```sql
CREATE COMPUTE POOL <pool_name>
  MIN_NODES = 1
  MAX_NODES = <n>
  INSTANCE_FAMILY = <family>;
```

### Create image repository

```sql
CREATE IMAGE REPOSITORY <db>.<schema>.<repo_name>;
```

### Push image

```bash
snow spcs image-registry login --connection <conn>
docker build --platform linux/amd64 -t <image>:latest .
docker tag <image>:latest <registry_url>/<db>/<schema>/<repo>/<image>:latest
docker push <registry_url>/<db>/<schema>/<repo>/<image>:latest
```

Registry URL: `<account>.registry.snowflakecomputing.com`

### Create service

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

### Update service (preserves URL)

```sql
ALTER SERVICE <service_name> FROM SPECIFICATION $$
<full yaml spec>
$$;
```

### Monitor service

```sql
SELECT SYSTEM$GET_SERVICE_STATUS('<service_name>');
SHOW ENDPOINTS IN SERVICE <service_name>;
SELECT SYSTEM$GET_SERVICE_LOGS('<service_name>', 0, '<container_name>');
```

## Parameters

### Instance families

| Family | Use Case |
|--------|----------|
| `CPU_X64_XS` | Small web apps, APIs |
| `CPU_X64_S` | Medium workloads |
| `CPU_X64_M` | Larger apps, multiple containers |
| `GPU_NV_S` | GPU workloads (1x A10G) |

### Service spec key fields

| Field | Required | Description |
|-------|----------|-------------|
| `containers[].image` | Yes | Full path with leading slash: `/<db>/<schema>/<repo>/<image>:latest` |
| `containers[].resources` | Yes | CPU/memory requests and limits |
| `containers[].readinessProbe` | Recommended | Port and path for health check |
| `endpoints[].port` | Yes | Must match the port the app listens on |
| `endpoints[].public` | No | `true` for internet-accessible endpoints |

### Port alignment

Three ports must match: `readinessProbe.port`, the `PORT` env var (what the app listens on), and `endpoints[].port`. Mismatches cause failed readiness checks.

## Constraints

- Images must be built for `linux/amd64` platform.
- Image path in spec must include leading slash and be case-sensitive.
- Registry login expires — re-run `snow spcs image-registry login` before pushing.
- `DROP SERVICE` then `CREATE SERVICE` changes the URL. Use `ALTER SERVICE` for updates.
- The service-owning role needs `SELECT`/etc. on any tables the app queries.

## Examples

### Grant consumer access

```sql
GRANT SERVICE ROLE <service_name>!ALL_ENDPOINTS_USAGE TO ROLE <consumer_role>;
GRANT USAGE ON DATABASE <db> TO ROLE <consumer_role>;
GRANT USAGE ON SCHEMA <db>.<schema> TO ROLE <consumer_role>;
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| `DROP SERVICE` + `CREATE SERVICE` for updates | Changes the ingress URL, breaking integrations | Use `ALTER SERVICE ... FROM SPECIFICATION` |
| Building image for `arm64` (e.g., Apple Silicon default) | SPCS runs `amd64` only | Always use `--platform linux/amd64` |
| Missing leading slash in image path | Image not found error | `/<db>/<schema>/<repo>/<image>:latest` |

## References

- [Snowflake Docs: SPCS](https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview)

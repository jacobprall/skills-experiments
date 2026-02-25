---
name: openflow-setup-discovery
description: Discover Openflow deployments and runtimes for the current Snowflake connection. Load when cache is missing or incomplete.
---

# Infrastructure Discovery

Discover Openflow deployments and runtimes, then write results to cache.

## Prerequisites

The setup workflow has already selected `CONNECTION`. Use that value with `-c <CONNECTION>` for all `snow sql` commands.

For diagnostic queries (Alternative Discovery section), you may also need the `event_table` from the cache. If the cache exists, check:

```bash
cat ~/.snowflake/cortex/memory/openflow_infrastructure_*.json | jq '.deployments[].event_table'
```

## Step 1: Find Deployments

```bash
snow sql -c <CONNECTION> -q "SHOW OPENFLOW DATA PLANE INTEGRATIONS;" --format json
```

| Result | Action |
|--------|--------|
| Empty result | No Openflow deployed. Tell user: "No Openflow deployments found in this account." |
| Returns rows | Extract deployment info, continue |
| Permissions error | User/Role lacks grants. Tell user to check Openflow permissions in Snowflake. |

For each deployment, get details:

```bash
snow sql -c <CONNECTION> -q "DESCRIBE INTEGRATION <data_plane_integration>;" --format json
```

Extract: `DATA_PLANE_ID`, `EVENT_TABLE`

**Event Table Scope:** The event table may be configured per-deployment or shared across multiple deployments in an account. Store the `EVENT_TABLE` value with each deployment in the cache. When querying events, use the event table associated with the specific deployment you're investigating.

## Step 2: Find Runtimes

```bash
snow sql -c <CONNECTION> -q "SHOW OPENFLOW RUNTIME INTEGRATIONS;" --format json
```

For each runtime, extract from `OAUTH_REDIRECT_URI`:
- Host: the domain before the runtime path
- Runtime key: the path segment before `/login/oauth2/...`
- URL: `https://{host}/{runtime_key}/nifi-api`

### Detect Deployment Type from URL

| Pattern | Type |
|---------|------|
| Host starts with `of--` | SPCS |
| Host contains `snowflake-customer.app` | BYOC |

## Step 3: SPCS Only - Find Runtime Role

If deployment type is SPCS, discover runtime role.

### High Signal: Event Table Grants

```bash
snow sql -c <CONNECTION> -q "SHOW GRANTS ON TABLE <event_table>;" --format json | jq '.[] | select(.privilege == "INSERT") | .grantee_name'
```

Roles with INSERT grants are likely runtime roles. Present to the user for validation.

### Medium Signal: Integration Grants (if no event table)

```bash
snow sql -c <CONNECTION> -q "SELECT grantee_name, COUNT(*) as eai_count FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_ROLES WHERE granted_on = 'INTEGRATION' AND privilege = 'USAGE' AND grantee_name LIKE 'OPENFLOW%' GROUP BY grantee_name ORDER BY eai_count DESC LIMIT 5;" --format json
```

### List Attached EAIs

```bash
snow sql -c <CONNECTION> -q "SHOW GRANTS TO ROLE <runtime_role>;" --format json | jq '[.[] | select(.granted_on == "INTEGRATION" and .privilege == "USAGE") | .name]'
```

Present to the user for validation.

## Step 4: Write Cache

Create cache directory if not exists:

```bash
mkdir -p ~/.snowflake/cortex/memory
```

Update the cache file with the `deployments` section (merge with existing cache):

```bash
jq '.discovered_at = "<ISO_TIMESTAMP>" | .deployments = [<DEPLOYMENTS_ARRAY>]' \
  ~/.snowflake/cortex/memory/openflow_infrastructure_${CONNECTION}.json > tmp && mv tmp ~/.snowflake/cortex/memory/openflow_infrastructure_${CONNECTION}.json
```

**Deployments structure:**

```json
{
  "data_plane_integration": "<name>",
  "data_plane_id": "<id>",
  "deployment_type": "<spcs|byoc>",
  "event_table": "<table>",
  "runtimes": [
    {
      "runtime_integration": "<name>",
      "runtime_name": "<key>",
      "url": "https://<host>/<key>/nifi-api",
      "runtime_role": "<role>",
      "attached_eais": ["<eai1>", "<eai2>"]
    }
  ]
}
```

Notes:
- For BYOC: omit `runtime_role` and `attached_eais`
- `nipyapi_profile` is added by the auth step, not discovery
- `tooling` section is managed by setup-tooling, not discovery
- See `references/core-session.md` for full cache schema

## Alternative: Discovery from Event Table

If `SHOW OPENFLOW RUNTIME INTEGRATIONS` returns unexpected results, query the event table directly:

```sql
SELECT DISTINCT
  RESOURCE_ATTRIBUTES:"k8s.namespace.name"::STRING as namespace,
  REGEXP_SUBSTR(RESOURCE_ATTRIBUTES:"k8s.namespace.name"::STRING, 'runtime-(.+)', 1, 1, 'e', 1) as runtime_name
FROM <event_table>
WHERE RESOURCE_ATTRIBUTES:"k8s.namespace.name"::STRING ILIKE 'runtime-%'
  AND TIMESTAMP >= DATEADD(day, -7, CURRENT_TIMESTAMP())
```

**Note:** This may reveal:
- Incompletely deployed runtimes that emitted events before failing
- Previously removed runtimes that still have event history
- Runtimes not yet registered as integrations

Compare results with the integration list to identify discrepancies for investigation. See `references/platform-diagnostics.md` for runtime troubleshooting.

## Next Step

After writing cache, **continue** to `references/setup-main.md` Step 3 to validate the cache and create nipyapi profiles.

Do not stop here - the setup is not complete until profiles are created and connectivity is verified.

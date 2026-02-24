---
name: openflow-core-session
description: Session initialization and cache management for Openflow. Always load this reference and follow the session check workflow at session start.
---

# Openflow Session Management

This reference handles session initialization. Load this at the start of every Openflow session and follow the workflow below.

## Session Start Workflow

Execute these steps at the start of each Openflow session:

### Step 1: Check Cache File

```bash
ls ~/.snowflake/cortex/memory/openflow_infrastructure_*.json 2>/dev/null
```

| Result | Action |
|--------|--------|
| No files found | Load `references/setup-main.md` and follow Fresh Setup |
| One or more files | Continue to Step 2 |

### Step 2: Validate Cache Contents

```bash
cat ~/.snowflake/cortex/memory/openflow_infrastructure_*.json 2>/dev/null | jq '{
  connection: .connection,
  tooling: .tooling.preferred,
  runtimes: [.deployments[].runtimes[] | {name: .runtime_name, profile: .nipyapi_profile}]
}'
```

| Result | Action |
|--------|--------|
| No `tooling` section | Load `references/setup-main.md` for tooling setup |
| No runtimes listed | Load `references/setup-main.md` for discovery |
| Runtimes have no `nipyapi_profile` | Load `references/setup-main.md` for profile creation |
| All sections present | Continue to Step 3 |

### Step 3: Match Profile to Runtime

The cache contains `nipyapi_profile` for each runtime. Verify the profile exists in profiles.yml.

```bash
# Get expected profiles from cache
cat ~/.snowflake/cortex/memory/openflow_infrastructure_*.json 2>/dev/null | jq -r '.deployments[].runtimes[] | "\(.runtime_name): \(.nipyapi_profile)"'

# Check which profiles exist
grep -E "^[a-zA-Z].*:$" ~/.nipyapi/profiles.yml 2>/dev/null | tr -d ':' || echo "No profiles"
```

| Result | Action |
|--------|--------|
| No profiles file | Load `references/setup-main.md` for profile creation |
| Cache profile not in profiles.yml | Load `references/setup-main.md` to recreate profile |
| Single runtime in cache, profile exists | Use that profile |
| Multiple runtimes in cache | Ask user: "Which runtime do you want to work with?" then use that runtime's `nipyapi_profile` |

### Step 4: Validate nipyapi Version

Check the nipyapi version to ensure full functionality:

```bash
nipyapi --version
```

| Result | Action |
|--------|--------|
| `nipyapi 1.2.0` or higher | Continue to Step 5 |
| Lower version or error | Load `references/setup-tooling.md` and follow "Upgrade nipyapi" section |

**Why this matters:** Older nipyapi versions may be missing CLI commands or modules that the skill references. Version 1.2.0+ includes the bulletins module and other essential features.

### Step 5: Session Ready

Once cache, profile, and version are validated:
1. Note the connection name (from cache `connection` field)
2. Note the selected profile name (from cache `nipyapi_profile` for chosen runtime)
3. Return to main skill for user intent routing
4. Use `--profile <profile_name>` with all nipyapi commands
5. Use `-c <connection>` with all snow sql commands

**Do not repeat this check before every command** - only at session start or when user switches connections.

---

## Connection and Profile Commands

### Snowflake CLI

**Always use `-c <connection>` with every `snow sql` command.**

```bash
# Correct - explicit connection
snow sql -c myconnection -q "SHOW OPENFLOW DATA PLANE INTEGRATIONS;"

# Wrong - may use wrong account
snow sql -q "SHOW OPENFLOW DATA PLANE INTEGRATIONS;"
```

The connection name is stored in the cache file's `connection` field.

### nipyapi CLI

**Always use `--profile <name>` with every nipyapi command.**

```bash
# Correct - explicit profile
nipyapi --profile myprofile ci get_status

# Wrong - may connect to wrong runtime
nipyapi ci get_status
```

The `--profile` option should come before the subcommand.

### nipyapi Python

**When writing Python scripts, activate the profile at the start:**

```python
import nipyapi

nipyapi.profiles.switch('myprofile')

# All subsequent calls use the activated profile
status = nipyapi.canvas.get_process_group_status('root')
```

---

## Cache File Location

```
~/.snowflake/cortex/memory/openflow_infrastructure_{connection}.json
```

Where `{connection}` is the name of the Snowflake CLI connection.

## Cache File Schema

### SPCS Example

```json
{
  "connection": "az1",
  "discovered_at": "2025-12-18T15:30:00Z",
  "stale_after_days": 30,

  "tooling": {
    "preferred": "nipyapi",
    "python_command": "python3",
    "pip_command": "uv pip",
    "updated_at": "2025-12-21T10:00:00Z"
  },

  "deployments": [
    {
      "data_plane_integration": "OPENFLOW_DATAPLANE_...",
      "data_plane_id": "5fac6f12-...",
      "event_table": "OPENFLOW.OPENFLOW.EVENTS",
      "admin_role": "OPENFLOWADMIN",
      "deployment_host": "of--account.snowflakecomputing.app",
      "deployment_type": "spcs",
      "runtimes": [
        {
          "runtime_integration": "OPENFLOW_RUNTIME_...",
          "runtime_role": "OPENFLOWRUNTIMEROLE_...",
          "attached_eais": ["BOX_EAI", "SHAREPOINT_EAI"],
          "runtime_name": "My Runtime",
          "runtime_key": "my-runtime",
          "url": "https://of--account.../my-runtime/nifi-api",
          "nipyapi_profile": "account_runtime_name"
        }
      ]
    }
  ]
}
```

### BYOC Example

```json
{
  "connection": "default",
  "discovered_at": "2025-12-23T22:00:00Z",
  "stale_after_days": 30,

  "tooling": {
    "preferred": "nipyapi",
    "python_command": "python3",
    "pip_command": "pip3",
    "updated_at": "2025-12-23T22:00:00Z"
  },

  "deployments": [
    {
      "data_plane_integration": "OPENFLOW_DATAPLANE_...",
      "data_plane_id": "fbaaa22f-...",
      "event_table": "OPENFLOW.OPENFLOW.EVENTS",
      "deployment_host": "xxx.openflow.region.snowflake-customer.app",
      "deployment_type": "byoc",
      "runtimes": [
        {
          "runtime_integration": "OPENFLOW_RUNTIME_...",
          "runtime_name": "dchruntime",
          "runtime_key": "dchruntime",
          "url": "https://xxx.openflow.region.snowflake-customer.app/dchruntime/nifi-api",
          "nipyapi_profile": "account_connection_runtime"
        }
      ]
    }
  ]
}
```

### SPCS vs BYOC Fields

| Field | SPCS | BYOC |
|-------|------|------|
| `admin_role` | Present | Omitted |
| `runtime_role` | Present | Omitted |
| `attached_eais` | Present | Omitted |

BYOC deployments use explicit key-pair authentication and have direct network access, so they do not require admin_role, runtime_role, or EAI configuration.

## Field Reference

### Tooling Section

| Field | Description |
|-------|-------------|
| `preferred` | User's preferred tool: `nipyapi` or `curl` |
| `python_command` | Detected python command: `python3` or `python` |
| `pip_command` | Detected pip command: `uv pip`, `pip3`, or `pip` |

**Use cached commands:** When running python or pip, use the cached values instead of hardcoding.

### Runtime Fields

| Field | Description |
|-------|-------------|
| `runtime_name` | Human-readable name from Control Plane UI |
| `runtime_key` | URL segment used in API paths |
| `url` | Full NiFi API URL for this runtime |
| `nipyapi_profile` | Profile name for nipyapi commands |
| `runtime_role` | Snowflake role for runtime operations (SPCS only) |
| `attached_eais` | External Access Integrations granted (SPCS only) |

### Deployment Fields

| Field | Description |
|-------|-------------|
| `deployment_host` | Base hostname for the deployment |
| `deployment_type` | `spcs` or `byoc` |
| `event_table` | Table for querying runtime logs |
| `admin_role` | Snowflake admin role for deployment operations (SPCS only) |

## Related References

- `references/setup-main.md` - Populates the cache via discovery workflow
- `references/core-guidelines.md` - Tool hierarchy and safety reminders

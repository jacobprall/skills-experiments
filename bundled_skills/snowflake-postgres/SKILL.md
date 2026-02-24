---
name: snowflake-postgres
description: "**[REQUIRED]** Use for **ALL** requests involving Snowflake Postgres: create instance, list instances, suspend, resume, reset credentials, describe instance, import connection. Triggers: 'postgres', 'pg', 'create instance', 'show instances', 'suspend', 'resume', 'reset credentials', 'rotate password', 'reset access', 'import connection', 'network policy', 'my IP'."
---

# Snowflake Postgres

## When to Use

When a user wants to manage Snowflake Postgres instances via Snowflake SQL.

## Setup

1. **Check for connection**: Verify a saved connection using the `connect/SKILL.md` workflow.
2. **Load references** as needed based on intent.

## Connection Storage (PostgreSQL Standard Files)

Connections use PostgreSQL's native configuration files instead of custom formats. This provides:
- Compatibility with all PostgreSQL tools (`psql`, pgAdmin, DBeaver, etc.)
- OS-enforced security (PostgreSQL rejects `.pgpass` if permissions are wrong)
- Separation of connection metadata from secrets

Never ask for credentials in chat.

### Service File: `~/.pg_service.conf`

PostgreSQL service file - stores named connection profiles (no passwords). Allows connecting with `psql service=<name>` instead of specifying all parameters:

```ini
[my_instance]
host=abc123.snowflakecomputing.com
port=5432
dbname=postgres
user=snowflake_admin
sslmode=require
```

Users can connect manually with: `psql service=my_instance` (if psql is installed)

### Password File: `~/.pgpass`

PostgreSQL password file - stores credentials separately from connection profiles. PostgreSQL clients automatically look up passwords from this file when connecting. Must have `chmod 600` permissions.

**⚠️ NEVER display `.pgpass` contents or format with actual passwords.** Always use `pg_connect.py` to manage passwords - it handles the file securely without exposing credentials in chat.

**Running queries:** Use `psql "service=<instance_name>" -c "<SQL>"` — authentication is handled automatically via the service file and pgpass. Never read or echo credential files.

## Progress Tracking

For multi-step operations, use `system_todo_write` to show progress:

```
┌──────────────────┬──────────────────────────────────────────────────────┐
│ Scenario         │ Create Todos                                         │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Create + setup   │ Create instance → Save connection → Network policy   │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Batch operations │ One todo per instance/object                         │
└──────────────────┴──────────────────────────────────────────────────────┘
```

**Rules:**
- Mark `in_progress` BEFORE starting each step
- Mark `completed` IMMEDIATELY after finishing
- Add new todos if issues are discovered mid-workflow

## Intent Detection

| Intent | Trigger Phrases | Route |
|--------|-----------------|-------|
| **MANAGE** | "create instance", "show instances", "list instances", "suspend", "resume", "describe", "rotate password", "reset credentials", "reset access" | Load `manage/SKILL.md` |
| **CONNECT** | "my IP", "network policy", "can't connect", "add IP", "import connection" | Load `connect/SKILL.md` |

### Unrecognized or Extended Operations

If the user's request involves Snowflake Postgres but doesn't match the intents above (e.g., fork, replica, maintenance window, upgrade, POSTGRES_SETTINGS):

1. **First** check `references/documentation.md` for the relevant doc URL
2. **Fetch** the official docs to get current syntax
3. **Apply** the same safety rules (approval for billable/destructive operations, no secrets in chat)

Examples of operations requiring doc lookup:
- Fork instance / point-in-time recovery
- Create read replica
- Set maintenance window
- Modify POSTGRES_SETTINGS
- Major version upgrades

## Routing

⚠️ **MANDATORY: Execute Sub-Skill Immediately**

After detecting intent, you MUST:
1. Load the sub-skill file
2. Execute its workflow **in this same response**
3. Do NOT stop after loading - continue to completion

| Intent | Action |
|--------|--------|
| **MANAGE** | Load `manage/SKILL.md` → Execute SQL immediately |
| **CONNECT** | Load `connect/SKILL.md` → Execute workflow immediately |

❌ **WRONG:** Load skill, then stop or explain
✅ **RIGHT:** Load skill, then execute the command/workflow

## Global Safety Rules

- Never ask for passwords in chat or echo secrets.
- **Never use `cat`, `echo`, heredoc (`<<`), or any shell command to create files containing `access_roles` or passwords** - these appear in chat history.
- Always require explicit approval for billable actions and network policy changes.
- For DESCRIBE responses, never show `access_roles`.
- For CREATE responses, never show raw SQL results - `access_roles` contains passwords.
- If any output might include secrets (passwords, access tokens), never display them in chat. Scripts save secrets to secure files (`~/.pgpass` with 0600 permissions) without echoing them.
- **For CREATE INSTANCE: MUST use `pg_connect.py --create`** - never use SQL tool directly. The script saves the connection automatically.
- **For RESET ACCESS: MUST use `pg_connect.py --reset`** - never use SQL tool directly. The script saves the password automatically.
- **Do NOT ask if user wants to save after CREATE/RESET** - the scripts save automatically.
- **Do NOT run RESET after CREATE** - CREATE already saves the password. RESET is only for rotating passwords later.


## Tools

### Tool: ask_user_question

**Description:** Ask the user to choose from a fixed list of options.

**When to use:** Present configuration menus (instance size, storage, HA, version, network policy).

### Script: network_policy_check.py

**Description:** Check whether an IP is allowed by a Snowflake network policy.

**Usage:**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network_policy_check.py \
  --policy-name <POLICY_NAME> \
  [--ip <IP>]
```

### Script: pg_connect.py

**Description:** Manage Snowflake Postgres connections. Handles CREATE, RESET, and connection file management (`~/.pg_service.conf` and `~/.pgpass`) without exposing credentials.

**Usage (create instance - executes SQL + saves connection):**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pg_connect.py \
  --create \
  --instance-name <NAME> \
  --compute-pool <STANDARD_M|STANDARD_L|...> \
  --storage <GB> \
  [--auto-suspend-secs <SECONDS>] \
  [--enable-ha] \
  [--postgres-version <VERSION>] \
  [--network-policy <POLICY_NAME>] \
  [--snowflake-connection <NAME>]
```

**Usage (reset credentials - executes SQL + updates password):**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pg_connect.py \
  --reset \
  --instance-name <NAME> \
  [--role <snowflake_admin|application>] \
  [--host <HOST>] \
  [--snowflake-connection <NAME>]
```
Use `--host` to create the service entry if it doesn't exist (e.g., from DESCRIBE output).

**Usage (list saved connections):**
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pg_connect.py --list
```

Uses Snowflake connection from `~/.snowflake/connections.toml` or environment variables. Use `--snowflake-connection` to specify a named connection.

## Output

Routes to the correct workflow and returns the results from that sub-skill.

## Stopping Points Summary

| Operation | Approval Required |
|-----------|-------------------|
| CREATE instance | ⚠️ Yes (billable) |
| SUSPEND instance | ⚠️ Yes (drops connections) |
| Network policy changes | ⚠️ Yes |
| RESUME instance | No |
| LIST/DESCRIBE | No |

**Resume rule:** On approval ("yes", "proceed", "approved"), continue without re-asking.

## Troubleshooting

**Error: `invalid property 'STORAGE_SIZE'`**
→ Use `STORAGE_SIZE_GB` (not `STORAGE_SIZE`)

**Error: `Missing option(s): [AUTHENTICATION_AUTHORITY]`**
→ Add `AUTHENTICATION_AUTHORITY = POSTGRES`

**Error: Network policy not working**
→ Verify rule uses `MODE = POSTGRES_INGRESS`

**Error: Connection refused**
→ IP not in network policy. Offer to check IP and add to policy.

## References

- `references/instance-options.md` - Valid compute families, storage limits
- `references/instance-states.md` - Instance state descriptions
- `references/documentation.md` - Official Snowflake docs URLs (fallback for commands not covered here)

---
name: snowflake-postgres-manage
description: "Manage Snowflake Postgres instances: list, describe, create, suspend, resume."
parent_skill: snowflake-postgres
---

# Snowflake Postgres - Manage

## When to Load

From `snowflake-postgres/SKILL.md` when intent is MANAGE.

**Note:** All `<SKILL_DIR>` placeholders must be absolute paths.

## Workflow

### List Instances

```sql
SHOW POSTGRES INSTANCES;
```

Present results showing name, state, compute_family, storage_size_gb.

If the user wants to import connections, compare instance names to saved connection names and offer to add missing ones:
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pg_connect.py --list
```

### Describe Instance

```sql
DESCRIBE POSTGRES INSTANCE <instance_name>;
```

⚠️ **CRITICAL:** DESCRIBE response contains credentials in `access_roles`.
- DO NOT display raw SQL results
- Show only: name, state, host, port, database, compute_family, storage_size_gb

### Create Instance

**⚠️ MANDATORY STOPPING POINT** - Creates billable resources.

#### Step 1: Gather Requirements

**Load** `references/instance-options.md` for valid options.

**Ask** user with ready-to-go defaults:
```
I'll create a Postgres instance with these defaults:

  Name:     pg_[timestamp]
  Size:     STANDARD_M (1 core, 4GB)
  Storage:  10 GB
  HA:       Off

Type yes to proceed, or tell me what to change.
Type "options" to see all available configurations.
```

**If user says "options":** Use `ask_user_question` to show what they can change:
```
What would you like to configure?

1. Instance size (currently: STANDARD_M)
2. Storage (currently: 10 GB)
3. High availability (currently: Off)
4. Postgres version (currently: latest)
5. Network policy (currently: none)
```

If the user asks for sizes or limits, load `references/instance-options.md`.

**If user gives partial info:** Merge with defaults and confirm.

#### Step 2: Validate Parameters

Validate against `references/instance-options.md`:
- Compute family exists and matches type (Standard/Burstable/HighMem)
- Storage within limits (Burstable max 100GB)
- HA not available for Burstable instances
- Network policy exists if specified

#### Step 3: Get Approval

Present full configuration to user:
```
I will create a Postgres instance:

| Setting | Value |
|---------|-------|
| Name | [name] |
| Compute | [compute_family] ([cores] cores, [memory]) |
| Storage | [size] GB |
| Postgres | [version] |
| High Availability | [Yes/No] |
| Network Policy | [policy_name or "None - configure after"] |

⚠️ This creates a billable resource.
Proceed? (yes/no)
```

**NEVER proceed without explicit approval.**

#### Step 4: Execute

**⚠️ MANDATORY: Use `pg_connect.py --create`** - this is the ONLY way to create instances that does not show passwords. Do NOT use `snowflake_sql_execute` or any SQL tool. The script:
1. Executes CREATE SQL internally
2. Saves connection to `~/.pg_service.conf` automatically
3. Saves password to `~/.pgpass` automatically
4. Never exposes passwords in chat

**Do NOT ask the user if they want to save the connection - the script saves automatically.**

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pg_connect.py \
  --create \
  --instance-name <name> \
  --compute-pool <compute_family> \
  --storage <size> \
  [--auto-suspend-secs <seconds>] \
  [--enable-ha] \
  [--postgres-version <version>] \
  [--network-policy <policy_name>] \
  [--snowflake-connection <name>]
```

**Parameters:**
- `--compute-pool` - `STANDARD_M`, `STANDARD_L`, etc. (not `STANDARD_S`)
- `--storage` - Size in GB (10-10000)
- `--auto-suspend-secs` - Inactivity timeout (optional)
- `--enable-ha` - Enable high availability
- `--postgres-version` - Postgres version (e.g., 16)
- `--network-policy` - Network policy name (must exist)
- `--snowflake-connection` - Snowflake CLI connection name (optional)

**Extended parameters:** If the user requests parameters not supported by the script (e.g., `MAINTENANCE_WINDOW_START`), consult `references/documentation.md` for current syntax and use raw SQL via SQL tool (but warn user credentials will be visible).

#### Step 5: After Success

**⚠️ Do NOT run `--reset` after CREATE.** The `--create` script already saved the password. RESET is only for rotating passwords later.

The script already saved the connection. Just relay the script's output to the user:
> ✅ Created **[name]** ([compute], [storage]GB)
> ⏳ Instance is provisioning (1-2 minutes)
> ✅ Connection saved to `~/.pg_service.conf`
> ✅ Password saved to `~/.pgpass`
> Connect with: `psql "service=[name]"`

Then offer network policy setup (can do while provisioning):
> Would you like to configure network access so you can connect?

### Suspend Instance

**⚠️ MANDATORY STOPPING POINT** - Get approval first, then execute.

**Step 1:** Present to user what will happen:
```
I will suspend [instance_name]. This will:
- Stop compute billing (storage billing continues)
- Drop all active connections

Proceed? (yes/no)
```

**Step 2:** After user approves, execute:
```sql
ALTER POSTGRES INSTANCE <instance_name> SUSPEND;
```

### Resume Instance

```sql
ALTER POSTGRES INSTANCE <instance_name> RESUME;
```

Note: May take 3-5 minutes. Connection string remains the same.

### Reset Credentials (Rotate Password)

**⚠️ MANDATORY STOPPING POINT**

Before attempting reset, verify the instance exists and you have access. See the connect skill for workflows.

Explain impact:
```
I will reset credentials for [instance_name] and role [role_name]. This will:
- Generate a new password for the role (only `snowflake_admin` or `application`)
- Invalidate the old password (existing connections may drop)

Proceed? (yes/no)
```

**⚠️ After approval, use `pg_connect.py --reset` (NOT `snowflake_sql_execute`)** - the script handles the SQL internally and updates ~/.pgpass. Executing RESET via SQL tool would expose the new password in chat.

```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pg_connect.py \
  --reset \
  --instance-name <instance_name> \
  [--role <role_name>] \
  [--host <host>] \
  [--snowflake-connection <name>]
```

- Supported roles: `snowflake_admin` (default) and `application`.
- `--host` - Creates service entry if missing (use host from DESCRIBE)
- `--snowflake-connection` - Snowflake CLI connection name (optional)

## Output

- List/Describe results (safe fields only)
- Confirmation of create/suspend/resume
- Import guidance for local connections file update

For LIST results:
- Let the SQL result table speak for itself, but you may mention they need to use ctrl+t to expand the table
- Add only a brief summary: count + any notable states (e.g., "8 instances, 2 suspended") and offer to show other details
- Don't create a second markdown table

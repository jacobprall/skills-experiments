---
name: snowflake-postgres-connect
description: "Network policy setup and connectivity checks. Triggers: 'my IP', 'network policy', 'can't connect', 'add IP', 'import connection'."
parent_skill: snowflake-postgres
---

# Snowflake Postgres - Connect

## When to Load

From `snowflake-postgres/SKILL.md` when intent is CONNECT.

**Note:** All `<SKILL_DIR>` placeholders must be absolute paths.

## Workflow

### Verify Saved Connection (Before Any Operations)

Before running any workflow that requires a saved connection, read existing saved connections:
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pg_connect.py --list
```
If the target instance isn't present, use the import flow below.

### Import Connection

For instances created outside Cortex Code (UI, CLI, etc.).

#### Step 1: List Existing Instances

```sql
SHOW POSTGRES INSTANCES;
```

List saved connections (no secrets) and compare against instance names:
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pg_connect.py --list
```
`<SKILL_DIR>` must be an absolute path.

If any instances are not saved, ask:
```
I see these instances not in your connections file: [list].
Would you like to add one? If yes, I can pre-fill host/port/user, and you can add the password locally.
```

#### Step 2: Get Instance Details

```sql
DESCRIBE POSTGRES INSTANCE <instance_name>;
```

⚠️ **DESCRIBE may contain sensitive metadata in `access_roles`** - do NOT display raw SQL results. Extract only: `host`.

#### Step 3: Add Connection Locally (No Secrets in Chat)

**Never** ask the user to paste a password into chat. Connections use standard PostgreSQL files.

Provide what we know:
- `host` from DESCRIBE
- `port` 5432
- `database` `postgres`
- `user` `snowflake_admin`
- `sslmode` `require`

Tell user to add to `~/.pg_service.conf`:
```ini
[<instance_name>]
host=<host>
port=5432
dbname=postgres
user=snowflake_admin
sslmode=require
```

**⚠️ For password management, always use file-based methods** - never show passwords or `.pgpass` format.

If the user needs new credentials, use `pg_connect.py --reset` (it handles SQL internally and updates ~/.pgpass):
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/pg_connect.py \
  --reset \
  --instance-name <instance_name> \
  --host <host_from_describe> \
  [--role <snowflake_admin|application>] \
  [--snowflake-connection <name>]
```
Use `--host` to create the connection if it doesn't exist. `<SKILL_DIR>` must be an absolute path. **Never execute RESET ACCESS via SQL tool** - passwords would appear in chat.

#### Step 4: Confirm

After the user has updated their connection (manually or via script):
```
✅ Connection **[instance_name]** ready
   Host: [host]
   Service file: ~/.pg_service.conf
   Password: ~/.pgpass
   Connect with: psql "service=[instance_name]"
```

### Get User's IP

```bash
curl -s ifconfig.me
```

Always append `/32` for CIDR notation for a single IP when using in network rules.

Optional: If the user already has a network policy name and wants to verify access first:
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/network_policy_check.py \
  --policy-name <POLICY_NAME> \
  --ip <IP>
```
`<SKILL_DIR>` must be an absolute path.

### Setup Network Policy

**⚠️ MANDATORY STOPPING POINT**

⚠️ **Postgres requires `POSTGRES_INGRESS` mode** - standard policies won't work!

#### Step 1: Get Approval
⚠️ **If the user is planning to use an IP/subnet that will be open to the internet or a very large range, eg 0.0.0.0/0, ::/0 stop and warn them about the risks**

Present to user:
```
⚠️ Please verify with your Security team before making any networking changes. 
Creating any network policies can have security implications.

I will create a network policy to allow your IP ([IP]/32) to connect.

This involves:
1. Creating a network rule (POSTGRES_INGRESS mode)
2. Creating a network policy
3. Attaching it to the instance

Proceed? (yes/no)
```

#### Step 2: Execute ALL Three SQL Statements

After approval, **execute all three SQL statements in sequence:**

```sql
-- Execute Step 1: Create network rule
CREATE NETWORK RULE POSTGRES_INGRESS_RULE_<INSTANCE>
  TYPE = IPV4
  VALUE_LIST = ('<IP>/32')
  MODE = POSTGRES_INGRESS;
```

```sql
-- Execute Step 2: Create network policy
CREATE NETWORK POLICY POSTGRES_INGRESS_POLICY_<INSTANCE>
  ALLOWED_NETWORK_RULE_LIST = ('POSTGRES_INGRESS_RULE_<INSTANCE>');
```

```sql
-- Execute Step 3: Attach to instance
ALTER POSTGRES INSTANCE <INSTANCE>
  SET NETWORK_POLICY = 'POSTGRES_INGRESS_POLICY_<INSTANCE>';
```

Do NOT stop after step 1 - complete all three steps.

## Output

- IP address shown
- Network policy SQL executed/confirmed

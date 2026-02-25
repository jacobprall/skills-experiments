---
name: openflow-ops-snowflake-auth
description: Configure Snowflake authentication for flows writing to Snowflake. Use for KEY_PAIR setup, session token configuration, and auth troubleshooting.
---

# Snowflake Authentication

Configure Snowflake authentication for flows that write to Snowflake. Applies to connectors and custom flows.

**Note:** These operations modify service state. Apply the Check-Act-Check pattern from `references/core-guidelines.md`.

## Scope

- Snowflake destination authentication (connectors and custom flows)
- SPCS vs BYOC configuration differences
- Key-pair setup and troubleshooting

## Overview

The SnowflakeConnectionService is the core component for Snowflake connectivity. Properties are set via Parameter Context, which is required for assets like private keys.

Authentication strategy is determined by deployment type (from cache):

| Deployment | Strategy |
|------------|----------|
| `spcs` | `SNOWFLAKE_SESSION_TOKEN` |
| `byoc` | `KEY_PAIR` (typical) |

For deployment type background, see `references/core-guidelines.md`.

---

## Property Reference

### Always Required

| Property | Notes |
|----------|-------|
| Destination Database | Target database for operations |
| Snowflake Authentication Strategy | `SNOWFLAKE_SESSION_TOKEN` (SPCS) or `KEY_PAIR` (BYOC) |
| Snowflake Role | Role for operations |

### Required for BYOC Only

| Property | Notes |
|----------|-------|
| Snowflake Account Identifier | Format: `org-name.account-name` |
| Snowflake Username | Service user name |
| Private Key | Via asset upload |

### Commonly Set

| Property | Notes |
|----------|-------|
| Schema | Check connector/flow requirements - may have defaults |
| Snowflake Warehouse | Check connector/flow requirements - may have defaults |

The calling workflow (connector or custom flow) specifies which properties are needed. Check connector documentation or existing parameter context for pre-set values.

---

## SPCS Configuration

Snowflake manages authentication automatically via session tokens.

Set the required properties. Leave these empty (automatic from session):
- Snowflake Account Identifier
- Snowflake Username
- Private Key

### Runtime Role

The `Snowflake Role` must be a role your runtime role can assume. Check the cache for the runtime role:

```bash
cat ~/.snowflake/cortex/memory/openflow_infrastructure_*.json | jq '.deployments[].runtimes[].runtime_role'
```

### PrivateKeyService Bulletins

On SPCS, you may see bulletins about `PrivateKeyService` errors. Ignore these - this service is only used on BYOC.

---

## BYOC Configuration

BYOC requires explicit authentication. Key-pair is the common approach.

### Step 1: Confirm Service User

Ask the user: "Do you have a Snowflake service user for Openflow? If so, what is the username?"

If user has a service user, record the username and proceed to Step 2.

If user needs a service user, see [Service User Setup](#service-user-setup) below, then return here.

### Step 2: Confirm Key Pair

Ask the user: "Do you have an RSA key pair assigned to this user, or should I help set one up?"

**If user has an existing key pair:**
- Ask for the private key file path
- Proceed to Step 3

**If user needs a new key pair:**

Generate one in `~/.ssh/`:

```bash
# Generate encrypted private key
openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 aes256 -inform PEM -out ~/.ssh/snowflake_rsa_key.p8

# Set restrictive permissions
chmod 600 ~/.ssh/snowflake_rsa_key.p8

# Extract public key
openssl rsa -in ~/.ssh/snowflake_rsa_key.p8 -pubout -out ~/.ssh/snowflake_rsa_key.pub
```

Assign the public key to the Snowflake user:

```sql
ALTER USER <username> SET RSA_PUBLIC_KEY = '<public_key_content>';
```

### Step 3: Upload Private Key

Use `references/ops-parameters-assets.md` to upload the private key to the parameter context.

### Step 4: Set Passphrase

If the private key is encrypted, use `references/ops-parameters-main.md` to set the `Private Key Passphrase` parameter.

### Step 5: Verify Grants

Ask the user: "Can you confirm the service user's role has the necessary grants for the target database and warehouse?"

If user is unsure, verify grants:

```sql
SHOW GRANTS TO ROLE <role>;
```

Check for:
- `USAGE` on the target database
- `USAGE`, `OPERATE` on the target warehouse
- Additional grants as specified by the connector/flow documentation

If grants are missing, see [Grant Setup](#grant-setup) below.

### Step 6: Configure Parameters

Use `references/ops-parameters-main.md` to set the required and commonly-set parameters for the deployment.

---

## Setup Procedures

### Service User Setup

Create a service user and role:

```sql
CREATE IF NOT EXISTS USER <username> TYPE = SERVICE;
CREATE IF NOT EXISTS ROLE <role_name>;
GRANT ROLE <role_name> TO USER <username>;
```

After creation, return to Step 2 to set up key pair authentication.

### Grant Setup

Grant minimum required permissions:

```sql
GRANT USAGE ON DATABASE <db> TO ROLE <role>;
GRANT USAGE, OPERATE ON WAREHOUSE <wh> TO ROLE <role>;
```

Additional grants depend on the connector/flow. Common additions:

```sql
-- For schema operations
GRANT USAGE ON SCHEMA <db>.<schema> TO ROLE <role>;
GRANT CREATE TABLE ON SCHEMA <db>.<schema> TO ROLE <role>;

-- For creating schemas
GRANT CREATE SCHEMA ON DATABASE <db> TO ROLE <role>;

-- For internal stage writes
GRANT READ, WRITE ON STAGE <db>.<schema>.<stage> TO ROLE <role>;
```

**SPCS Runtime Role Naming:** On SPCS, runtime roles have names like `RUNTIMEROLE_<service_name>`. Don't confuse this with OAuth service names (`SF$OAUTH$...`) which appear in integration metadata. Use the actual runtime role name for GRANT statements.

After granting, return to the verification step.

---

## Troubleshooting

### Deployment Mode Mismatch

**Symptom:** Auth errors on SPCS with BYOC-style parameters set.

**Check:** On SPCS, these should be empty:
- Snowflake Account Identifier
- Snowflake Username
- Private Key

**Fix:** Clear the conflicting parameters.

### Partial Flow Failure

**Symptom:** Some Snowflake processors work, others fail.

**Cause:** Different processors use different APIs (JDBC, Streaming, Iceberg REST). A misconfigured auth strategy may allow one pathway while another fails.

**Fix:** Verify auth strategy matches deployment type. Check all required parameters are set or unset as required for the failing pathway.

### Invalid Credentials

**On SPCS:**
- Verify `Snowflake Authentication Strategy` = `SNOWFLAKE_SESSION_TOKEN`
- Check role has required permissions
- Verify no BYOC parameters are set

**On BYOC:**
- Verify public key assigned: `DESC USER <username>`
- Check private key format (PEM, PKCS#8)
- Verify passphrase if key is encrypted

### Insufficient Privileges

```sql
SHOW GRANTS TO ROLE <role>;
SHOW GRANTS TO USER <user>;
```

Compare against required grants for the connector/flow.

---

## Next Step

After configuring authentication, return to the calling workflow to continue.

## See Also

- `references/core-guidelines.md` - Deployment types
- `references/ops-parameters-main.md` - Parameter configuration
- `references/ops-parameters-assets.md` - Asset upload

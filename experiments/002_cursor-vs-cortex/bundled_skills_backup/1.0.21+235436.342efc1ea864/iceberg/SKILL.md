---
name: iceberg
description: "Use for **ALL** Iceberg table requests in Snowflake. This is the **REQUIRED** entry point for catalog integrations, catalog-linked databases, external volumes, auto-refresh issues, and Snowflake Intelligence. DO NOT work with Iceberg manually - invoke this skill first. Triggers: iceberg, iceberg table, apache iceberg, catalog integration, REST catalog, ICEBERG_REST, glue, AWS glue, glue IRC, lake formation, unity catalog, databricks, polaris, opencatalog, open catalog, CLD, catalog-linked database, linked catalog, auto-discover tables, sync tables, LINKED_CATALOG, external volume, storage access, S3, Azure blob, GCS, IAM role, trust policy, Access Denied, 403 error, ALLOW_WRITES, storage permissions, auto-refresh, autorefresh, stale data, refresh stuck, delta direct, snowflake intelligence, text-to-SQL iceberg, query iceberg natural language."
---

# Iceberg

## When to Use

When a user wants to work with Iceberg tables in Snowflake. This includes:
- Setting up catalog integrations (AWS Glue, Unity Catalog, OpenCatalog/Polaris)
- Creating catalog-linked databases for automatic table discovery
- Configuring external volumes for storage access
- Debugging auto-refresh issues
- Surfacing CLD Iceberg data in Snowflake Intelligence

This is the entry point for all Iceberg workflows.

---

## Session Prerequisites

Before routing to any operation, confirm the user's goal to avoid unnecessary work.

**Confirmation checkpoint** (use before starting any workflow):

> "It sounds like you want to [detected intent]. Is that right, or were you looking for something else?"

---

## Routing Principles

1. **Confirm before routing** - State detected intent, ask user for confirmation
2. **Primary wins ties** - If ambiguous between intents, choose the more common operation
3. **Follow dependencies** - Some workflows depend on others (e.g., CLD requires catalog integration first)
4. **Sub-skills handle details** - This skill routes; sub-skills execute

---

## Intent Detection

When user makes a request, detect their intent and route to the appropriate sub-skill:

### Primary Operations

These are the most common operations users perform. Route here confidently.

**CATALOG_INTEGRATION Intent** - User wants to connect Snowflake to an external catalog:

- Trigger phrases: "catalog integration", "connect to glue", "connect to databricks", "connect to unity catalog", "connect to polaris", "connect to opencatalog", "setup iceberg REST", "configure catalog"
- **→ Route to** [Catalog Integration Routing](#catalog-integration-routing)

**CATALOG_LINKED_DATABASE Intent** - User wants to auto-discover tables from a catalog:

- Trigger phrases: "catalog-linked database", "CLD", "auto-discover tables", "sync tables from catalog", "CREATE DATABASE LINKED_CATALOG", "import iceberg tables"
- **→ Load** `catalog-linked-database/SKILL.md`

**EXTERNAL_VOLUME Intent** - User wants to configure or debug storage access:

- Trigger phrases: "external volume", "storage access", "S3 access", "Azure storage", "GCS storage", "Access Denied", "403 error", "cannot write", "ALLOW_WRITES", "trust policy", "IAM role"
- **→ Load** `external-volume/SKILL.md`

**AUTO_REFRESH Intent** - User has stale data or refresh issues:

- Trigger phrases: "auto-refresh", "stale data", "refresh not working", "refresh stuck", "STALLED", "STOPPED", "delta direct", "not syncing", "data not updating"
- **→ Load** `auto-refresh/SKILL.md`

### Secondary Operations

Route here when user language indicates more advanced or combined workflows.

**SNOWFLAKE_INTELLIGENCE Intent** - User wants to query CLD Iceberg tables with natural language:

- Trigger phrases: "snowflake intelligence", "natural language", "text-to-SQL", "query CLD with AI", "create agent for CLD", "semantic view for CLD", "query iceberg naturally"
- **→ Load** `cld-snowflake-intelligence/SKILL.md`

---

## Catalog Integration Routing

When user wants to connect to an external catalog, identify which catalog type:

**Ask the user**:
```
Which external catalog are you connecting to?

A: AWS Glue Data Catalog (Glue IRC)
   → Iceberg tables managed in AWS Glue

B: Databricks Unity Catalog
   → Iceberg tables managed in Databricks

C: OpenCatalog / Polaris
   → Snowflake's open Iceberg catalog

D: I'm not sure / I need help choosing
```

**Route based on response**:
- **A (Glue)** → **Load** `catalog-integration/glueirc-catalog-integration-setup/SKILL.md`
- **B (Unity Catalog)** → **Load** `catalog-integration/unitycatalog-catalog-integration-setup/SKILL.md`
- **C (OpenCatalog/Polaris)** → **Load** `catalog-integration/opencatalog-catalog-integration-setup/SKILL.md`
- **D (Not sure)** → Help user identify their catalog (see [Catalog Selection Guide](#catalog-selection-guide))

---

## Catalog Selection Guide

Help users identify their catalog type:

| If user mentions... | Catalog Type | Route to |
|---------------------|--------------|----------|
| AWS, Glue, Lake Formation, S3 with Iceberg | AWS Glue IRC | `glueirc-catalog-integration-setup` |
| Databricks, Unity, Delta Lake (converted to Iceberg) | Unity Catalog | `unitycatalog-catalog-integration-setup` |
| Polaris, OpenCatalog, Snowflake Open Catalog | OpenCatalog | `opencatalog-catalog-integration-setup` |

---

## Workflow Decision Tree

```
Start Session
    ↓
Detect User Intent
    ↓
    ├─→ CATALOG_INTEGRATION → Identify catalog type
    │   ├─→ AWS Glue → Load `glueirc-catalog-integration-setup`
    │   ├─→ Unity Catalog → Load `unitycatalog-catalog-integration-setup`
    │   ├─→ OpenCatalog/Polaris → Load `opencatalog-catalog-integration-setup`
    │   └─→ Not sure → Catalog Selection Guide
    │
    ├─→ CATALOG_LINKED_DATABASE → Load `catalog-linked-database/SKILL.md`
    │
    ├─→ EXTERNAL_VOLUME → Load `external-volume/SKILL.md`
    │
    ├─→ AUTO_REFRESH → Load `auto-refresh/SKILL.md`
    │
    └─→ SNOWFLAKE_INTELLIGENCE → Load `cld-snowflake-intelligence/SKILL.md`
```

---

## Typical User Journeys

### Journey 1: New Iceberg Setup (End-to-End)
```
CATALOG_INTEGRATION → EXTERNAL_VOLUME (if needed) → CATALOG_LINKED_DATABASE → SNOWFLAKE_INTELLIGENCE
```
Example: "I want to set up Iceberg from scratch and query with natural language"

### Journey 2: Connect External Catalog
```
CATALOG_INTEGRATION → CATALOG_LINKED_DATABASE
```
Example: "I want to query my Glue Iceberg tables from Snowflake"

### Journey 3: Storage Access Issues
```
EXTERNAL_VOLUME (diagnose) → fix IAM/trust policy → EXTERNAL_VOLUME (verify)
```
Example: "I'm getting Access Denied when creating an Iceberg table"

### Journey 4: Data Freshness Problems
```
AUTO_REFRESH (diagnose) → apply fix → AUTO_REFRESH (verify)
```
Example: "My Iceberg table data is stale"

### Journey 5: Add Natural Language to Existing CLD
```
CATALOG_LINKED_DATABASE (verify) → SNOWFLAKE_INTELLIGENCE
```
Example: "I have a CLD and want to query it with natural language"

### Journey 6: Catalog Integration Troubleshooting
```
CATALOG_INTEGRATION → Troubleshoot Workflow
```
Example: "My Unity Catalog integration isn't working"

### Journey 7: CLD Not Syncing Tables
```
CATALOG_LINKED_DATABASE (troubleshoot) → AUTO_REFRESH (if refresh issues)
```
Example: "Tables aren't appearing in my catalog-linked database"

---

## Compound Requests

If the user describes multiple operations:

1. Create a task list capturing all requested operations
2. Ask the user to confirm the order:
   > "I've identified these tasks: [list]. What order would you like me to tackle them?"
3. Execute in confirmed order, completing each before moving to the next
4. Note: Natural dependencies exist:
   - Catalog Integration → before → CLD
   - External Volume → before → CLD (if not using vended credentials)
   - CLD → before → Snowflake Intelligence

---

## Sub-Skill Reference Index

### Catalog Integrations

| Sub-Skill | Purpose |
|-----------|---------|
| `catalog-integration/glueirc-catalog-integration-setup/SKILL.md` | AWS Glue Data Catalog (Glue IRC) integration |
| `catalog-integration/unitycatalog-catalog-integration-setup/SKILL.md` | Databricks Unity Catalog integration |
| `catalog-integration/opencatalog-catalog-integration-setup/SKILL.md` | OpenCatalog/Polaris integration |
| `catalog-integration/shared/next-steps/SKILL.md` | Post-integration options (CLD or individual tables) |
| `catalog-integration/shared/verify/SKILL.md` | Shared verification workflow |

### Catalog-Linked Databases

| Sub-Skill | Purpose |
|-----------|---------|
| `catalog-linked-database/SKILL.md` | CLD creation, verification, troubleshooting router |
| `catalog-linked-database/setup/SKILL.md` | CLD configuration collection |
| `catalog-linked-database/create/SKILL.md` | CLD creation workflow |
| `catalog-linked-database/verify/SKILL.md` | CLD verification workflow |
| `catalog-linked-database/references/troubleshooting.md` | CLD error patterns and solutions |

### External Volumes

| Sub-Skill | Purpose |
|-----------|---------|
| `external-volume/SKILL.md` | External volume debugging for AWS S3, Azure, GCS |
| `external-volume/examples/examples.md` | Example configurations |
| `external-volume/examples/known-issues.md` | Known issues and workarounds |

### Auto-Refresh

| Sub-Skill | Purpose |
|-----------|---------|
| `auto-refresh/SKILL.md` | Auto-refresh debugging for Iceberg and Delta Direct |
| `auto-refresh/delta-direct.md` | Delta Direct specific debugging |
| `auto-refresh/monitoring.md` | Auto-refresh monitoring and alerting setup |

### Snowflake Intelligence (CLD)

| Sub-Skill | Purpose |
|-----------|---------|
| `cld-snowflake-intelligence/SKILL.md` | Query CLD Iceberg tables via Snowflake Intelligence |
| `cld-snowflake-intelligence/references/semantic-view-sql.md` | Semantic view syntax for CLD tables |

---

## Stopping Points

- **Intent Detection**: Confirm detected intent before routing
- **Catalog Type Selection**: Wait for user to identify their catalog
- **Sub-skill handoff**: Each sub-skill has its own stopping points

**Resume rule**: Upon user approval ("yes", "looks good", "proceed"), route to the appropriate sub-skill without re-asking.

---

## Scope

**In scope**:
- Routing to appropriate Iceberg sub-skills
- Initial diagnosis to identify the right workflow

**Out of scope** (handled by sub-skills):
- Detailed catalog integration setup → specific catalog integration skills
- CLD configuration details → `catalog-linked-database/SKILL.md`
- External volume IAM/permission details → `external-volume/SKILL.md`
- Auto-refresh debugging details → `auto-refresh/SKILL.md`

---

## Output

- User routed to the correct Iceberg sub-skill based on their intent
- Sub-skill completes the requested operation (setup, verification, or troubleshooting)

---

## Documentation

- [Snowflake Iceberg Tables](https://docs.snowflake.com/user-guide/tables-iceberg)
- [Configure Catalog Integration](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration)
- [Catalog-Linked Databases](https://docs.snowflake.com/en/user-guide/tables-iceberg-catalog-linked-database)
- [External Volumes](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-external-volume)
- [Auto-Refresh Iceberg Tables](https://docs.snowflake.com/en/user-guide/tables-iceberg-auto-refresh)

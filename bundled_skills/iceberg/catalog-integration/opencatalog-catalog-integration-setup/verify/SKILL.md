---
name: opencatalog-verify-integration
description: "Verify OpenCatalog (Polaris) catalog integration is configured correctly. Triggers: check opencatalog integration, verify polaris integration, test opencatalog connection, is my polaris integration working, validate opencatalog catalog integration, confirm polaris catalog setup."
parent_skill: opencatalog-catalog-integration-setup
---

# OpenCatalog (Polaris) Verification

## ⚠️ REQUIRED: Load Shared Verification Workflow

**STOP.** Before proceeding with any verification steps, you **MUST** load and execute the shared verification workflow:

**Path**: `../../shared/verify/SKILL.md`

DO NOT attempt to verify the integration without loading the shared skill first.

## Workflow

Follow these steps in order:

1. **FIRST**: Load `shared/verify/SKILL.md` (path: `../../shared/verify/SKILL.md`) and execute ALL steps in that workflow
2. **DURING**: Apply OpenCatalog-specific context below when interpreting results or errors
3. **IF FAILURES**: Load `references/troubleshooting.md` for OpenCatalog-specific diagnosis

## OpenCatalog-Specific Context

Use this information while executing the shared verification workflow:

**Expected configuration values**:
- `catalog_source`: `POLARIS` or `ICEBERG_REST`
- `catalog_uri`: `https://<orgname>-<account>.snowflakecomputing.com/polaris/api/catalog`
- `catalog_api_type`: `PUBLIC` or `PRIVATE`

**Common OpenCatalog-specific issues**:
| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| `SYSTEM$VERIFY_CATALOG_INTEGRATION` fails with OAuth error | Invalid credentials | Verify Client ID and Client Secret are correct |
| OAuth error with correct credentials | Service connection disabled | Enable the service connection in OpenCatalog UI |
| Connection succeeds but no namespaces found | Missing catalog role | Assign catalog role to service principal in OpenCatalog |
| Namespaces visible but no tables | Missing table privileges | Grant `TABLE_READ_DATA` on tables to the catalog role |

## Output

After completing the shared verification workflow, report results using the format defined in `shared/verify/SKILL.md`.

## Next Steps (On Success)

**If all verification checks passed**:

**Load** `shared/next-steps/SKILL.md` (path: `../../shared/next-steps/SKILL.md`)

Guide user through options for accessing catalog tables. DO NOT skip this step after successful verification.

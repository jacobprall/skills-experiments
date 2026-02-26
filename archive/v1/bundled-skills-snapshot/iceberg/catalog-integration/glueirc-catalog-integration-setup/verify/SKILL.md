---
name: glueirc-verify
description: "Verify AWS Glue IRC catalog integration"
parent_skill: glueirc-catalog-integration-setup
---

# AWS Glue IRC Verification

## ⚠️ REQUIRED: Load Shared Verification Workflow

**STOP.** Before proceeding with any verification steps, you **MUST** load and execute the shared verification workflow:

**Path**: `../../shared/verify/SKILL.md`

DO NOT attempt to verify the integration without loading the shared skill first.

## Workflow

Follow these steps in order:

1. **FIRST**: Load `shared/verify/SKILL.md` (path: `../../shared/verify/SKILL.md`) and execute ALL steps in that workflow
2. **DURING**: Apply Glue-specific context below when interpreting results or errors
3. **IF FAILURES**: Load `references/troubleshooting.md` for Glue-specific diagnosis

## Glue-Specific Context

Use this information while executing the shared verification workflow:

**Namespace format**: Glue database names (single-level, case-sensitive)

**Expected configuration values**:
- `catalog_source`: `ICEBERG_REST`
- `catalog_api_type`: `AWS_GLUE`

**Common Glue-specific issues**:
| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| `SYSTEM$VERIFY_CATALOG_INTEGRATION` fails with access denied | Trust relationship not configured | Check IAM role trust policy has Snowflake's IAM user ARN and external ID |
| Connection succeeds but no namespaces found | Missing Glue permissions | Verify IAM policy has `glue:GetDatabase`, `glue:GetDatabases` |
| Namespaces visible but no tables | Missing table permissions | Verify IAM policy has `glue:GetTable`, `glue:GetTables` |
| Vended credentials error | Lake Formation blocking | Check Lake Formation grants to IAM role, ensure `lakeformation:GetDataAccess` permission |

## Output

After completing the shared verification workflow, report results using the format defined in `shared/verify/SKILL.md`.

## Next Steps (On Success)

**If all verification checks passed**:

**Load** `shared/next-steps/SKILL.md` (path: `../../shared/next-steps/SKILL.md`)

Guide user through options for accessing catalog tables. DO NOT skip this step after successful verification.

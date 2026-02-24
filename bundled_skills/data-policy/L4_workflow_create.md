# Guided Workflow: Create New Policies

Use this file when the user wants to create new policies, extend existing ones, or says "protect the data."

---

## Step 1: Understand the Request

Before creating policies, understand what the customer needs.

**Scope options (ask the user):**

| Option | When to Use | Next Step |
|--------|-------------|-----------|
| **Auto-discover** | User wants CORTEX to find sensitive data automatically | Use auto-classification to scan and identify sensitive columns |
| **Specific tables** | User already knows which tables/columns to protect | Ask for the specific database, schema, table, and column names |
| **All tables** | User wants blanket protection across a database | Apply policies broadly using tag-based masking |

> 💡 **Default to auto-discover** if the user doesn't specify tables. This provides the best experience by leveraging Snowflake's data classification capabilities.

**If user selects Auto-discover:**
1. Check if auto-classification is enabled. If not, refer to `sensitive-data-classification` skill to enable it first.
2. Query the classification tags to find sensitive columns:
   ```sql
   -- Find all classified columns in a database
   SELECT * FROM TABLE(<db>.INFORMATION_SCHEMA.TAG_REFERENCES_ALL_COLUMNS(
     '<db>.<schema>.<table>', 'TABLE'
   )) WHERE TAG_DATABASE = 'SNOWFLAKE' AND TAG_SCHEMA = 'CORE';
   ```
3. Present the discovered sensitive columns to the user for confirmation.
4. Ask if there are any additional fields that should be classified.
5. Proceed to policy creation with the confirmed list.

**Additional discovery questions:**
- What industry and what compliance apply to your use case?
- Refer to `compliance_reference.md` to identify sensitive fields based on regulations.
- List all the columns that have sensitive data.
- Use the reference files to create appropriate policies. 

**Industry → Regulation mapping:**

| Industry | Likely Regulations |
|----------|-------------------|
| Healthcare | **HIPAA** — PHI protection, minimum necessary rule |
| Financial Services | **PCI-DSS** (card data), **SOX** (public companies) |
| Retail / E-commerce | **PCI-DSS** (payments), **CCPA/CPRA** (CA consumers) |
| Technology / SaaS | **GDPR** (EU users), **CCPA** (CA users) |
| Education | **FERPA** — student records protection |
| Any with EU customers | **GDPR** — personal data, data subject rights |
| Any with CA customers | **CCPA/CPRA** — consumer privacy rights |

> 📚 **For compliance guidance:** See `compliance_reference.md` for regulation-specific requirements, sensitive fields, and sample policies.

> 💡 **If customer mentions existing policies:** Always examine them before creating new ones.

---

## Step 2: Choose Policy Type

| Goal | Policy Type | When to Use |
|------|-------------|-------------|
| Hide column values | **Masking Policy** | SSN, email, card numbers |
| Filter rows by user attribute | **Row Access Policy** | Regional data, department isolation |
| Scale protection across many tables | **Tag-Based Masking** | 10+ tables with similar data |
| Restrict to aggregate-only queries | **Aggregation Policy** | Analytics users who shouldn't see individual records |
| Hide columns entirely | **Projection Policy** | Columns that shouldn't appear in results at all |

---

## Step 3: Check for Existing Policies

Before creating a new policy, check what already exists.

### 3.1 Find Policies on the Table

```sql
-- NOTE: Must qualify with database name, or USE DATABASE first
SELECT 
  REF_COLUMN_NAME AS COLUMN_NAME,
  POLICY_NAME,
  POLICY_KIND
FROM TABLE(<db>.INFORMATION_SCHEMA.POLICY_REFERENCES(
  REF_ENTITY_NAME => '<db>.<schema>.<table>',
  REF_ENTITY_DOMAIN => 'TABLE'
))
ORDER BY REF_COLUMN_NAME;
```

### 3.2 Find Existing Policies by Data Type

```sql
-- List masking policies in the database
SHOW MASKING POLICIES IN DATABASE <db>;

-- Filter results by return type if needed (from SHOW output)
-- Then get the definition of matching policies:
SELECT GET_DDL('POLICY', '<db>.<schema>.<policy_name>');
```

### 3.3 Examine the Existing Policy

If extending an existing policy to a new data type, examine its implementation:

```sql
SELECT GET_DDL('POLICY', '<db>.<schema>.<policy_name>');
```

**Check: Is the policy "split"?**

```
✅ SPLIT (good):                    ❌ NOT SPLIT (anti-pattern):
CASE                                CASE  
  WHEN schema.unmask_condition()      WHEN CURRENT_ROLE() IN ('ROLE_A', 'ROLE_B')
  THEN val                            THEN val
  ELSE '***'                          ELSE '***'
END                                 END
     ↑                                   ↑
     Calls a shared function             Unmask logic embedded directly
```

| What You See in Policy Body | Decision |
|-----------------------------|----------|
| Calls a shared function like `unmask_condition()` | ✅ **Already split** — create new policy using same function |
| Hardcoded roles in CASE statement | ⚠️ **Not split** — apply split pattern first |
| Direct subquery or complex logic | ⚠️ **Not split** — extract to function first |
| No suitable existing policy | ➕ **Create new** — use split pattern from the start |

> 💡 **Split pattern principle:** Unmask logic should live in ONE place (a memoizable function), not duplicated across policies.

---

## Step 4: Apply the Split Pattern (If Needed)

When extending a policy that has embedded unmask logic, split it out first.

> ⚠️ **Order matters:** You MUST create the function FIRST, before creating or modifying any policies that reference it.

### 4.1 Create the Shared Unmask Function FIRST

```sql
CREATE OR REPLACE FUNCTION <schema>.unmask_condition()
RETURNS BOOLEAN
MEMOIZABLE
AS
$$
  CURRENT_ROLE() IN ('AUTHORIZED_ROLE_1', 'AUTHORIZED_ROLE_2')
$$;
```

### 4.2 Refactor the Existing Policy

```sql
-- Unset from columns first
ALTER TABLE <table> MODIFY COLUMN <col> UNSET MASKING POLICY;

-- Recreate using the function
CREATE OR REPLACE MASKING POLICY <schema>.MASK_STRING_PII
AS (val STRING)
RETURNS STRING ->
  CASE
    WHEN <schema>.unmask_condition() THEN val
    ELSE '***MASKED***'
  END
COMMENT = 'Masks STRING PII. Uses shared unmask_condition() for auth.';

-- Reapply
ALTER TABLE <table> MODIFY COLUMN <col> SET MASKING POLICY <schema>.MASK_STRING_PII;
```

### 4.3 Create New Policy Using Same Function

```sql
-- TIMESTAMP example (function must exist before running this)
CREATE OR REPLACE MASKING POLICY <schema>.MASK_TIMESTAMP_PII
AS (val TIMESTAMP)
RETURNS TIMESTAMP ->
  CASE
    WHEN <schema>.unmask_condition() THEN val
    ELSE '1900-01-01 00:00:00'::TIMESTAMP
  END
COMMENT = 'Masks TIMESTAMP PII. Uses same unmask_condition() as other policies.';
```

> 📚 See `L2_proven_patterns.md` → Pattern 2 for complete templates for each data type.

---

## Step 5: Create the Policy

If creating from scratch (no existing policy to extend), use the split pattern from the start.

### Masking Policy Template

```sql
-- Step 1: Create shared function
CREATE OR REPLACE FUNCTION <schema>.unmask_condition()
RETURNS BOOLEAN
MEMOIZABLE
AS
$$
  CURRENT_ROLE() IN ('ROLE_A', 'ROLE_B')
$$;

-- Step 2: Create policy using the function
CREATE OR REPLACE MASKING POLICY <schema>.MASK_<TYPE>_PII
AS (val <DATA_TYPE>)
RETURNS <DATA_TYPE> ->
  CASE
    WHEN <schema>.unmask_condition() THEN val
    ELSE <masked_value>
  END;

-- Step 3: Apply to column
ALTER TABLE <table> MODIFY COLUMN <col> SET MASKING POLICY <schema>.MASK_<TYPE>_PII;
```

### Row Access Policy Template

```sql
CREATE OR REPLACE ROW ACCESS POLICY <schema>.FILTER_BY_REGION
AS (region_col STRING)
RETURNS BOOLEAN ->
  region_col = CURRENT_USER()  -- or use mapping table
;

ALTER TABLE <table> ADD ROW ACCESS POLICY <schema>.FILTER_BY_REGION ON (region);
```

### Projection Policy Template

```sql
CREATE OR REPLACE PROJECTION POLICY <schema>.HIDE_SENSITIVE_COLUMN
AS ()
RETURNS PROJECTION_CONSTRAINT ->
  CASE
    WHEN IS_ROLE_IN_SESSION('DATA_OWNER') THEN PROJECTION_CONSTRAINT(ALLOW => TRUE)
    ELSE PROJECTION_CONSTRAINT(ALLOW => FALSE)
  END;

ALTER TABLE <table> MODIFY COLUMN <col> SET PROJECTION POLICY <schema>.HIDE_SENSITIVE_COLUMN;
```

---

## Step 6: Verify

Test that the policy works as expected:

```sql
-- 1. Check policy is applied (must qualify with database name)
SELECT * FROM TABLE(<db>.INFORMATION_SCHEMA.POLICY_REFERENCES(
  REF_ENTITY_NAME => '<db>.<schema>.<table>',
  REF_ENTITY_DOMAIN => 'TABLE'
));

-- 2. Test with authorized role
USE ROLE <authorized_role>;
SELECT <protected_column> FROM <table> LIMIT 5;
-- Expected: See real data

-- 3. Test with unauthorized role
USE ROLE <unauthorized_role>;
SELECT <protected_column> FROM <table> LIMIT 5;
-- Expected: See masked data
```

---

## Step 7: Recommend Scale Path

After the immediate problem is solved, mention future options:

- **Tag-based masking:** For protecting many tables with similar data
- **Centralized governance schema:** Keep all policies in one place
- **Shared functions:** Already using split pattern = easy to extend

> 📚 See `L2_proven_patterns.md` → Pattern 1 (ABAC) for tag-based approach.

---

## Decision Summary

| Scenario | Action |
|----------|--------|
| New policy, no existing | Create with split pattern from start |
| Extend existing policy (already split) | Create new policy using same function |
| Extend existing policy (not split) | Apply split pattern first, then create new |
| Multiple tables need same protection | Consider tag-based masking |

---

## Stopping Points

- ✋ Step 1: Request understood
- ✋ Step 3: Existing policies evaluated — **split or not?**
- ✋ Step 6: Verification complete

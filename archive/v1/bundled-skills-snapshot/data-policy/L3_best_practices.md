# Best Practices

Use this file when the user asks about policy design guidelines, anti-patterns, or practical constraints.

## Quick Reference

| # | Best Practice | Priority | When to Apply |
|---|--------------|----------|---------------|
| 1 | Check similar tables first | **CRITICAL** | Before creating any new policy |
| 2 | Use generic, reusable policies | HIGH | Always when creating new policies |
| 3 | Centralize in a governance database | HIGH | Account-wide policy management |
| 4 | Use memoizable functions for lookups | HIGH | Policy uses mapping/lookup tables |
| 5 | Use IS_ROLE_IN_SESSION() for role checks | MEDIUM | Role-based access control |

---

## 1. Check Similar Tables First

**Problem:** Creating a new policy without checking existing ones leads to inconsistent protection and policy sprawl.

**Solution:** Before protecting any column, check what policies already protect similar columns or tables with the same tags.

**Why this matters:**
- Ensures **consistency** — similar data gets similar protection
- Promotes **reuse** — one policy protects many columns
- Avoids **sprawl** — prevents dozens of near-identical policies
- Reveals **gaps** — find unprotected tables that should have policies

**Discovery queries:**

```sql
-- List existing masking policies in the database
SHOW MASKING POLICIES IN DATABASE <db>;

-- Check what policies are on a similar table
SELECT 
  POLICY_NAME,
  POLICY_KIND,
  REF_COLUMN_NAME AS COLUMN_NAME
FROM TABLE(<db>.INFORMATION_SCHEMA.POLICY_REFERENCES(
  REF_ENTITY_NAME => '<db>.<schema>.<similar_table>',
  REF_ENTITY_DOMAIN => 'TABLE'
));

-- Get the policy definition to understand its logic
SELECT GET_DDL('POLICY', '<db>.<schema>.<policy_name>');

-- Find columns with a specific tag (in a schema)
SELECT 
  OBJECT_NAME AS TABLE_NAME,
  COLUMN_NAME,
  TAG_VALUE
FROM TABLE(<db>.INFORMATION_SCHEMA.TAG_REFERENCES(
  '<db>.<schema>', 'SCHEMA'
)) WHERE TAG_NAME = 'PII_TYPE';
```

**Decision flow:**
1. ✅ Found policy on similar table? → **Reuse it**
2. ✅ Found multiple different policies? → **Consolidate to one**
3. ⚠️ Found unprotected similar tables? → **Protect them too**
4. ❌ No similar tables exist? → **Create new generic policy**

---

## 2. Use Generic, Reusable Policies

**Problem:** Creating separate masking policies for every table or column leads to policy sprawl and maintenance burden.

**Solution:** Define generic policies that can be reused across datasets.

**Good:**
```sql
-- One policy for all PII string columns
CREATE MASKING POLICY pii_string_mask AS (val STRING) RETURNS STRING ->
  CASE
    WHEN IS_ROLE_IN_SESSION('PII_VIEWER') THEN val
    ELSE '***MASKED***'
  END;
```

**Anti-pattern:**
```sql
-- DON'T: Create table-specific policies
CREATE MASKING POLICY customers_email_mask ...
CREATE MASKING POLICY orders_email_mask ...
CREATE MASKING POLICY users_email_mask ...
```

---

## 3. Centralize in a Governance Database

**Problem:** Policies, tags, and mapping tables scattered across schemas make governance difficult to manage and audit.

**Solution:** Create a dedicated governance database to centralize all policy-related objects.

**Recommended structure:**
```
GOVERNANCE_DB
├── POLICIES (schema)
│   └── masking policies, row access policies, projection policies
├── TAGS (schema)
│   └── tag definitions
└── ACCESS_CONTROL (schema)
    ├── role_mapping tables
    └── entitlement tables
```

**Setup:**
```sql
CREATE DATABASE GOVERNANCE_DB;
CREATE SCHEMA GOVERNANCE_DB.POLICIES;
CREATE SCHEMA GOVERNANCE_DB.TAGS;
CREATE SCHEMA GOVERNANCE_DB.ACCESS_CONTROL;

-- Restrict access to governance role
GRANT USAGE ON DATABASE GOVERNANCE_DB TO ROLE GOVERNOR;
GRANT ALL ON SCHEMA GOVERNANCE_DB.POLICIES TO ROLE GOVERNOR;
```

---

## 4. Use Memoizable Functions for Lookups

**Problem:** Policies that query mapping tables execute the lookup for every row, causing performance issues.

**Solution:** Use a memoizable function to cache the result within a session.

**Good:**
```sql
CREATE OR REPLACE FUNCTION is_authorized_role()
RETURNS BOOLEAN
MEMOIZABLE
AS
$$
  EXISTS (
    SELECT 1 FROM governance_db.access_control.authorized_roles 
    WHERE role_name = CURRENT_ROLE()
  )
$$;

CREATE MASKING POLICY secure_mask AS (val STRING) RETURNS STRING ->
  CASE
    WHEN is_authorized_role() THEN val
    ELSE '***MASKED***'
  END;
```

**Anti-pattern:**
```sql
-- DON'T: Query mapping table directly in policy body
CREATE MASKING POLICY slow_mask AS (val STRING) RETURNS STRING ->
  CASE
    WHEN CURRENT_ROLE() IN (SELECT role_name FROM mapping_table) THEN val
    ELSE '***MASKED***'
  END;
```

**When NOT to use memoizable functions:**
- Mapping table is a view with complex logic
- Mapping data changes frequently within a session

---

## 5. Use IS_ROLE_IN_SESSION() for Role Checks

**Problem:** `CURRENT_ROLE()` only checks the active role, ignoring role hierarchy.

**Solution:** Use `IS_ROLE_IN_SESSION()` to check if a role is in the current session's role hierarchy.

**Good:**
```sql
-- Hierarchy-aware: works if user has inherited the role
WHEN IS_ROLE_IN_SESSION('ANALYST') THEN val
```

**Anti-pattern:**
```sql
-- DON'T: Only checks exact active role
WHEN CURRENT_ROLE() = 'ANALYST' THEN val
```

---

## Common Anti-Patterns Summary

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Table-specific policies | Sprawl, maintenance burden | Use generic policies + tags |
| Unmask logic in policy body | Duplicated across policies, hard to maintain | **Apply split pattern** — extract to memoizable function |
| Hardcoded role lists | Adding roles requires editing each policy | **Apply split pattern** — extract to memoizable function |
| Direct mapping table queries in policy | Per-row lookup overhead | **Apply split pattern** — wrap in memoizable function |
| Using CURRENT_ROLE() only | Ignores role hierarchy | Use IS_ROLE_IN_SESSION() |
| Policies scattered across schemas | Hard to audit | Centralize in governance database |
| **Missing ELSE NULL clause** | Data leaks if no condition matches | **Always include ELSE NULL** |
| **No policy documentation** | Hard to understand ownership/purpose | **Add COMMENT with owner and purpose** |

> 💡 **Split pattern:** Extract unmask logic from policy bodies into a shared memoizable function. All policies call this function instead of having their own logic. See `L2_proven_patterns.md` → Pattern 2.

---

## 6. Always Include ELSE NULL (Secure Default)

**Problem:** If no CASE condition matches and there's no ELSE clause, the policy returns NULL implicitly—but this behavior is unclear and error-prone. Worse, some SQL engines or future changes might return the original value.

**Solution:** Always include an explicit `ELSE NULL` to ensure secure default behavior.

**Good:**
```sql
CREATE MASKING POLICY mask_ssn AS (val STRING) RETURNS STRING ->
  CASE
    WHEN IS_ROLE_IN_SESSION('HR_ADMIN') THEN val
    WHEN IS_ROLE_IN_SESSION('FINANCE_ADMIN') THEN val
    ELSE NULL  -- Secure default: unauthorized roles see nothing
  END
COMMENT = 'Masks SSN for non-privileged roles. Owner: Security Team';
```

**Anti-pattern:**
```sql
-- DON'T: Missing ELSE clause
CREATE MASKING POLICY mask_ssn AS (val STRING) RETURNS STRING ->
  CASE
    WHEN CURRENT_ROLE() = 'HR_ADMIN' THEN val
    WHEN CURRENT_ROLE() = 'FINANCE_ADMIN' THEN val
    -- No ELSE clause = unclear behavior
  END;
```

> 📊 **Finding:** ~80% of production policies include ELSE NULL. The remaining 20% are potential security gaps.

---

## 7. Document Every Policy with COMMENT

**Problem:** Policies without documentation become orphaned—no one knows who owns them, what they protect, or whether they can be modified.

**Solution:** Add a COMMENT to every policy specifying owner, purpose, and protected data.

**Good:**
```sql
CREATE MASKING POLICY mask_email AS (val STRING) RETURNS STRING ->
  CASE
    WHEN IS_ROLE_IN_SESSION('MARKETING_ADMIN') THEN val
    ELSE '***@***'
  END
COMMENT = 'Masks email addresses. Owner: Data Governance Team. Protected: PII-EMAIL';
```

**Recommended COMMENT format:**
```
'<Purpose>. Owner: <Team/Person>. Protected: <Data Classification>'
```

**Anti-pattern:**
```sql
-- DON'T: No comment
CREATE MASKING POLICY mask_email AS (val STRING) RETURNS STRING -> ...;
```

---

## Before/After Transformations

### Transform 1: Scattered → Centralized

**Before (scattered):**
```
SALES_DB.DATA.email_mask
SALES_DB.POLICIES.phone_mask
HR_DB.EMPLOYEE_DATA.ssn_mask
FINANCE_DB.TRANSACTIONS.card_mask
```

**After (centralized):**
```
GOVERNANCE_DB.POLICIES.pii_string_mask    -- Reusable for email, phone
GOVERNANCE_DB.POLICIES.ssn_mask           -- Specific for SSN format
GOVERNANCE_DB.POLICIES.card_mask          -- Specific for card numbers
```

### Transform 2: Hardcoded → Dynamic

**Before (hardcoded roles):**
```sql
CREATE MASKING POLICY old_mask AS (val STRING) RETURNS STRING ->
  CASE
    WHEN CURRENT_ROLE() IN ('ADMIN', 'MANAGER', 'ANALYST', 'SUPPORT',
                            'VIEWER_US', 'VIEWER_EU', 'VIEWER_APAC') THEN val
    ELSE '***MASKED***'
  END;
```

**After (dynamic with mapping table):**
```sql
-- Step 1: Create mapping table
CREATE TABLE GOVERNANCE_DB.ACCESS_CONTROL.authorized_roles (
    role_name STRING,
    can_view_pii BOOLEAN
);

-- Step 2: Create memoizable function
CREATE FUNCTION can_view_pii()
RETURNS BOOLEAN
MEMOIZABLE
AS $$ 
  EXISTS (SELECT 1 FROM GOVERNANCE_DB.ACCESS_CONTROL.authorized_roles 
          WHERE role_name = CURRENT_ROLE() AND can_view_pii = TRUE)
$$;

-- Step 3: Create simple policy
CREATE MASKING POLICY new_mask AS (val STRING) RETURNS STRING ->
  CASE WHEN can_view_pii() THEN val ELSE '***MASKED***' END
  COMMENT = 'Generic PII mask. Access controlled via authorized_roles table.';
```

### Transform 3: Slow → Fast

**Before (slow - subquery per row):**
```sql
CREATE MASKING POLICY slow_mask AS (val STRING) RETURNS STRING ->
  CASE
    WHEN EXISTS (
      SELECT 1 FROM auth_table 
      WHERE role = CURRENT_ROLE() AND access_level = 'FULL'
    ) THEN val
    ELSE '***MASKED***'
  END;
```

**After (fast - memoized):**
```sql
-- Memoizable function caches result for entire session
CREATE FUNCTION has_full_access()
RETURNS BOOLEAN
MEMOIZABLE
AS $$
  EXISTS (SELECT 1 FROM auth_table 
          WHERE role = CURRENT_ROLE() AND access_level = 'FULL')
$$;

CREATE MASKING POLICY fast_mask AS (val STRING) RETURNS STRING ->
  CASE WHEN has_full_access() THEN val ELSE '***MASKED***' END;
```

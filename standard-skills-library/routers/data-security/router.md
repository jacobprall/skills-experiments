---
type: router
name: data-security
domain: data-security
parameters:
  - name: user_goal
    description: "What the user is trying to accomplish with data security"
    options:
      - id: end-to-end-protection
        description: "Discover, protect, and monitor sensitive data — full workflow"
      - id: discover-pii
        description: "Find and classify sensitive data (PII, financial, health) in tables"
      - id: mask-columns
        description: "Hide or redact column values so unauthorized users can't see them"
      - id: restrict-rows
        description: "Limit which rows certain users or roles can access"
      - id: restrict-columns
        description: "Block specific columns from being queried by certain roles"
      - id: audit-access
        description: "Review who accessed what data and which policies are in place"
routes_to:
  - primitives/data-classification
  - primitives/masking-policies
  - primitives/row-access-policies
  - primitives/projection-policies
  - primitives/account-usage-views
  - playbooks/secure-sensitive-data
---

# Data Security

Single entry point for all data protection, classification, and access auditing in Snowflake. Replaces the overlapping `data-governance`, `data-policy`, and `sensitive-data-classification` skills.

## Decision Criteria

Determine the user's intent before routing. Ask if unclear.

| Input | How to Determine | Example User Statements |
|-------|-----------------|------------------------|
| **Goal** | What outcome does the user want? | "Find PII", "Mask SSNs", "Audit who accessed what" |
| **Scope** | Table-level, schema-level, or account-level? | "This table", "All tables in prod", "Entire account" |
| **Existing state** | Are policies already in place, or starting fresh? | "Review existing policies", "Set up from scratch" |

## Routing Logic

```
Start
  ├─ User wants END-TO-END data protection (discover + protect + audit)?
  │   └─ YES → playbooks/secure-sensitive-data
  │
  ├─ User wants to FIND or DETECT sensitive data?
  │   └─ YES → primitives/data-classification
  │
  ├─ User wants to HIDE or MASK column values?
  │   └─ YES → primitives/masking-policies
  │
  ├─ User wants to RESTRICT which ROWS users can see?
  │   └─ YES → primitives/row-access-policies
  │
  ├─ User wants to RESTRICT which COLUMNS users can see?
  │   └─ YES → primitives/projection-policies
  │
  └─ User wants to AUDIT access or query history?
      └─ YES → primitives/account-usage-views
```

Check for broad intent first. If the user's goal spans multiple concerns (discover + protect + audit), route to the playbook. Only route to individual primitives for narrow, specific requests.

## Routes To

| Target | Mode | When Selected | What It Provides |
|--------|------|---------------|------------------|
| `playbooks/secure-sensitive-data` | Playbook | Broad intent: discover, protect, and verify end to end | Composed workflow through classification → policies → monitoring |
| `primitives/data-classification` | Reference | Narrow: discover or classify sensitive data (PII, PHI, financial) | SYSTEM$CLASSIFY syntax, classification profiles, custom classifiers |
| `primitives/masking-policies` | Reference | Narrow: hide column values based on role or context | Masking policy syntax, tag-based masking, split pattern |
| `primitives/row-access-policies` | Reference | Narrow: filter rows by user identity or role | Row access policy syntax, mapping tables, role-based filtering |
| `primitives/projection-policies` | Reference | Narrow: prevent SELECT on specific columns | Projection policy syntax, column-level access control |
| `primitives/account-usage-views` | Reference | Narrow: audit access patterns, query history, or policy usage | ACCOUNT_USAGE view reference, governance queries |
| *(multiple primitives)* | Guided | Moderate intent: user knows what they want but no pre-built playbook covers it | Agent constructs a plan from relevant primitives, user approves before execution |

## Anti-patterns

| Mis-routing | Why It Happens | Correct Route |
|-------------|----------------|---------------|
| Sending "audit my policies" to `data-classification` | "Audit" is ambiguous — could mean audit policies or audit access | If auditing *existing policies*, route to `account-usage-views`. If auditing *data for PII*, route to `data-classification` |
| Sending "protect my data" directly to `masking-policies` | User may need row-level or column-level protection, not just masking | Ask what kind of protection: hide values (masking), restrict rows (row access), or restrict columns (projection) |
| Skipping classification before protection | User says "mask all PII columns" but doesn't know which columns have PII | Route to `data-classification` first, then `masking-policies` with the results |

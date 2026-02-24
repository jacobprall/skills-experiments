---
name: data-policy
description: "**[REQUIRED]** for creating, modifying, or auditing Snowflake masking policies, row access policies, or projection policies. This skill provides critical best practices and audit checklists that identify security anti-patterns (like CURRENT_ROLE vs IS_ROLE_IN_SESSION). Triggers: masking policy, row access policy, projection policy, audit policies, policy best practices, create policy, data policy."
---

# Snowflake Data Policy Skill

## When to Use/Load
Use this skill when a user asks to design or improve data policies, audit existing data policies, troubleshoot data policy issues, or needs help choosing the right policy approach.

## Abstraction Hierarchy

This skill organizes content in layers, from low-level syntax to high-level methodology:

- **L1 — Core Concepts** (`L1_core_concepts.md`)
  - Policy syntax and structure (masking, row access, projection)
  - Data type matching rules
  - Context functions (`IS_ROLE_IN_SESSION`, `CURRENT_ROLE`, etc.)
  - Tag-based masking mechanics
  - Memoizable function syntax
  - Privileges and runtime behavior

- **L2 — Proven Patterns** (`L2_proven_patterns.md`)
  - **Pattern 1:** Attribute-Based Access Control (ABAC) — column masking and row access policies that use tags for attributes
  - **Pattern 2:** Split Pattern — extract unmask logic into a memoizable function, then call it from all policies (key pattern for extending to new data types)

- **L3 — Best Practices** (`L3_best_practices.md`)
  - **Check similar tables first** (before creating any new policy)
  - Use generic, reusable policies (avoid table-specific sprawl)
  - Centralize policies in a governance database
  - Use memoizable functions for lookups
  - Use IS_ROLE_IN_SESSION() for role checks
  - Anti-patterns to avoid
  - Visual pattern recognition for spotting bad policies

- **L4 — Guided Workflows**
  - **`L4_workflow_create.md`** — Creating new policies
    - Discovery questions to understand requirements
    - Policy type selection (masking, row access, projection)
    - Check existing policies — **is it split?** (uses shared function vs. embedded logic)
    - Apply split pattern when extending policies
    - Verification steps
  - **`L4_workflow_audit.md`** — Auditing existing policies
    - Policy discovery queries
    - Evaluation checklist with severity levels
    - Health report generation
    - Safe migration workflow with rollback

- **Reference — Compliance Regulations** (`compliance_reference.md`)
  - PCI-DSS (payment card data)
  - HIPAA (healthcare/PHI)
  - GDPR (EU personal data)
  - CCPA/CPRA (California consumer data)
  - SOX (financial reporting)
  - FERPA (student records)
  - Quick lookup table by data type and region

## Setup
1. **Load** `L1_core_concepts.md` for policy syntax and fundamentals.
2. **Load** `L2_proven_patterns.md` for reusable patterns and examples.
3. **Load** `L3_best_practices.md` for design guidelines and anti-patterns.
4. **Load** `L4_workflow_create.md` for creating new policies.
5. **Load** `L4_workflow_audit.md` for auditing existing policies.
6. **Load** `compliance_reference.md` for regulatory requirements and industry-specific policy examples.

## Intent Detection

| Intent | Triggers | Action |
|--------|----------|--------|
| CONCEPTS | "syntax", "how to write", "data types", "policy definition" | Use `L1_core_concepts.md` |
| PATTERNS | "example", "ABAC", "template", "show me how", "pattern" | Use `L2_proven_patterns.md` |
| BEST_PRACTICES | "best practice", "should I", "anti-pattern", "governance", "memoizable" | Use `L3_best_practices.md` |
| CREATE | "create policy", "new policy", "mask column", "restrict access", "extend policy", "same rules" | Use `L4_workflow_create.md` |
| AUDIT | "audit policies", "review policies", "inventory", "health check", "scattered policies", "consolidate", "migrate" | Use `L4_workflow_audit.md` |
| COMPLIANCE | "regulation", "HIPAA", "GDPR", "PCI", "CCPA", "SOX", "FERPA", "compliance", "healthcare", "financial", "privacy law" | Use `compliance_reference.md` |

## Workflow
### Step 1: Clarify intent
- Identify which layer the user needs: L1 (concepts), L2 (patterns), L3 (best practices), or L4 (workflows).
- If unclear, start with `L4_workflow_create.md`.

**⚠️ STOP**: Confirm the chosen track before drafting SQL.

### Step 2: Provide guidance
- Use the relevant document to respond.
- If drafting SQL, keep it minimal and ask for object names and roles.

### Step 3: Verify
- Ask how the user wants to validate outcomes (roles, test queries, or policy inventory).

## Stopping Points
- ✋ After Step 1 (track confirmed)
- ✋ After Step 2 (design or SQL drafted)
- ✋ After audit scope confirmed (audit workflow)
- ✋ After health report presented (audit workflow)
- ✋ Before applying fixes (all workflows)

## Output
- Clear policy recommendation or draft SQL aligned to the chosen track
- Health report with recommendations (for audit workflow)

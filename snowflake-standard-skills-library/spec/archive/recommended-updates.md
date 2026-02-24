# Recommended Framework Updates

A prioritized plan to address identified failure points in the Standard Skills Library architecture.

---

## Implementation Status

| # | Issue | Status |
|---|-------|--------|
| 1.1 | Explicit context mapping | ✅ Implemented |
| 1.2 | Mandatory probes | ✅ Implemented |
| 1.3 | Rollback/compensation actions | ✅ Implemented |
| 1.4 | Thread compaction | ✅ Implemented |
| 1.5 | Guided mode guardrails | ✅ Implemented |
| 2.1 | Routing confidence scores | ✅ Implemented |
| 2.2 | Error categories | ✅ Implemented |
| 2.3 | Dry-run mode | ✅ Implemented |
| 2.4 | Checkpoint severity | ✅ Implemented |
| 3.1 | Domain cycle validation | ✅ Implemented |
| 3.2 | Primitive staleness | ✅ Implemented |
| 3.3 | Multi-account context | ✅ Implemented |

**Files updated:**
- `router.md` — context_mapping, outputs, guided_mode, routing confidence, dry_run, validation config
- `spec/skill-schema.md` — probes, checkpoints, compensation, error categories, staleness fields, account_locator type
- `spec/standard-skills-library.md` — events, checkpoints, errors, compaction, guided mode, dry-run, multi-account, validation events
- `playbooks/secure-sensitive-data/playbook.md` — probes, compensation, checkpoint severity
- `playbooks/build-streaming-pipeline/playbook.md` — probes, compensation, checkpoint severity
- `playbooks/build-react-app/playbook.md` — probes, compensation, checkpoint severity
- All primitives — staleness tracking (tested_on, last_reviewed)

---

## Overview

This document proposes 12 enhancements based on first-principles analysis of where real-world use cases could break. Each section includes the problem, proposed solution, implementation details, and affected files.

---

## Priority 1: High Severity

### 1.1 Explicit Context Mapping Between Domains

✅ **IMPLEMENTED**

**Problem:** "Agent uses judgment" for context handoff between phases is risky and unpredictable.

**Solution:** Add explicit `context_mapping` declarations to the meta-router.

**Implementation:**

Update `router.md` front-matter schema:

```yaml
domains:
  data-transformation:
    router: routers/data-transformation
    produces: [tables, pipelines]
    outputs:                              # NEW: Structured output declarations
      - name: created_tables
        type: list[string]
        description: "Fully qualified table names created by this phase"
      - name: pipeline_name
        type: string
        description: "Name of the pipeline if one was created"

  data-security:
    router: routers/data-security
    requires: [tables]
    produces: [policies, governance]
    context_mapping:                      # NEW: Explicit input mapping
      created_tables → target_scope       # Map from previous phase output
      # If no mapping, agent must gather from user
    outputs:
      - name: applied_policies
        type: list[string]
        description: "Policy names that were created/applied"
```

Add new event type for context handoff:

```yaml
- type: context_mapped
  phase: 2
  mappings:
    - from: "phase_1.created_tables"
      to: "target_scope"
      value: ["analytics.orders", "analytics.customers"]
    - from: "user_input"
      to: "admin_role"
      value: "SECURITYADMIN"
```

**Affected files:**
- `router.md` — Add context_mapping to domains
- `spec/standard-skills-library.md` — Document context_mapping schema
- `spec/skill-schema.md` — Add context_mapping to meta-router schema

**Validation rule:** If a required input has no context_mapping and no default, agent MUST gather from user before proceeding.

---

### 1.2 Mandatory Pre-Execution Probes

**Problem:** Probes are "should" not "must" — skipping them causes late failures.

**Solution:** Make probes mandatory, blocking, and validated.

**Implementation:**

Update playbook schema to require probes with validation:

```yaml
---
type: playbook
name: secure-sensitive-data
probes:                                   # NEW: Structured probe declarations
  - id: existing_policies
    query: "SHOW MASKING POLICIES IN ACCOUNT"
    required: true
    validate:
      - condition: "count > 100"
        action: warn
        message: "Large number of existing policies — review before proceeding"
        
  - id: target_tables
    query: "SELECT COUNT(*) FROM {target_scope}.INFORMATION_SCHEMA.TABLES"
    required: true
    validate:
      - condition: "count == 0"
        action: block
        message: "No tables found in target scope"
      - condition: "count > 500"
        action: confirm
        message: "Large scope ({count} tables) — this may take significant time"

  - id: role_check
    query: "SELECT CURRENT_ROLE()"
    required: true
    validate:
      - condition: "result NOT IN ('ACCOUNTADMIN', 'SECURITYADMIN')"
        action: block
        message: "Requires ACCOUNTADMIN or SECURITYADMIN role"
---
```

Add probe execution to thread:

```yaml
- type: probes_executed
  results:
    - probe_id: existing_policies
      status: passed
      result: { count: 12 }
    - probe_id: target_tables
      status: warning
      result: { count: 847 }
      message: "Large scope (847 tables)"
    - probe_id: role_check
      status: passed
      result: "SECURITYADMIN"

- type: probe_checkpoint
  warnings: ["Large scope (847 tables) — this may take significant time"]
  options:
    - id: proceed
      description: "Continue with all 847 tables"
    - id: reduce_scope
      description: "Narrow the target scope first"
    - id: abort
      description: "Stop and review"
```

**Validation actions:**
| Action | Behavior |
|--------|----------|
| `pass` | Continue silently |
| `warn` | Log warning, continue, show in checkpoint |
| `confirm` | Pause for explicit user confirmation |
| `block` | Stop execution, escalate to user |

**Affected files:**
- `spec/skill-schema.md` — Add probes schema to playbooks
- `spec/standard-skills-library.md` — Document probe execution model
- `spec/authoring-guide.md` — Update playbook template with probes
- All playbooks — Convert prose probes to structured format

---

### 1.3 Rollback / Compensation Actions

**Problem:** Partial execution leaves orphaned objects with no cleanup path.

**Solution:** Add compensation actions to playbook steps and abort handling.

**Implementation:**

Update step schema:

```yaml
### Step 3: Create masking policies

Reference: `primitives/masking-policies`

```sql
CREATE MASKING POLICY {policy_name} AS (val STRING)
  RETURNS STRING ->
  CASE WHEN IS_ROLE_IN_SESSION('ANALYST') THEN val
       ELSE '***MASKED***'
  END;
```

Compensation:                             # NEW
```sql
DROP MASKING POLICY IF EXISTS {policy_name};
```

Creates:                                  # NEW: Track what this step creates
  - type: masking_policy
    name: "{policy_name}"
```

Add cleanup handling to thread model:

```yaml
- type: step_completed
  step: 3
  created_objects:
    - type: masking_policy
      name: "PII_EMAIL_MASK"
      fqn: "MYDB.POLICIES.PII_EMAIL_MASK"

- type: step_failed
  step: 4
  error: "Insufficient privileges"
  
- type: abort_requested
  reason: "User chose abort after step 4 failure"
  
- type: cleanup_proposed                  # NEW
  orphaned_objects:
    - type: masking_policy
      name: "PII_EMAIL_MASK"
      created_in_step: 3
      compensation: "DROP MASKING POLICY IF EXISTS MYDB.POLICIES.PII_EMAIL_MASK"
  options:
    - id: cleanup
      description: "Run compensation actions to remove created objects"
    - id: keep
      description: "Keep objects — I'll handle cleanup manually"
    - id: review
      description: "Show me what was created before deciding"
```

**Affected files:**
- `spec/skill-schema.md` — Add compensation schema to steps
- `spec/standard-skills-library.md` — Document cleanup model
- `spec/authoring-guide.md` — Update step template
- All playbooks — Add compensation actions to steps

---

### 1.4 Thread Compaction

**Problem:** Append-only threads grow unbounded, exceeding context windows.

**Solution:** Add thread compaction with phase summaries.

**Implementation:**

Add compaction events:

```yaml
# Before compaction: 47 events from phase 1

# After compaction:
- type: phase_summary                     # NEW
  phase: 1
  domain: data-transformation
  status: completed
  duration_seconds: 342
  inputs:
    target_scope: "analytics"
  outputs:
    created_tables: ["analytics.orders", "analytics.daily_summary"]
    pipeline_name: "order_refresh_pipeline"
  steps_completed: [1, 2, 3, 4, 5, 6]
  steps_skipped: []
  errors_recovered: 1
  checkpoints_passed: 3
  # Full event log available at: thread_archive/thr_abc123_phase1.yaml
```

**Compaction rules:**
1. Compact after each phase completes
2. Compact after N events (configurable, default 50)
3. Always preserve:
   - Last 10 events in full
   - All checkpoint events with human responses
   - All error events
   - Current step context
4. Archive full event log to separate storage

**Thread structure after compaction:**

```yaml
thread_id: "thr_abc123"
status: running
compaction_version: 2
archived_phases: ["thread_archive/thr_abc123_phase1.yaml"]

events:
  - type: phase_summary        # Compacted phase 1
    phase: 1
    ...
    
  - type: phase_started        # Current phase 2 - full detail
    phase: 2
    domain: data-security
    
  - type: step_started
    step: 1
    ...
```

**Affected files:**
- `spec/standard-skills-library.md` — Document compaction model
- New: `spec/thread-compaction.md` — Detailed compaction rules

---

### 1.5 Guided Mode Guardrails

**Problem:** Agent-generated plans have no validation, single approval checkpoint is insufficient.

**Solution:** Add plan validation rules, complexity limits, and step-by-step checkpoints.

**Implementation:**

**A. Plan validation rules:**

```yaml
# In meta-router or domain router
guided_mode:
  max_steps: 8                            # Refuse plans > 8 steps
  require_primitives: true                # Every step must reference a primitive
  prohibited_actions:                     # Actions that require playbook, not guided
    - "DROP DATABASE"
    - "DROP SCHEMA"
    - "GRANT OWNERSHIP"
  required_probes: true                   # Must probe before planning
  validation_rules:
    - "No step may depend on output of step > 2 positions prior"
    - "All SQL must use parameterized values from inputs"
```

**B. Step-by-step checkpoints in guided mode:**

```yaml
- type: plan_proposed
  mode: guided
  checkpoint_frequency: every_step        # NEW: Not just at plan approval
  steps:
    - step: 1
      action: "Create compute pool"
      primitive: spcs-deployment
      checkpoint: true                    # Pause after this step
    - step: 2
      action: "Build container image"
      primitive: spcs-deployment
      checkpoint: true
```

**C. Complexity escape hatch:**

```yaml
- type: plan_rejected
  reason: "complexity_exceeded"
  message: "This goal requires 12 steps. Guided mode is limited to 8 steps."
  suggestion: "Consider requesting a playbook for this workflow, or break into smaller goals."
  options:
    - id: proceed_anyway
      description: "I understand the risk — proceed with 12 steps"
      requires_confirmation: "Type 'proceed' to confirm"
    - id: simplify
      description: "Help me break this into smaller goals"
    - id: abort
      description: "Stop"
```

**Affected files:**
- `spec/standard-skills-library.md` — Document guided mode guardrails
- `router.md` — Add guided_mode configuration
- Domain routers — Add domain-specific guided_mode limits

---

## Priority 2: Medium Severity

### 2.1 Routing Confidence Scores

✅ **IMPLEMENTED**

**Problem:** Keyword matching is brittle; ambiguous intents route incorrectly.

**Solution:** Add confidence scoring with clarification threshold.

**Implementation:**

```yaml
# In meta-router routing logic
routing:
  confidence_threshold: 0.7               # Below this, ask for clarification
  ambiguity_threshold: 0.2                # If top two domains within this, ask
  
  scoring:
    keyword_match: 0.3                    # Weight for keyword presence
    intent_pattern: 0.4                   # Weight for intent pattern matching
    context_signals: 0.3                  # Weight for session context
```

Add routing event with confidence:

```yaml
- type: routed
  router: data-security
  target: playbooks/secure-sensitive-data
  mode: playbook
  confidence: 0.85                        # NEW
  alternatives:                           # NEW
    - domain: data-transformation
      confidence: 0.23
    - domain: app-deployment
      confidence: 0.08

# Or if ambiguous:
- type: routing_ambiguous                 # NEW
  top_candidates:
    - domain: data-security
      confidence: 0.52
    - domain: cost-operations
      confidence: 0.48
  clarification_options:
    - id: security
      description: "I want to protect/mask/classify data"
    - id: cost
      description: "I want to analyze/reduce Snowflake costs"
```

**Affected files:**
- `router.md` — Add confidence scoring configuration
- `spec/standard-skills-library.md` — Document confidence model
- Domain routers — Add intent patterns for scoring

---

### 2.2 Error Categories with Default Behaviors

**Problem:** Only hand-curated expected errors are handled; everything else just escalates.

**Solution:** Add error categories with default behaviors.

**Implementation:**

Add to spec:

```yaml
# Global error categories (in standard-skills-library.md)
error_categories:
  permission:
    patterns: ["Insufficient privileges", "Access denied", "not authorized"]
    retryable: false
    default_recovery: "Check role grants and retry with elevated privileges"
    escalate: true
    
  object_exists:
    patterns: ["already exists", "duplicate", "conflicts with"]
    retryable: true
    default_recovery: "Use CREATE OR REPLACE or ALTER syntax"
    
  object_not_found:
    patterns: ["does not exist", "not found", "unknown"]
    retryable: false
    default_recovery: "Verify object name and schema context"
    escalate: true
    
  transient:
    patterns: ["timeout", "connection", "temporarily unavailable", "rate limit"]
    retryable: true
    max_retries: 3
    backoff: exponential
    base_delay_seconds: 5
    
  resource:
    patterns: ["warehouse.*suspended", "quota exceeded", "resource limit"]
    retryable: true
    default_recovery: "Resume warehouse or wait for quota reset"
    max_retries: 2
    
  syntax:
    patterns: ["syntax error", "invalid", "unexpected"]
    retryable: false
    escalate: true
    default_recovery: "Review SQL syntax against primitive documentation"
    
  conflict:
    patterns: ["concurrent", "modified by", "locked"]
    retryable: true
    max_retries: 2
    backoff: linear
    base_delay_seconds: 10
```

Error matching priority:
1. Step-specific expected_errors (exact match)
2. Primitive-specific expected_errors
3. Global error categories (pattern match)
4. Unknown → escalate immediately

**Affected files:**
- `spec/standard-skills-library.md` — Add error categories section
- Primitives — Can override category defaults

---

### 2.3 Dry-Run Mode

✅ **IMPLEMENTED**

**Problem:** Users can't preview impact before execution.

**Solution:** Add dry-run mode that plans without executing.

**Implementation:**

Add dry-run to thread model:

```yaml
- type: playbook_started
  playbook: secure-sensitive-data
  mode: dry_run                           # NEW

- type: probes_executed
  # Probes still run in dry-run mode
  
- type: step_planned                      # NEW (instead of step_started)
  step: 1
  action: "Classify tables in analytics schema"
  would_execute:
    - "CALL SYSTEM$CLASSIFY('analytics.orders')"
    - "CALL SYSTEM$CLASSIFY('analytics.customers')"
    - "... (23 more tables)"
  estimated_duration: "2-5 minutes"
  
- type: step_planned
  step: 3
  action: "Create masking policies"
  would_create:
    - type: masking_policy
      name: "PII_EMAIL_MASK"
      affects_columns: ["orders.customer_email", "customers.email"]
    - type: masking_policy
      name: "PII_PHONE_MASK"
      affects_columns: ["customers.phone"]
  would_execute:
    - "CREATE MASKING POLICY PII_EMAIL_MASK..."
    - "CREATE MASKING POLICY PII_PHONE_MASK..."

- type: dry_run_summary                   # NEW
  playbook: secure-sensitive-data
  would_create:
    masking_policies: 4
    row_access_policies: 1
    projection_policies: 0
  would_modify:
    tables: 25
    columns: 47
  estimated_duration: "15-30 minutes"
  estimated_compute: "~2 credits"
  options:
    - id: execute
      description: "Proceed with actual execution"
    - id: export_plan
      description: "Export SQL scripts for manual review"
    - id: abort
      description: "Cancel"
```

**Affected files:**
- `spec/standard-skills-library.md` — Document dry-run mode
- `spec/skill-schema.md` — Add dry_run event types
- Playbooks — Add estimation hints to steps

---

### 2.4 Checkpoint Severity Levels

**Problem:** Every checkpoint interrupts equally; users experience fatigue.

**Solution:** Add severity levels with different behaviors.

**Implementation:**

```yaml
# In playbook step
**Checkpoint:** 
  severity: review                        # NEW
  present: "Classification complete. Found {pii_count} PII columns."
```

Severity levels:

| Level | Behavior | Use When |
|-------|----------|----------|
| `info` | Log event, auto-proceed after 3s unless user intervenes | Low-risk informational updates |
| `review` | Pause, require explicit approval (default) | Standard checkpoints |
| `critical` | Pause, require typed confirmation | Destructive or irreversible actions |
| `silent` | Log event, no pause | Progress tracking only |

Add batch approval:

```yaml
- type: checkpoint_reached
  severity: review
  options:
    - id: approve
    - id: approve_remaining              # NEW
      description: "Approve this and remaining review-level checkpoints"
    - id: modify
    - id: abort
```

**Affected files:**
- `spec/skill-schema.md` — Add checkpoint severity schema
- `spec/standard-skills-library.md` — Document severity levels
- Playbooks — Add severity to checkpoints

---

## Priority 3: Lower Severity

### 3.1 Domain Dependency Cycle Validation

**Problem:** Circular `produces`/`requires` could cause infinite loops.

**Solution:** Add manifest validation.

**Implementation:**

Add validation rules to manifest processing:

```yaml
# In skill-index.yaml or router.md processing
validation:
  check_domain_cycles: true
  check_routes_exist: true
  check_depends_on_exist: true
```

Validation errors:

```
ERROR: Domain dependency cycle detected
  data-transformation requires [reports]
  cost-operations produces [reports], requires [pipelines]
  data-transformation produces [pipelines]
  
  Cycle: data-transformation → cost-operations → data-transformation
  
  Resolution: Remove one of these dependencies or merge domains.
```

**Affected files:**
- `spec/standard-skills-library.md` — Document validation rules
- New: Add validation checklist to `spec/extending-routers.md`

---

### 3.2 Primitive Staleness Tracking

✅ **IMPLEMENTED**

**Problem:** Primitives can become outdated as Snowflake evolves.

**Solution:** Add version tracking and staleness warnings.

**Implementation:**

Add to primitive front-matter:

```yaml
---
type: primitive
name: masking-policies
domain: data-security
snowflake_docs: "https://docs.snowflake.com/en/..."
tested_on:                                # NEW
  snowflake_version: "8.23"
  test_date: "2026-02-15"
  test_account_type: "enterprise"
last_reviewed: "2026-02-15"               # NEW
---
```

Add staleness check to agent behavior:

```yaml
# If primitive.last_reviewed > 180 days old:
- type: staleness_warning
  primitive: masking-policies
  last_reviewed: "2025-08-15"
  days_stale: 192
  message: "This primitive was last reviewed 192 days ago. Snowflake may have changed."
  options:
    - id: proceed
      description: "Use anyway — I'll verify against current docs"
    - id: check_docs
      description: "Open Snowflake documentation for this feature"
```

**Affected files:**
- `spec/skill-schema.md` — Add staleness fields to primitive schema
- All primitives — Add tested_on and last_reviewed fields
- `spec/authoring-guide.md` — Add staleness fields to template

---

### 3.3 Multi-Account Context

**Problem:** Framework assumes single account; real users have multiple.

**Solution:** Add account context to threads and probes.

**Implementation:**

Add to playbook inputs:

```yaml
inputs:
  - name: target_account
    required: false
    description: "Snowflake account to operate on (defaults to current)"
    phase: before_start
    type: account_locator
```

Add to thread:

```yaml
- type: playbook_started
  playbook: secure-sensitive-data
  account_context:                        # NEW
    account_locator: "xy12345"
    account_name: "myorg-prod"
    region: "us-west-2"
    current_role: "SECURITYADMIN"
    current_warehouse: "COMPUTE_WH"
```

Add cross-account probe:

```yaml
probes:
  - id: account_access
    query: "SELECT CURRENT_ACCOUNT(), CURRENT_ROLE()"
    validate:
      - condition: "account != target_account"
        action: block
        message: "Connected to wrong account. Expected {target_account}, got {account}."
```

**Affected files:**
- `spec/skill-schema.md` — Add account_context schema
- `spec/standard-skills-library.md` — Document multi-account handling
- Playbooks — Add optional target_account input

---

## Implementation Phases

### Phase 1: Critical Safety (Weeks 1-2)
1. Mandatory probes with validation (1.2)
2. Rollback/compensation actions (1.3)
3. Guided mode guardrails (1.5)

### Phase 2: Reliability (Weeks 3-4)
4. Explicit context mapping (1.1)
5. Error categories (2.2)
6. Domain cycle validation (3.1)

### Phase 3: Usability (Weeks 5-6)
7. Dry-run mode (2.3)
8. Checkpoint severity levels (2.4)
9. Thread compaction (1.4)

### Phase 4: Polish (Weeks 7-8)
10. Routing confidence scores (2.1)
11. Primitive staleness tracking (3.2)
12. Multi-account context (3.3)

---

## Files to Create/Update

### New Files
- `spec/thread-compaction.md` — Detailed compaction rules
- `spec/error-categories.md` — Global error category definitions

### Major Updates
- `spec/standard-skills-library.md` — All architectural changes
- `spec/skill-schema.md` — New schema fields
- `spec/authoring-guide.md` — Updated templates
- `router.md` — Context mapping, confidence scoring, guided mode config

### All Playbooks
- Add structured probes with validation
- Add compensation actions to steps
- Add checkpoint severity levels
- Add estimation hints for dry-run

### All Primitives
- Add tested_on and last_reviewed fields

---

## Backward Compatibility

All changes are **additive**. Existing skills will continue to work:

- New fields have sensible defaults
- Probes without validation → validation skipped
- Steps without compensation → no cleanup on abort
- Checkpoints without severity → default to `review`
- Threads without compaction → grow unbounded (current behavior)

Migration path:
1. Update spec with new schemas
2. New skills use new features immediately
3. Existing skills updated incrementally
4. Add CI validation for new requirements over time

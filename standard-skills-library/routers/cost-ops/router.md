---
type: router
name: cost-ops
domain: cost-ops
routes_to:
  - primitives/warehouse-costs
  - primitives/serverless-costs
  - primitives/cortex-ai-costs
  - playbooks/investigate-cost-spike
  - playbooks/set-up-cost-monitoring
---

# Cost Operations

Single entry point for all Snowflake cost analysis, spend attribution, and budget monitoring. Consolidates warehouse costs, serverless costs, Cortex AI costs, user-level attribution, anomaly detection, and budget tracking.

## Decision Criteria

Determine the user's intent before routing. Ask if unclear.

| Input | How to Determine | Example User Statements |
|-------|-----------------|------------------------|
| **Goal** | What cost question does the user want answered? | "Why is my bill so high?", "Who is spending the most?", "Are we over budget?" |
| **Scope** | Account-wide, specific warehouse, specific user, or specific service? | "Overall costs", "ETL warehouse costs", "Data team spending" |
| **Time range** | What period? Default to last 7 days if unspecified | "Last week", "this month", "compared to last month" |

## Routing Logic

```
Start
  ├─ User wants FULL COST INVESTIGATION (why is bill high, what happened, comprehensive)?
  │   └─ YES → playbooks/investigate-cost-spike
  │
  ├─ User wants ONGOING MONITORING (alerts, budgets, tracking)?
  │   └─ YES → playbooks/set-up-cost-monitoring
  │
  ├─ User asks about WAREHOUSE or COMPUTE costs specifically?
  │   └─ YES → primitives/warehouse-costs
  │
  ├─ User asks about SERVERLESS features (tasks, Snowpipe, serverless credits)?
  │   └─ YES → primitives/serverless-costs
  │
  ├─ User asks about CORTEX AI, LLM, or AI function costs?
  │   └─ YES → primitives/cortex-ai-costs
  │
  └─ User asks about USER SPENDING, QUERY COSTS, or ATTRIBUTION?
      └─ YES → primitives/warehouse-costs (user/query attribution section)
```

Check for broad intent first. If the user says something vague like "our bill jumped" or "where is our money going," route to the investigate-cost-spike playbook. Only route to individual primitives for narrow, specific requests about a particular cost category.

## Routes To

| Target | Mode | When Selected | What It Provides |
|--------|------|---------------|------------------|
| `playbooks/investigate-cost-spike` | Playbook | Broad intent: understand cost increase, full investigation | Composed workflow: overview → breakdown → trends → anomalies → attribution → recommendations |
| `playbooks/set-up-cost-monitoring` | Playbook | User wants ongoing cost visibility or budget alerts | Budget status checks, anomaly detection setup, monitoring recommendations |
| `primitives/warehouse-costs` | Reference | Narrow: warehouse credit analysis, user/query attribution | WAREHOUSE_METERING_HISTORY queries, QUERY_ATTRIBUTION_HISTORY, user spend |
| `primitives/serverless-costs` | Reference | Narrow: task costs, Snowpipe costs, serverless credit breakdown | SERVERLESS_TASK_HISTORY queries, serverless feature cost analysis |
| `primitives/cortex-ai-costs` | Reference | Narrow: AI function costs, Cortex Analyst usage, LLM token costs | CORTEX_FUNCTIONS_USAGE_HISTORY, CORTEX_ANALYST_USAGE_HISTORY queries |
| *(multiple primitives)* | Guided | Moderate intent: user knows what they want but no playbook fits | Agent constructs a plan from relevant primitives, user approves |

## Anti-patterns

| Mis-routing | Why It Happens | Correct Route |
|-------------|----------------|---------------|
| Sending "why is my bill high?" to a single primitive | User needs a comprehensive investigation, not a narrow query | Route to `playbooks/investigate-cost-spike` for full workflow |
| Sending "AI costs" to `warehouse-costs` | Cortex AI costs use different ACCOUNT_USAGE views | Route to `primitives/cortex-ai-costs` |
| Skipping overview before drill-down | User asks about cost increase but agent jumps to warehouse detail | Start with service-level breakdown (METERING_HISTORY), then drill down |
| Sending budget questions to investigate-cost-spike | Budget monitoring is a distinct workflow | Route to `playbooks/set-up-cost-monitoring` |

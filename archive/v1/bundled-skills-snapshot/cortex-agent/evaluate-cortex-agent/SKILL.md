---
name: evaluate-cortex-agent
description: Run formal evaluations on Cortex Agents using Snowflake's native Agent Evaluations. Use this to benchmark agent performance, measure accuracy metrics (correctness, tool_selection_accuracy, tool_execution_accuracy, logical_consistency), and compare before/after improvements.
---

# Evaluate Cortex Agent

Evaluate Cortex Agents using the native Snowflake Agent Evaluations feature (preview).

**Available Metrics:**
| Metric | API Name | Requires Ground Truth | Description |
|--------|----------|----------------------|-------------|
| Answer Correctness | `correctness` | Yes | Semantic match of final answer |
| Tool Selection Accuracy | `tool_selection_accuracy` | Yes | Did agent pick the right tools? |
| Tool Execution Accuracy | `tool_execution_accuracy` | Yes | Correct tool inputs/outputs? |
| Logical Consistency | `logical_consistency` | No | Consistency across instructions, planning, and tool calls within a single execution (reference-free) |

## Prerequisites

**Account:** Agent Evaluations preview enabled

**Check if preview is available on your account:**
```sql
CALL SYSTEM$EXECUTE_AI_BATCH_EVALS('EVALS', '');
```

**Interpret the result:**
- **"Unsupported feature 'LLM EVALUATION'"** → Preview NOT available. See alternative below.
- Any other error (e.g., invalid parameters) → Preview IS available. Proceed with workflow.

---

**If Preview is NOT Available:**

Native Agent Evaluations is a preview feature not enabled on all accounts. Use the script-based evaluation alternative:

```bash
# Script-based evaluation using run_evaluation.py
uv run python scripts/run_evaluation.py \
    --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
    --eval-source database.schema.eval_table \
    --output-dir ./evals/eval_results \
    --connection CONNECTION_NAME
```

This provides:
- LLM-as-judge evaluation using `SNOWFLAKE.CORTEX.COMPLETE`
- Results stored locally in JSON files
- Flexible SQL-based filtering for evaluation sources
- No preview feature requirement

For the full workflow, use the `optimize-cortex-agent` skill with script-based evaluation.

**STOP here if preview is not available.**

---

**Access Control Setup (if preview IS available):**
```sql
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE <role>;
GRANT APPLICATION ROLE SNOWFLAKE.AI_OBSERVABILITY_EVENTS_LOOKUP TO ROLE <role>;
GRANT EXECUTE TASK ON ACCOUNT TO ROLE <role>;
GRANT CREATE FILE FORMAT ON SCHEMA <agent_schema> TO ROLE <role>;
GRANT CREATE DATASET ON SCHEMA <agent_schema> TO ROLE <role>;
GRANT CREATE TASK ON SCHEMA <agent_schema> TO ROLE <role>;
GRANT IMPERSONATE ON USER <user> TO ROLE <role>;
GRANT MONITOR ON AGENT <database>.<schema>.<agent> TO ROLE <role>;
```

**Verify Permissions Before Proceeding:**

Run these checks to verify your role has the required permissions:

```sql
-- 1. Check current role and user
SELECT CURRENT_ROLE(), CURRENT_USER();

-- 2. Check if role has CORTEX_USER database role
SHOW GRANTS TO ROLE <your_role>;
-- Look for: SNOWFLAKE.CORTEX_USER

-- 3. Check if role has AI_OBSERVABILITY_EVENTS_LOOKUP application role
SHOW GRANTS TO ROLE <your_role>;
-- Look for: SNOWFLAKE.AI_OBSERVABILITY_EVENTS_LOOKUP

-- 4. Check schema-level privileges for creating evaluation objects
SHOW GRANTS ON SCHEMA <agent_database>.<agent_schema>;
-- Look for: CREATE DATASET, CREATE TASK, CREATE FILE FORMAT

-- 5. Check agent-specific permissions
SHOW GRANTS ON AGENT <database>.<schema>.<agent_name>;
-- Look for: MONITOR privilege

-- 6. Test dataset creation permission (will fail if missing CREATE DATASET)
-- The availability check above also tests this implicitly

-- 7. Check EXECUTE TASK on account (required for evaluation runs)
SHOW GRANTS ON ACCOUNT;
-- Look for: EXECUTE TASK granted to your role
```

**Common Permission Errors and Fixes:**

| Error | Missing Permission | Fix |
|-------|-------------------|-----|
| `Insufficient privileges to operate on dataset` | CREATE DATASET | `GRANT CREATE DATASET ON SCHEMA <schema> TO ROLE <role>;` |
| `Cannot create task` | CREATE TASK | `GRANT CREATE TASK ON SCHEMA <schema> TO ROLE <role>;` |
| `Access denied to function GET_AI_OBSERVABILITY_EVENTS` | AI_OBSERVABILITY_EVENTS_LOOKUP | `GRANT APPLICATION ROLE SNOWFLAKE.AI_OBSERVABILITY_EVENTS_LOOKUP TO ROLE <role>;` |
| `Insufficient privileges on agent` | MONITOR | `GRANT MONITOR ON AGENT <db>.<schema>.<agent> TO ROLE <role>;` |
| `Cannot execute task` | EXECUTE TASK | `GRANT EXECUTE TASK ON ACCOUNT TO ROLE <role>;` |

If you encounter permission errors, work with your Snowflake administrator to grant the necessary privileges.

## Workflow

**IMPORTANT: Go through each step ONE AT A TIME. Wait for user confirmation before proceeding.**

Present this plan first:
```
I'll help you evaluate your Cortex Agent. Here's the workflow:

1. **Identify Agent** - Confirm which agent to evaluate
2. **Choose Metrics** - Select evaluation metrics (correctness, tool accuracy, etc.)
3. **Dataset Setup** - Use existing dataset or create new one
4. **Run Evaluation** - Execute evaluation against the agent
5. **View Results** - Review scores in Snowsight

Ready to proceed?
```

**STOP**: Wait for user confirmation before proceeding to Step 1.

---

### Step 1: Identify Agent and Gather Info

**Ask user:**
```
Which agent do you want to evaluate?
- Agent name (fully qualified: DATABASE.SCHEMA.AGENT_NAME)
- Connection to use
```

**If the agent name is ambiguous or unclear, DO NOT ASSUME.**

List available agents:
```sql
SHOW AGENTS IN SCHEMA <DATABASE>.<SCHEMA>;
-- Or search across databases:
SHOW AGENTS IN ACCOUNT;
```

**Extract agent configuration:**
```sql
DESC AGENT <DATABASE>.<SCHEMA>.<AGENT_NAME>;
```

The `agent_spec` column (index 6) contains a JSON object with the full agent configuration.

**Present to user:**
```
Agent: DATABASE.SCHEMA.AGENT_NAME
Tools found:
1. revenue_analyst (cortex_analyst_text_to_sql) - Revenue and sales data
2. policy_search (cortex_search) - Company policies
3. get_weather (generic) - Weather lookups

I'll help you set up an evaluation for this agent.
```

**STOP**: Confirm agent details before proceeding to Step 2.

---

### Step 2: Choose Evaluation Metrics

**Ask user:**
```
Which metrics do you want to evaluate?

1. [ ] correctness - Does the agent give correct answers?
       Requires: expected answer for each question

2. [ ] tool_selection_accuracy - Does the agent pick the right tools?
       Requires: expected tool name for each question

3. [ ] tool_execution_accuracy - Does the agent use tools correctly?
       Requires: expected tool inputs/outputs for each question

4. [ ] logical_consistency - Is the response internally consistent? (reference-free)
       Requires: nothing (no ground truth needed)

Select metrics (e.g., "1,2,4" or "all" or "just 4"):
```

**Based on selection, determine dataset requirements:**

| If user selects... | Dataset needs... |
|-------------------|------------------|
| Only `logical_consistency` | Just `INPUT_QUERY` column |
| `correctness` | `ground_truth_output` |
| `tool_selection_accuracy` | `tool_name`, `tool_sequence` in ground_truth_invocations |
| `tool_execution_accuracy` | Above + `tool_output` with actual SQL/search results |

**STOP**: Confirm metrics selection before proceeding to Step 3.

**If ONLY `logical_consistency` selected** -> Skip to Step 3 Option C (simplified flow)

---

### Step 3: Dataset Setup

Present options to user:
```
For your evaluation dataset, would you like to:

A) Use an existing evaluation dataset or table
B) Build a new dataset (I'll help curate questions from agent logs and/or generate new ones)
C) Reference-free only (just questions, no ground truth needed)

Which option?
```

**STOP**: Wait for user to choose before proceeding.

---

#### Option A: Use Existing Dataset

**Check for existing evaluation datasets:**
```sql
SHOW DATASETS IN SCHEMA <DATABASE>.<SCHEMA>;
```

Present any existing datasets:
```
I found the following existing evaluation datasets:
1. AGENT_NAME_EVAL_DS_20260101 (created 2026-01-01)
2. AGENT_NAME_EVAL_DS_20251215 (created 2025-12-15)

Would you like to use one of these, or do you have a different table?
```

**If user has an existing table (not yet registered as dataset):**
```
Please provide:
- Table name (fully qualified)
- Column with questions
- Column with expected answers (if applicable)
- Column with expected tool names (if applicable)
```

**Before proceeding with existing dataset, check agent logs for new patterns:**

Query recent agent logs:
```sql
SELECT DISTINCT
    RECORD_ATTRIBUTES:"ai.observability.record_root.input"::STRING AS USER_QUESTION,
    RECORD_ATTRIBUTES:"ai.observability.record_root.output"::STRING AS AGENT_RESPONSE
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(
    '<DATABASE>',
    '<SCHEMA>',
    '<AGENT_NAME>',
    'CORTEX AGENT'))
WHERE RECORD_ATTRIBUTES:"ai.observability.span_type" = 'record_root'
AND USER_QUESTION IS NOT NULL
ORDER BY RECORD_ATTRIBUTES:"ai.observability.record_id" DESC
LIMIT 50;
```

Present findings:
```
I checked recent agent logs and found some question patterns not covered in your existing dataset:
- [Pattern 1]: "example question"
- [Pattern 2]: "example question"

Would you like to add these to your evaluation dataset before running?
```

**STOP**: Get user decision on whether to add questions or proceed with existing dataset.

If user wants to add questions -> Go to Option B to add questions, then return.
If user declines -> Proceed to Step 4.

---

#### Option B: Build New Dataset

**Step B.1: Query Agent Logs**

Check the agent's observability logs for real user questions:
```sql
SELECT DISTINCT
    RECORD_ATTRIBUTES:"ai.observability.record_root.input"::STRING AS USER_QUESTION,
    RECORD_ATTRIBUTES:"ai.observability.record_root.output"::STRING AS AGENT_RESPONSE,
    RECORD_ATTRIBUTES:"ai.observability.record_id"::STRING AS REQUEST_ID
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(
    '<DATABASE>',
    '<SCHEMA>',
    '<AGENT_NAME>',
    'CORTEX AGENT'))
WHERE RECORD_ATTRIBUTES:"ai.observability.span_type" = 'record_root'
AND USER_QUESTION IS NOT NULL
ORDER BY RECORD_ATTRIBUTES:"ai.observability.record_id" DESC
LIMIT 50;
```

Present findings:
```
Found [N] unique questions in agent logs. Here are common patterns:
1. [Category]: "example question 1", "example question 2"
2. [Category]: "example question 3"
3. [Category]: "example question 4"

Would you like to include some of these in your evaluation dataset?
```

**STOP**: Get user input on which log questions to include.

**Step B.2: Review Agent Instructions**

Before creating questions, understand what the agent is designed to do:
```sql
DESCRIBE AGENT <DATABASE>.<SCHEMA>.<AGENT_NAME>;
```

Check `agent_spec.instructions` for:
- **Guardrails**: Does the agent refuse certain question types?
- **Persona**: Is it customer-facing? Analytics-focused?
- **Sample questions**: What questions is it designed to answer?

**Common pitfall**: Creating analytics questions for a customer-service agent that's programmed to deflect data queries.

**Step B.3: Propose Evaluation Questions**

**Target: 10-20 queries** depending on agent complexity:
- Simple agent (1-2 tools): 10-12 queries
- Medium agent (3-4 tools): 12-16 queries
- Complex agent (5+ tools): 16-20 queries

Present proposed questions one category at a time:
```
Here are proposed evaluation questions for [CATEGORY]:

| # | Question | Expected Tool | Notes |
|---|----------|---------------|-------|
| 1 | [question] | [tool] | [note] |
| 2 | [question] | [tool] | [note] |

Any to add, modify, or remove for this category?
```

**STOP**: Get user approval on each category before moving to next.

**Step B.4: Generate Ground Truth**

For each approved question, generate expected ground truth based on:
- The agent's tools and their purposes
- The semantic model / search corpus
- The agent's instructions and persona

**Important for Cortex Search tools**: Always use `cortex_search` as the tool_name (NOT custom names).

Present ground truth for review:
```
| # | Question | Expected Tool(s) | Ground Truth Output |
|---|----------|------------------|---------------------|
| 1 | [question] | [tool] | [concise expected answer] |

Review the ground truth above. Any corrections needed?
```

**STOP**: Get user approval on ground truth before creating table.

**Step B.5: Create Evaluation Table**

```sql
CREATE OR REPLACE TABLE <DATABASE>.<SCHEMA>.<AGENT_NAME>_EVAL_DATASET (
    INPUT_QUERY VARCHAR(16777216),
    EXPECTED_TOOLS VARCHAR(16777216)
);

INSERT INTO <DATABASE>.<SCHEMA>.<AGENT_NAME>_EVAL_DATASET (INPUT_QUERY, EXPECTED_TOOLS)
VALUES 
    ('<QUESTION_1>', '{"ground_truth_invocations": [{"tool_name": "<TOOL>", "tool_sequence": 1}], "ground_truth_output": "<ANSWER>"}'),
    ('<QUESTION_2>', '{"ground_truth_invocations": [{"tool_name": "<TOOL>", "tool_sequence": 1}], "ground_truth_output": "<ANSWER>"}');
```

**Critical format requirements:**
- Column name: `EXPECTED_TOOLS` (not GROUND_TRUTH)
- Column type: `VARCHAR` (not OBJECT or VARIANT)
- Insert as plain JSON string

Proceed to Step 4.

---

#### Option C: Reference-Free Evaluation Only

If user only wants `logical_consistency`:

**Propose test questions** covering all tools:
```
| # | Question |
|---|----------|
| 1 | [question covering tool 1] |
| 2 | [question covering tool 2] |
| 3 | [edge case question] |
```

**STOP**: Get user approval on questions.

**Create table:**
```sql
CREATE OR REPLACE TABLE <DATABASE>.<SCHEMA>.<AGENT_NAME>_EVAL_LC (
    INPUT_QUERY VARCHAR(16777216),
    EXPECTED_TOOLS VARCHAR(16777216)
);

INSERT INTO <DATABASE>.<SCHEMA>.<AGENT_NAME>_EVAL_LC (INPUT_QUERY, EXPECTED_TOOLS)
VALUES 
    ('<QUESTION_1>', '{}'),
    ('<QUESTION_2>', '{}');
```

Proceed to Step 4.

---

### Step 4: Register Dataset and Run Evaluation

**Set database context:**
```sql
USE DATABASE <DATABASE>;
USE SCHEMA <SCHEMA>;
```

**Register the dataset:**
```sql
CALL SYSTEM$CREATE_EVALUATION_DATASET(
    'Cortex Agent',
    '<DATABASE>.<SCHEMA>.<TABLE_NAME>',
    '<AGENT_NAME>_EVAL_DS_<YYYYMMDD>',
    OBJECT_CONSTRUCT(
        'query_text', 'INPUT_QUERY',
        'expected_tools', 'EXPECTED_TOOLS'
    )
);
```

**Run evaluation:**
```sql
CALL SYSTEM$EXECUTE_AI_OBSERVABILITY_RUN(
    OBJECT_CONSTRUCT(
        'object_name', '<DATABASE>.<SCHEMA>.<AGENT_NAME>',
        'object_type', 'CORTEX AGENT'
    ),
    OBJECT_CONSTRUCT(
        'run_name', '<AGENT_NAME>_eval_<YYYYMMDD_HHMMSS>',
        'label', 'evaluation',
        'description', '<DESCRIPTION>'
    ),
    OBJECT_CONSTRUCT(
        'type', 'dataset',
        'dataset_name', '<DATABASE>.<SCHEMA>.<DATASET_NAME>',
        'dataset_version', 'SYSTEM_AI_OBS_CORTEX_AGENT_DATASET_VERSION_DO_NOT_DELETE'
    ),
    ARRAY_CONSTRUCT(<SELECTED_METRICS>),
    ARRAY_CONSTRUCT('INGESTION', 'COMPUTE_METRICS')
);
```

**Example metric arrays:**
```sql
ARRAY_CONSTRUCT('correctness', 'tool_selection_accuracy', 'logical_consistency')
ARRAY_CONSTRUCT('logical_consistency')
```

---

### Step 5: View Results

**Generate Snowsight link:**
```sql
SELECT LOWER(CURRENT_ORGANIZATION_NAME()), LOWER(CURRENT_ACCOUNT_NAME());
```

URL format:
```
https://app.snowflake.com/<org>/<account>/#/agents/database/<DATABASE>/schema/<SCHEMA>/agent/<AGENT_NAME>/evaluations/<RUN_NAME>/records
```

**Note**: Use underscore in account name for Snowsight URLs (e.g., `sfdevrel_enterprise` not `sfdevrel-enterprise`).

**Open in browser:**
```bash
open "https://app.snowflake.com/<org>/<account>/#/agents/..."
```

Present to user:
```
Evaluation run started: <RUN_NAME>

Results include:
- Overall scores for each metric
- Per-question breakdowns
- Agent reasoning traces
- Tool call details

[Link to Snowsight]
```

**STOP**: Review results with user. Discuss findings and next steps.

---

### Step 5.1: Query Results Programmatically (Optional)

**Get per-question scores:**
```sql
SELECT 
    RECORD_ATTRIBUTES:"ai.observability.eval.target_record_id"::STRING AS RECORD_ID,
    RECORD_ATTRIBUTES:"ai.observability.eval.metric_name"::STRING AS METRIC,
    RECORD_ATTRIBUTES:"ai.observability.eval_root.score"::FLOAT AS SCORE
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(
    '<DATABASE>', '<SCHEMA>', '<AGENT_NAME>', 'CORTEX AGENT'))
WHERE RECORD_ATTRIBUTES:"snow.ai.observability.run.name" = '<RUN_NAME>'
AND RECORD_ATTRIBUTES:"ai.observability.span_type" = 'eval_root';
```

**Get failure explanations:**
```sql
SELECT 
    RECORD_ATTRIBUTES:"ai.observability.eval.target_record_id"::STRING AS RECORD_ID,
    RECORD_ATTRIBUTES:"ai.observability.eval.metric_name"::STRING AS METRIC,
    RECORD_ATTRIBUTES:"ai.observability.eval.explanation"::STRING AS EXPLANATION
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(
    '<DATABASE>', '<SCHEMA>', '<AGENT_NAME>', 'CORTEX AGENT'))
WHERE RECORD_ATTRIBUTES:"snow.ai.observability.run.name" = '<RUN_NAME>'
AND RECORD_ATTRIBUTES:"ai.observability.span_type" = 'eval';
```

---

## Troubleshooting

### Agent Refuses to Use Tools (0% scores but no errors)

The evaluation questions don't match the agent's persona. Check `DESCRIBE AGENT` for guardrails. Create questions that match what the agent is designed to do.

### "No current database" Error

```sql
USE DATABASE <DATABASE>;
USE SCHEMA <SCHEMA>;
-- Then call the procedure
```

### Ground Truth Not Parsed (Expected tools: [])

1. Column must be named `EXPECTED_TOOLS` (not GROUND_TRUTH)
2. Column type must be `VARCHAR` (not OBJECT or VARIANT)
3. Insert JSON as plain string (no PARSE_JSON)
4. JSON must use `ground_truth_invocations` array with `tool_name` and `tool_sequence`

---

## Integration with Optimization Workflow

This skill integrates with `optimize-cortex-agent` during:
- **Phase 3 (Baseline Evaluation)**: Run initial benchmark
- **Phase 6 (Validation)**: Verify improvements after changes

The closed-loop workflow:
```
Benchmark (evaluate-cortex-agent)
    |
Analyze failures -> Identify patterns
    |
Make improvements (instructions, tools, semantic views)
    |
Validate (evaluate-cortex-agent again)
    |
Compare before/after scores
```

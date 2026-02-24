---
name: dataset-curation
description: Create and manage evaluation datasets for Cortex Agents. Use this to build datasets from scratch, from production data, or to add questions to existing datasets. Outputs datasets in the format required by Snowflake Agent Evaluations.
---

# Dataset Curation for Cortex Agent Evaluation

## Purpose

Create and manage evaluation datasets for Cortex Agents. This workflow helps you build high-quality datasets that can be used with Snowflake's native Agent Evaluations (`evaluate-cortex-agent` skill).

## When to Use

- **New agent**: Create evaluation dataset from scratch
- **Production agent**: Build dataset from real production queries
- **Expanding coverage**: Add questions to existing dataset
- **Format conversion**: Convert existing Q&A data to evaluation format

## Prerequisites

**Snowflake Access:**
- Connection with write access to create tables
- For production data: access to agent event tables

**Understanding:**
- Agent's tools and capabilities
- Expected behaviors for different question types

## Dataset Format

Snowflake Agent Evaluations require a specific format:

**Source table columns:**
| Column | Type | Description |
|--------|------|-------------|
| `INPUT_QUERY` | VARCHAR | The question to ask the agent |
| `GROUND_TRUTH` | OBJECT | Expected results (structure below) |

**GROUND_TRUTH structure:**
```json
{
  "ground_truth_output": "Expected answer text",
  "ground_truth_invocations": [
    {
      "tool_name": "expected_tool",
      "tool_sequence": 1,
      "tool_input": {"param": "value"},
      "tool_output": "expected output"
    }
  ]
}
```

**What each field enables:**
| Field | Enables Metric |
|-------|----------------|
| `ground_truth_output` | `answer_correctness` |
| `ground_truth_invocations.tool_name` | `tool_selection_accuracy` |
| `ground_truth_invocations.*` (full) | `tool_execution_accuracy` |
| (none required) | `logical_consistency` |

## Workflows

### Option A: Create Dataset from Scratch

**Goal:** Design and build evaluation dataset for a new or untested agent.

#### Step 1: Understand Agent Capabilities

**Gather agent information:**

```sql
-- Get agent tools
SELECT tool_name, tool_type, tool_spec
FROM <DATABASE>.INFORMATION_SCHEMA.CORTEX_AGENT_TOOLS
WHERE agent_name = '<AGENT_NAME>';
```

Or extract from agent config:
```bash
uv run --project <SKILL_DIR> python <SKILL_DIR>/scripts/get_agent_config.py \
    --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
    --connection CONNECTION_NAME --output agent_config.json
```

**Document capabilities:**
- What tools are available?
- What questions can each tool answer?
- What are the boundaries between tools?

#### Step 2: Design Question Categories

**Recommended distribution:**

| Category | % | Purpose | Example |
|----------|---|---------|---------|
| Core use cases | 40% | Primary agent purpose | "What was Q3 revenue?" |
| Tool routing | 25% | Verify correct tool selection | "Show ML platform usage" (not general usage) |
| Edge cases | 15% | Boundary conditions | "Revenue for Feb 30th" (invalid date) |
| Ambiguous queries | 10% | Interpretation tests | "Show me recent activity" (vague) |
| Data validation | 10% | Quality checks | "Total for incomplete period" |

**For each tool, include:**
- 1-2 clear routing questions (obviously maps to this tool)
- 1 negative routing question (similar but should NOT use this tool)
- 1 ambiguous question (could use multiple tools)

#### Step 3: Draft Questions with Expected Answers

**Work with user to create questions:**

```
For each question, I need:
1. The exact question text
2. Expected answer (specific, verifiable)
3. Which tool should handle it
4. Any edge case notes

Let's start with core use cases for [TOOL_NAME]:

Question 1: "What was the total revenue for Q3 2025?"
Expected answer: ?
Expected tool: ?
```

**Expected answer guidelines:**

✅ **Good** (specific, verifiable):
- "Total revenue for Q3 2025 was $2.5M"
- "15,432 active users in December"
- "No data available for the specified period"

❌ **Bad** (vague, unverifiable):
- "Revenue information"
- "Some users were active"
- "The agent should return data"

#### Step 4: Create Dataset Table

**Create source table:**

```sql
CREATE OR REPLACE TABLE <DATABASE>.<SCHEMA>.EVAL_DATASET_<AGENT_NAME> (
    question_id INT AUTOINCREMENT,
    INPUT_QUERY VARCHAR NOT NULL,
    GROUND_TRUTH OBJECT NOT NULL,
    category VARCHAR,
    expected_tool VARCHAR,
    author VARCHAR DEFAULT CURRENT_USER(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    notes VARCHAR
);
```

**Insert questions:**

```sql
-- Answer correctness only (minimal)
INSERT INTO EVAL_DATASET_<AGENT_NAME> (INPUT_QUERY, GROUND_TRUTH, category, expected_tool, notes)
VALUES (
    'What was the total revenue for Q3 2025?',
    OBJECT_CONSTRUCT('ground_truth_output', 'Total revenue for Q3 2025 was $2.5M'),
    'core_use_case',
    'revenue_tool',
    'Basic revenue query'
);

-- With tool selection info
INSERT INTO EVAL_DATASET_<AGENT_NAME> (INPUT_QUERY, GROUND_TRUTH, category, expected_tool, notes)
VALUES (
    'Show ML platform usage for last month',
    OBJECT_CONSTRUCT(
        'ground_truth_output', 'ML Platform had 1,234 executions last month',
        'ground_truth_invocations', ARRAY_CONSTRUCT(
            OBJECT_CONSTRUCT('tool_name', 'ml_platform_tool', 'tool_sequence', 1)
        )
    ),
    'tool_routing',
    'ml_platform_tool',
    'Should route to ML tool, not general usage'
);
```

#### Step 5: Register Dataset

**Create evaluation dataset:**

```sql
CALL SYSTEM$CREATE_EVALUATION_DATASET(
    'Cortex Agent',
    '<DATABASE>.<SCHEMA>.EVAL_DATASET_<AGENT_NAME>',
    '<AGENT_NAME>_eval_v1',
    OBJECT_CONSTRUCT('query_text', 'INPUT_QUERY', 'expected_tools', 'GROUND_TRUTH')
);
```

**Deliverables:**
- Source table with 15-20 questions
- Registered evaluation dataset
- Coverage across all agent tools

---

### Option B: Create Dataset from Production Data

**Goal:** Build evaluation dataset from real production queries.

#### Step 1: Access Production Events

**Option 1: Use Agent Events Explorer (recommended)**

```bash
uv run --project <SKILL_DIR> streamlit run <SKILL_DIR>/scripts/agent_events_explorer.py -- \
    --connection CONNECTION_NAME \
    --database DATABASE \
    --schema SCHEMA \
    --agent AGENT_NAME
```

**Option 2: Query event table directly**

```sql
-- Find recent agent interactions
SELECT 
    TIMESTAMP,
    REQUEST_ID,
    RECORD:request:messages[0]:content::STRING AS question,
    RECORD:response:message:content::STRING AS answer
FROM <DATABASE>.<SCHEMA>.<EVENT_TABLE>
WHERE RECORD:request:model::STRING ILIKE '%<AGENT_NAME>%'
    AND TIMESTAMP > DATEADD(day, -7, CURRENT_TIMESTAMP())
ORDER BY TIMESTAMP DESC
LIMIT 100;
```

#### Step 2: Filter and Select Questions

**Criteria for good evaluation questions:**
- Representative of real usage
- Clear expected answer exists
- Tests specific capability
- Not duplicate of existing questions

**Filter examples:**
```sql
-- Find questions about specific topics
WHERE question ILIKE '%revenue%'

-- Find questions that used specific tools
WHERE RECORD:response LIKE '%tool_name%'

-- Find questions with errors or issues
WHERE RECORD:response:error IS NOT NULL
```

#### Step 3: Annotate with Expected Answers

**For each selected question:**
1. Review the agent's actual response
2. Determine if it was correct
3. Write the expected answer (what SHOULD have been returned)
4. Note which tool should have been used

**Using Agent Events Explorer:**
- Browse events with filters
- View question, answer, and trace
- Add expected answer annotation
- Provide feedback (correct/incorrect)
- Auto-saves to JSON file

**Manual annotation:**
```sql
CREATE OR REPLACE TABLE EVAL_ANNOTATIONS AS
SELECT 
    REQUEST_ID,
    question,
    answer AS actual_answer,
    NULL AS expected_answer,  -- Fill in manually
    NULL AS expected_tool,    -- Fill in manually
    NULL AS is_correct        -- Fill in manually
FROM production_events;
```

#### Step 4: Convert to Evaluation Format

**From annotated data:**

```sql
CREATE OR REPLACE TABLE EVAL_DATASET_<AGENT_NAME> AS
SELECT 
    ROW_NUMBER() OVER (ORDER BY timestamp) AS question_id,
    question AS INPUT_QUERY,
    OBJECT_CONSTRUCT(
        'ground_truth_output', expected_answer,
        'ground_truth_invocations', 
        CASE WHEN expected_tool IS NOT NULL 
            THEN ARRAY_CONSTRUCT(OBJECT_CONSTRUCT('tool_name', expected_tool, 'tool_sequence', 1))
            ELSE NULL 
        END
    ) AS GROUND_TRUTH,
    CASE WHEN is_correct THEN 'passing' ELSE 'failing' END AS category,
    expected_tool,
    'production_data' AS source
FROM annotated_production_data
WHERE expected_answer IS NOT NULL;
```

#### Step 5: Register Dataset

```sql
CALL SYSTEM$CREATE_EVALUATION_DATASET(
    'Cortex Agent',
    '<DATABASE>.<SCHEMA>.EVAL_DATASET_<AGENT_NAME>',
    '<AGENT_NAME>_eval_v1',
    OBJECT_CONSTRUCT('query_text', 'INPUT_QUERY', 'expected_tools', 'GROUND_TRUTH')
);
```

**Deliverables:**
- Dataset built from real production queries
- Mix of passing and failing cases
- Registered for evaluation

---

### Option C: Add Questions to Existing Dataset

**Goal:** Expand coverage of existing evaluation dataset.

#### Step 1: Review Current Coverage

```sql
-- Count by category
SELECT category, COUNT(*) as count
FROM EVAL_DATASET_<AGENT_NAME>
GROUP BY category;

-- Count by expected tool
SELECT expected_tool, COUNT(*) as count
FROM EVAL_DATASET_<AGENT_NAME>
GROUP BY expected_tool;

-- List all questions
SELECT question_id, INPUT_QUERY, category, expected_tool
FROM EVAL_DATASET_<AGENT_NAME>
ORDER BY question_id;
```

**Identify gaps:**
```
Current Coverage:
- revenue_tool: 5 questions
- usage_tool: 3 questions
- ml_platform_tool: 0 questions  ← GAP
- Edge cases: 1 question         ← GAP
- Tool routing tests: 2 questions ← Need more

Recommendations:
1. Add 2 questions for ml_platform_tool
2. Add 3 edge case questions
3. Add 2 tool routing tests
```

#### Step 2: Add New Questions

```sql
INSERT INTO EVAL_DATASET_<AGENT_NAME> (INPUT_QUERY, GROUND_TRUTH, category, expected_tool, notes)
VALUES 
-- ML platform questions
(
    'How many ML models were trained last quarter?',
    OBJECT_CONSTRUCT(
        'ground_truth_output', '47 models were trained in Q4 2025',
        'ground_truth_invocations', ARRAY_CONSTRUCT(
            OBJECT_CONSTRUCT('tool_name', 'ml_platform_tool', 'tool_sequence', 1)
        )
    ),
    'core_use_case',
    'ml_platform_tool',
    'New - filling ML tool coverage gap'
),
-- Edge case
(
    'What was revenue on February 30th, 2025?',
    OBJECT_CONSTRUCT('ground_truth_output', 'February 30th is not a valid date. Please provide a valid date.'),
    'edge_case',
    NULL,
    'Invalid date edge case'
),
-- Tool routing
(
    'Show platform usage statistics',
    OBJECT_CONSTRUCT(
        'ground_truth_output', 'I need clarification: Are you asking about ML Platform usage or general Snowflake platform usage?'
    ),
    'ambiguous',
    NULL,
    'Ambiguous - should ask for clarification'
);
```

#### Step 3: Re-register Dataset

**Important:** After adding questions, re-register the dataset:

```sql
-- Re-create with new version name
CALL SYSTEM$CREATE_EVALUATION_DATASET(
    'Cortex Agent',
    '<DATABASE>.<SCHEMA>.EVAL_DATASET_<AGENT_NAME>',
    '<AGENT_NAME>_eval_v2',  -- New version
    OBJECT_CONSTRUCT('query_text', 'INPUT_QUERY', 'expected_tools', 'GROUND_TRUTH')
);
```

**Deliverables:**
- Expanded dataset with better coverage
- New dataset version registered

---

## Best Practices

### Question Design

**Do:**
- ✅ Use realistic language (how users actually ask)
- ✅ Include variations ("Q3 revenue", "third quarter revenue", "revenue for Jul-Sep")
- ✅ Test boundaries (first day, last day, invalid inputs)
- ✅ Include negative cases (questions agent should NOT answer)

**Don't:**
- ❌ Use overly formal language users wouldn't use
- ❌ Make all questions easy/obvious
- ❌ Skip edge cases
- ❌ Ignore tool routing scenarios

### Expected Answers

**Do:**
- ✅ Be specific with numbers ("$2.5M" not "around 2 million")
- ✅ Match expected format ("15,432 users" if agent formats with commas)
- ✅ Include context ("for Q3 2025" not just the number)
- ✅ Document what constitutes "close enough"

**Don't:**
- ❌ Use vague descriptions
- ❌ Expect exact string matches for long responses
- ❌ Forget about date/time formatting variations

### Coverage

**Minimum targets:**
- 15-20 questions total
- At least 1-2 questions per tool
- 25% tool routing tests
- Mix of passing and expected-failing cases

### Maintenance

- Version your datasets (`_v1`, `_v2`, etc.)
- Document changes between versions
- Keep source table for easy updates
- Re-register after modifications

---

## Integration with Other Skills

**From `adhoc-testing-for-cortex-agent`:**
- Test questions interactively first
- Add validated questions here for formal evaluation

**To `evaluate-cortex-agent`:**
- Use created dataset to run evaluations
- Measure agent performance with metrics

**In `optimize-cortex-agent`:**
- Create dataset in Phase 2
- Use for baseline and validation evaluations

---
name: optimize-cortex-agent
description: |
   This goes through a workflow to guide AI assistants through optimizing Snowflake Cortex Agents for production readiness through systematic evaluation, improvement, and generalization. The process uses AI reasoning combined with human domain expertise to achieve significant accuracy improvements.
   Use this workflow when:
   - Preparing an agent for production deployment
   - Agent has known accuracy or performance issues
   - Need to validate agent behavior systematically
   - Want to ensure agent generalizes beyond test cases
---

# Optimize Cortex Agent 

## Required Access & Tools

**Snowflake Access:**
- Connection to Snowflake account with Cortex Agents access
- Permissions to query agent schemas and run evaluations
- Ability to modify agent configurations (for updates)

**Essential Scripts:** (in `../scripts/` directory)
- `get_agent_config.py` - Extract agent configuration
- `run_evaluation.py` - Execute evaluation questions in batch from any table or SQL query
- `create_or_alter_agent.py` - Create or alter/modify agents
- `test_agent.py` - Test individual questions for debugging
- `agent_events_explorer.py` - Interactive Streamlit app to explore agent events, annotate responses, and create evaluation datasets
- `fetch_events_from_event_table.py` - Fetch events from AI Observability Event Table
- `load_eval_data_from_json.py` - Load evaluation dataset JSON into Snowflake table

Whenever running scripts, make sure to use `uv`.

**Human Collaboration:**
- Domain expert availability (2-3 sessions, 2-3 hours each)
- Expert should understand agent's domain and expected behavior

**Tracking changes:**
Use the `agent-system-of-record` skill to track changes. Follow its organizational protocol for workspace structure, versioning, and file organization.

## Progress Tracking (Required)

**CRITICAL:** Use the TodoWrite tool to track progress through this workflow. Update todo status as you complete each phase.

When starting this workflow, create todos for ALL phases upfront:

```
Phase 1: Agent Discovery & Workspace Setup [in_progress]
Phase 2: Evaluation Dataset Creation [pending]
Phase 3: Baseline Evaluation [pending]
Phase 4: Instruction Improvements [pending]
Phase 5: Overfitting Detection [pending]
Phase 6: Generalization & Validation [pending]
```

**Rules for todo progression:**
- Mark current phase as `in_progress` when starting it
- Mark phase as `completed` only when ALL deliverables are achieved
- Move to next phase by marking it `in_progress`
- Update todos IMMEDIATELY when phase status changes - do not batch updates

**Phase transition triggers:**
- Phase 1 → 2: Workspace created, agent config extracted, optimization log initialized
- Phase 2 → 3: Evaluation dataset ready (15-20 questions with expected answers)
- Phase 3 → 4: Baseline evaluation complete, failure patterns identified and categorized
- Phase 4 → 5: Instruction improvements applied, re-evaluation shows improvement
- Phase 5 → 6: Overfitting issues identified and prioritized
- Phase 6 → Done: Generalized instructions validated, deployment summary created

---

## The Optimization Process

### Phase 1: Agent Discovery, Workspace Setup & Configuration Extraction

**Goal:** Identify which agent to optimize, establish versioned workspace structure, and extract current configuration.

**What You Should Do:**

1. **Discover the agent:**
   
   **Check if user already has agent in mind:**
   
   Ask user:
   ```
   Do you already have a specific agent you want to optimize?
   
   If yes, please provide:
   - Agent name
   - Database and schema where it's located
   
   If no, I can query Snowflake to show available agents.
   ```
   
   **If user doesn't have agent in mind, query Snowflake for available agents:**
   ```sql
   -- Find agents in accessible schemas
   SELECT agent_name, agent_schema, created_on, comment
   FROM <DATABASE>.INFORMATION_SCHEMA.CORTEX_AGENTS;
   
   -- For each agent, get tool count
   SELECT agent_name, COUNT(*) as tool_count
   FROM <DATABASE>.INFORMATION_SCHEMA.CORTEX_AGENT_TOOLS
   GROUP BY agent_name;
   ```
   
   Present findings to user:
   - List agents by database.schema
   - Show tool count, last modified date, description
   - Ask which agent they want to optimize

2. **Confirm workspace location and production status:**
   - Fully qualified agent name (`DATABASE.SCHEMA.AGENT`)
   - Workspace directory (default: current dir + FQN with underscores)
   - Is this a production agent? If yes, ask user for the **fully qualified clone name** (`DATABASE.SCHEMA.CLONE_AGENT_NAME`) where they want the clone created.

3. **Create workspace:**
   ```bash
   AGENT_FQN="DATABASE.SCHEMA.AGENT"
   AGENT_DIR_NAME=$(echo "$AGENT_FQN" | tr '.' '_')
   WORKSPACE_DIR="${WORKSPACE_DIR:-$(pwd)/$AGENT_DIR_NAME}"
   mkdir -p "$WORKSPACE_DIR/versions"
   ```

4. **For production agents, create clone first:**

   ⚠️ **Ask the user:** "What fully qualified name would you like for the clone? (e.g., `DATABASE.SCHEMA.CLONE_NAME`)"

   ```bash
   VERSION="v$(date +%Y%m%d-%H%M)"
   VER_DIR="$WORKSPACE_DIR/versions/$VERSION"
   mkdir -p "$VER_DIR/evals"

   uv run python ../scripts/get_agent_config.py --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
     --connection CONNECTION_NAME --output "$VER_DIR/full_agent_spec.json"

   # Create clone using user-provided fully qualified name (CLONE_DATABASE.CLONE_SCHEMA.CLONE_AGENT_NAME)
   uv run python ../scripts/create_or_alter_agent.py create --agent-name CLONE_AGENT_NAME --config-file "$VER_DIR/full_agent_spec.json" \
     --database CLONE_DATABASE --schema CLONE_SCHEMA --connection CONNECTION_NAME

   # Use the clone's FQN (CLONE_DATABASE.CLONE_SCHEMA.CLONE_AGENT_NAME) for all subsequent operations
   ```

5. **Create initial version folder for baseline:**
   ```bash
   VERSION="v$(date +%Y%m%d-%H%M)"
   VER_DIR="$WORKSPACE_DIR/versions/$VERSION"
   mkdir -p "$VER_DIR/evals"
   ```

6. **Extract agent configuration to version folder:**
   ```bash
   # Get agent config JSON
   uv run python ../scripts/get_agent_config.py --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
     --connection CONNECTION_NAME --output "$VER_DIR/agent_config.json"
   
   # Extract into separate files directly to version folder
   uv run python ../scripts/extract_agent_config.py --config-file "$VER_DIR/agent_config.json" --output-dir "$VER_DIR"
   ```
   
   Files are now stored in:
   - `$VER_DIR/agent_config.json` - Full configuration
   - `$VER_DIR/instructions_orchestration.txt` - Current instructions
   - `$VER_DIR/tools_summary.json` - Tool inventory

7. **Review with user:**
   - "Here are the agent's current orchestration instructions (X characters)"
   - "The agent has Y tools available: [list]"
   - "What is this agent designed to do?"
   - "Are there known accuracy or performance issues?"

8. **Initialize optimization log:**
   Create `<WORKSPACE_DIR>/optimization_log.md` following the template from `agent-system-of-record` skill.

**Deliverables:**
- Selected agent name
- Workspace directory structure established
- Production clone created at user-specified FQN (if applicable)
- Extracted configuration in version folder
- Understanding of agent's purpose and known issues
- Optimization log initialized

---

### Phase 2: Evaluation Dataset Creation

**Goal:** Ensure you have 15-20 diverse evaluation questions with expected answers.

**Step 0: Check Native Evaluation Availability & Permissions**

Before choosing an evaluation approach, check if Native Snowflake Agent Evaluations (preview) is available and you have the required permissions.

**LOAD:** `evaluate-cortex-agent` skill and follow the **Prerequisites** section to:
1. Run `SYSTEM$CREATE_EVALUATION_DATASET` test to check availability (requires database/schema context)
2. Verify your role has required permissions (if available)

**Summary of outcomes:**
- **"Unknown function" error** → Preview NOT available. Use script-based evaluation only.
- **"Object does not exist" or parameter error** → Preview IS available. Both options available (if permissions are set up).

---

**If Native Evaluation is NOT available:**

Inform the user:
```
Native Snowflake Agent Evaluations is a preview feature not enabled on this account.

We'll use script-based evaluation (run_evaluation.py) which provides:
- LLM-as-judge evaluation using SNOWFLAKE.CORTEX.COMPLETE
- Results stored locally in JSON files
- Good for iteration and debugging
- Flexible SQL-based filtering

This approach is fully functional for the optimization workflow.
```

Skip the evaluation approach choice below and proceed with script-based evaluation.

---

**If Native Evaluation IS available, choose your evaluation approach:**

| Approach | Best For | Dataset Format |
|----------|----------|----------------|
| **Script-based** (`run_evaluation.py`) | Quick iteration, local analysis | `question`, `expected_answer` columns |
| **Native Snowflake** (`evaluate-cortex-agent` skill) | Formal benchmarking, Snowsight tracking | `INPUT_QUERY`, `GROUND_TRUTH` (OBJECT) columns |

Ask user:
```
Which evaluation approach would you like to use?

A) Script-based evaluation (run_evaluation.py)
   - Results stored locally in JSON files
   - Good for quick iteration and debugging
   - Flexible SQL-based filtering

B) Native Snowflake Agent Evaluations
   - Uses SYSTEM$EXECUTE_AI_OBSERVABILITY_RUN
   - Built-in metrics: correctness, tool_selection_accuracy, logical_consistency
   - Results visible in Snowsight Evaluations UI
   - Better for formal benchmarking and tracking over time
```

**For detailed dataset creation guidance, LOAD:** `dataset-curation` skill

**What You Should Do:**

1. **Check if evaluation dataset already exists:**
   
   Ask user:
   ```
   Do you already have an evaluation dataset for this agent? 
   
   For example:
   - A table with test questions and expected answers
   - A spreadsheet or document with evaluation cases
   - Production queries you've been tracking
   - Known failure cases you want to test
   
   If yes, where is it located?
   ```

2. **If evaluation dataset exists:**
   - Query the table/file to see existing questions
   - Count total questions available
   - Review coverage across agent capabilities
   - Validate expected answers are specific enough
   - Assess if additional questions are needed
   
   Present findings:
   ```
   I found your existing evaluation dataset:
   - Location: DATABASE.SCHEMA.agent_eval
   - Total Questions: 13
   - Tools covered: X, Y, Z
   - Question types: [list categories you observe]
   
   Coverage looks good/We should add questions for [gaps identified].
   Ready to proceed with baseline evaluation?
   ```
   
   **Note:** The evaluation source must have these columns:
   - `question` (required): The question text
   - `expected_answer` (required): Expected answer for comparison
   - Optional: `tool_used`, `category`, `difficulty`, `author`, `date_added`, or any other metadata

3. **If no evaluation dataset exists, create one:**

   You have two main approaches:
   - **Option A:** Create from production data (recommended if agent has been used)
   - **Option B:** Create from scratch (if agent is new or production data unavailable)

   **Option A: Create Evaluation Dataset from Production Data**
   
   If your agent has been running in production, you can use the Agent Events Explorer to:
   - Browse real production queries with natural language filters
   - Filter by question content, answer quality, or trace patterns
   - View traces in a scrollable, searchable format
   - Annotate responses with expected answers and feedback
   - Dataset auto-saves after each annotation to JSON file
   - Optionally export directly to Snowflake table
   
   **Launch the Agent Events Explorer:**
   ```bash
   # Start the interactive Streamlit app
   uv run streamlit run ../scripts/agent_events_explorer.py -- \
     --connection CONNECTION_NAME \
     --database DATABASE \
     --schema SCHEMA \
     --agent AGENT_NAME
   ```
   
   **Workflow in the Agent Events Explorer:**
   
   1. **Fetch Events** - Query production agent events with filters:
      - Set time range, question filters, answer filters
      - Use AI filters to find specific patterns (e.g., "questions about SQL errors")
      - Limit results to manageable size (e.g., 50-100 events)
   
   2. **Review & Annotate** - For each event:
      - See the question, answer, and full trace (scrollable JSON view)
      - Add expected answer for the question
      - Provide feedback (positive/negative, message, categories)
      - Dataset auto-saves after each "Submit & Next"
      - Skip records as needed
   
   3. **Dataset Auto-Saved** - Evaluation dataset created automatically:
      - After each annotation, the complete dataset is saved to `eval_dataset_{DATABASE}_{SCHEMA}_{AGENT}.json`
      - Includes all annotated records with question, answer, expected_answer, feedback, trace
      - No manual export needed - file is always up-to-date
      - Optional: Export directly to Snowflake table from the UI
   
   **Example workflow:**
   ```
   You: "Let me help you create an evaluation dataset from production data.
        I'll launch the Agent Events Explorer so you can review and annotate
        real production queries."
   
   [Launch Streamlit app]
   
   You: "In the app:
        1. Fetch recent events (suggest: last 7 days, limit 50)
        2. Review each question-answer pair (with scrollable trace view)
        3. Add expected answer for each question
        4. Provide feedback: positive/negative, optional message and categories
        5. Dataset auto-saves after each annotation to eval_dataset_{DATABASE}_{SCHEMA}_{AGENT}.json
        6. Aim for 15-20 annotated examples with good coverage"
   
   [User works in Streamlit app]
   
   User: "I've annotated 18 questions"
   
   You: "Great! The evaluation dataset has been auto-saved. Let me load that into 
        a Snowflake table for evaluation..."
   ```
   
   **Benefits of production-based dataset:**
   - Real user questions (not synthetic)
   - Includes edge cases that actually occurred
   - Shows current failure patterns
   - Faster than creating from scratch
   
   **Using the Auto-Saved Dataset:**
   
   The Agent Events Explorer auto-saves to `eval_dataset_{DATABASE}_{SCHEMA}_{AGENT}.json` after each annotation.
   This file contains all annotated records with fields: `timestamp`, `request_id`, `question`, `answer`, 
   `expected_answer`, `feedback` (JSON string), `trace` (JSON string).
   
   Load the JSON into Snowflake using the provided script:
   
   ```bash
   uv run python ../scripts/load_eval_data_from_json.py \
       --json-file eval_dataset_{DATABASE}_{SCHEMA}_{AGENT}.json \
       --database DATABASE \
       --schema SCHEMA \
       --agent-name AGENT_NAME \
       --connection CONNECTION_NAME
   ```
   
   This creates table `{DATABASE}.{SCHEMA}.EVAL_DATASET_{AGENT_NAME}` with schema:
   - `timestamp` (TIMESTAMP)
   - `request_id` (VARCHAR)
   - `question` (VARCHAR) - Required by run_evaluation.py
   - `answer` (VARCHAR)
   - `expected_answer` (VARCHAR) - Required by run_evaluation.py
   - `feedback` (VARIANT) - JSON object
   - `trace` (VARIANT) - JSON object
   
   Or use the direct Snowflake export from the Agent Events Explorer (specify table FQN in the app).
   
   **Auxiliary Notes:**
   - The dataset is directly compatible with `run_evaluation.py` (both use `expected_answer` column)
   - Feedback is stored as JSON string matching the [Cortex Agents Feedback REST API](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-feedback-rest-api) format
   - Feedback submitted via the app is also sent to the feedback endpoint (may have ingestion delay)
   - Multiple feedback submissions are allowed per `request_id` - query the feedback table for complete history

   **Option B: Create Evaluation Dataset from Scratch**

   **Understand agent capabilities:**
   - Review tools available to agent
   - Understand primary use cases
   - Identify edge cases and failure scenarios

   ```
   I recommend creating 15-20 evaluation questions with this distribution:
   
   - Core use cases (40%): Primary questions the agent was built for
   - Tool routing tests (25%): Verify correct semantic model selection
   - Edge cases (15%): Boundary conditions, unusual requests
   - Ambiguous queries (10%): Questions requiring interpretation
   - Data validation (10%): Questions requiring data quality checks
   
   For tool routing specifically, I'll create questions that test:
   - Clear single-tool routing (baseline)
   - Ambiguous multi-tool scenarios (asks for clarification)
   - Multi-tool coordination (queries multiple tools)
   - Negative routing (avoids wrong tool selection)
   
   Does this coverage make sense for your agent?
   ```

   - Propose specific questions based on tools and use cases
   - Ask user to refine or confirm each question
   - For each question, ask: "What should the expected answer be?"
   - Help format expected answers with specific, verifiable details

   **Question Type Coverage - Include These Categories:**
   
   When creating evaluation questions, ensure you cover these critical areas:
   
   **A. Core Use Cases (40%):** Primary questions the agent was built for
   - Basic queries for each tool
   - Common aggregations and filters
   - Standard time period queries
   
   **B. Tool Routing Tests (25%):** Verify agent selects correct semantic model
   - **Clear routing:** Questions that clearly map to one tool
     - Example: "How many Streamlit apps were viewed?" → feature_usage tool
     - Example: "What was Native Apps revenue?" → native_apps tool
   - **Ambiguous routing:** Questions where tool choice isn't obvious
     - Example: "Show me ML usage" (could be product_categories or overall_ai_ml_usage)
     - Test if agent asks for clarification
   - **Multi-tool coordination:** Questions requiring multiple tools
     - Example: "Compare Notebooks adoption vs Streamlit adoption"
   - **Negative routing:** Questions that might route to wrong tool
     - Example: Ensure "Streamlit Open Source" doesn't use "Streamlit in Snowflake" tool
   
   **C. Edge Cases (15%):** Boundary conditions, unusual requests
   - Missing data scenarios
   - Outlier detection
   - Empty result sets
   
   **D. Ambiguous Queries (10%):** Questions requiring interpretation
   - Vague time periods ("lately", "recently")
   - Implicit comparisons ("better", "more of a")
   - Undefined metrics ("adoption", "usage")
   
   **E. Data Validation (10%):** Questions requiring quality checks
   - Incomplete time coverage
   - Double-counting risks
   - Scale reasonableness checks

   **Example Interaction:**
   ```
   You: "Based on the agent's tools, I suggest this question: 
        'What was the total AI/ML spend for Q3 2025?'
        Does this align with how users would ask?"

   User: "Yes, but also test 'AI spending in Q3' and 'third quarter AI credits'"

   You: "Good point. I'll add those variations. What's the expected answer?"

   User: "Approximately 2.5M credits covering July-September 2025"

   You: "Should I also test tool routing? For example, testing if the agent 
        correctly chooses the product categories tool vs overall usage tool?"

   User: "Yes, add routing questions for each of our semantic models"
   ```

   ```sql
   CREATE TABLE IF NOT EXISTS <DATABASE>.<SCHEMA>.agent_eval (
       question_id INT AUTOINCREMENT,
       question TEXT NOT NULL,
       expected_answer TEXT NOT NULL,
       tool_used TEXT,
       author VARCHAR(100),
       date_added DATE DEFAULT CURRENT_DATE(),
       notes TEXT,
       PRIMARY KEY (question_id)
   );
   
   INSERT INTO agent_eval (question, expected_answer, tool_used, author, notes)
   VALUES (...);
   ```

6. **Validate evaluation set:**
   - Check tool coverage: "We have routing questions for X out of Y tools"
   - Check single-tool questions: "Each tool has at least 1-2 clear routing questions"
   - Check multi-tool questions: "We have N questions testing tool coordination"
   - Check ambiguous scenarios: "We test if agent asks for clarification when tool choice is unclear"
   - Check negative routing: "We verify agent doesn't use wrong tools for similar queries"
   - Check question diversity: "Questions span different types (aggregation, filtering, etc.)"
   - Identify gaps: "We don't have routing questions for [specific tool] yet"
   - Confirm with user before proceeding

7. **Log evaluation dataset location to optimization log:**
   Update `<WORKSPACE_DIR>/optimization_log.md` under the "Evaluation dataset" section with:
   - Location: `<local path or DATABASE.SCHEMA.TABLE/VIEW>`
   - Coverage: `<question count, categories>`
   
   Example:
   ```
   ## Evaluation dataset
   - Location: SNOWFLAKE_INTELLIGENCE.AGENTS.agent_eval
   - Coverage: 18 questions, covering core use cases (7), tool routing (5), edge cases (3), ambiguous queries (2), data validation (1)
   ```

**Deliverables:**
- 15-20 evaluation questions in database
- Each with specific, verifiable expected answer
- Good coverage across agent capabilities
- **25% of questions specifically test tool routing**
- At least 1-2 routing questions per semantic model/tool
- Evaluation dataset location logged in `optimization_log.md`

---

### Phase 3: Baseline Evaluation

**Goal:** Measure current agent accuracy and identify failure patterns.

**Choose evaluation method based on Phase 2 availability check and decision:**

- If Native Evaluation was **NOT available** in Phase 2 → Use Option A (Script-Based) only
- If Native Evaluation **IS available** → Use whichever option was chosen in Phase 2

**⚠️ IMPORTANT: Pick ONE method and stick with it throughout the entire optimization workflow.**

Once you choose an evaluation method (Option A or Option B), use ONLY that method for:
- Baseline evaluation (this phase)
- Re-evaluation after improvements (Phase 4)
- Final validation (Phase 6)

This ensures consistent metrics and valid before/after comparisons.

---

#### Option A: Script-Based Evaluation (run_evaluation.py)

Use this for quick iteration and local analysis.

1. **Run evaluation using run_evaluation.py:**
   
   The `run_evaluation.py` script supports flexible evaluation sources:
   
   **Option A: Use a table or view**
   ```bash
   uv run python ../scripts/run_evaluation.py \
       --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
       --eval-source database.schema.eval_table \
       --output-dir "$VER_DIR/evals/eval_baseline" \
       --connection CONNECTION_NAME
   ```
   
   **Option B: Use a SQL query to filter questions**
   ```bash
   # Example: Test only first 5 questions
   uv run python ../scripts/run_evaluation.py \
       --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
       --eval-source "SELECT * FROM database.schema.eval_table LIMIT 5" \
       --output-dir "$VER_DIR/evals/eval_baseline" \
       --connection CONNECTION_NAME
   
   # Example: Test specific category
   uv run python ../scripts/run_evaluation.py \
       --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
       --eval-source "SELECT question, expected_answer FROM eval_table WHERE category = 'finance'" \
       --output-dir "$VER_DIR/evals/eval_baseline" \
       --connection CONNECTION_NAME
   ```
   
   **Script behavior:**
   - Automatically detects if input is table name or SQL query
   - Requires `question` and `expected_answer` columns
   - Includes any optional metadata columns (tool_used, category, etc.)
   - Creates individual response files (q01_response.json, q02_response.json, etc.)
   - Generates evaluation_summary.json with all results
   
   **Tip:** For large evaluation sets (>20 questions), consider running in batches:
   ```bash
   # Test critical questions first
   uv run python ../scripts/run_evaluation.py --agent-name AGENT_NAME --database DB --schema SCHEMA \
       --eval-source "SELECT * FROM eval_table WHERE difficulty = 'critical'" \
       --output-dir "$VER_DIR/evals/eval_critical" \
       --connection CONNECTION_NAME
   
   # Then test remaining questions
   uv run python ../scripts/run_evaluation.py --agent-name AGENT_NAME --database DB --schema SCHEMA \
       --eval-source "SELECT * FROM eval_table WHERE difficulty != 'critical'" \
       --output-dir "$VER_DIR/evals/eval_remaining" \
       --connection CONNECTION_NAME
   ```

2. **Calculate accuracy:**
   ```python
   # Analyze evaluation_summary.json
   total_questions = len(results)
   correct_answers = sum(1 for r in results if r['success'])
   accuracy = correct_answers / total_questions * 100
   ```
   
   Present to user:
   ```
   Baseline Evaluation Results:
   - Total Questions: 13
   - Correct Answers: 4 (31%)
   - Failed Answers: 9 (69%)
   ```

**Skip to step 3 below (Analyze each failure deeply).**

---

#### Option B: Native Snowflake Agent Evaluations

**Note:** This option requires the Native Agent Evaluations preview to be enabled on your account. If the availability check in Phase 2 showed "Unknown function" error, skip this option and use Option A instead.

Use this for formal benchmarking with built-in metrics and Snowsight tracking.

**LOAD:** `evaluate-cortex-agent` skill for detailed workflow.

---

**⚠️ CRITICAL: DO NOT MIX EVALUATION METHODS**

If you chose Native Snowflake Agent Evaluations (Option B), you MUST:
1. Use ONLY the native evaluation approach throughout the optimization
2. Wait for native evaluation runs to complete before proceeding
3. Query results from `GET_AI_OBSERVABILITY_EVENTS` - DO NOT fall back to `run_evaluation.py`

Native evaluations may take several minutes to complete. **Be patient and poll for results:**

```sql
-- Check if evaluation run has completed
SELECT COUNT(*) as record_count
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(
    '<DATABASE>', '<SCHEMA>', '<AGENT_NAME>', 'CORTEX AGENT'))
WHERE RECORD_ATTRIBUTES:"snow.ai.observability.run.name" = '<RUN_NAME>'
AND RECORD_ATTRIBUTES:"ai.observability.span_type" = 'eval_root';
```

If `record_count` is 0 or less than expected, wait 30-60 seconds and try again. The evaluation is running asynchronously.

**Do NOT:**
- Switch to `run_evaluation.py` "while waiting" for native results
- Run both evaluation methods in parallel on the same questions
- Mix results from different evaluation methods in your analysis

Mixing methods creates confusion about which metrics to trust and makes comparison impossible.

---

**Quick summary:**

1. **Ensure dataset is in native format:**
   
   If you created dataset with `question`/`expected_answer` columns, convert it:
   ```sql
   CREATE OR REPLACE TABLE EVAL_NATIVE_FORMAT AS
   SELECT 
       question AS INPUT_QUERY,
       OBJECT_CONSTRUCT('ground_truth_output', expected_answer) AS GROUND_TRUTH
   FROM existing_eval_table;
   ```

2. **Register evaluation dataset:**
   ```sql
   CALL SYSTEM$CREATE_EVALUATION_DATASET(
       'Cortex Agent',
       '<DATABASE>.<SCHEMA>.EVAL_NATIVE_FORMAT',
       '<AGENT_NAME>_baseline_dataset',
       OBJECT_CONSTRUCT('query_text', 'INPUT_QUERY', 'expected_tools', 'GROUND_TRUTH')
   );
   ```

3. **Run baseline evaluation:**
   ```sql
   CALL SYSTEM$EXECUTE_AI_OBSERVABILITY_RUN(
       OBJECT_CONSTRUCT('object_name', '<DB>.<SCHEMA>.<AGENT>', 'object_type', 'CORTEX AGENT', 'object_version', ''),
       OBJECT_CONSTRUCT('run_name', 'baseline_v1', 'label', 'baseline', 'description', 'Initial baseline before optimization'),
       OBJECT_CONSTRUCT('type', 'dataset', 'dataset_name', '<AGENT_NAME>_baseline_dataset', 'dataset_version', 'SYSTEM_AI_OBS_CORTEX_AGENT_DATASET_VERSION_DO_NOT_DELETE'),
       ARRAY_CONSTRUCT('answer_correctness', 'tool_selection_accuracy', 'logical_consistency'),
       ARRAY_CONSTRUCT('INGESTION', 'COMPUTE_METRICS')
   );
   ```

4. **Query and present results:**
   ```sql
   WITH eval_results AS (
       SELECT * FROM TABLE(
           GET_AI_OBSERVABILITY_EVENTS(
               OBJECT_CONSTRUCT('object_name', '<DB>.<SCHEMA>.<AGENT>', 'object_type', 'CORTEX AGENT'),
               'baseline_v1'
           )
       )
   ),
   scores AS (
       SELECT 
           r.value:ATTRIBUTES:input_query::STRING AS question,
           r.value:ATTRIBUTES:answer_correctness::FLOAT AS correctness,
           r.value:ATTRIBUTES:tool_selection_accuracy::FLOAT AS tool_selection,
           r.value:ATTRIBUTES:logical_consistency::FLOAT AS consistency,
           r.value:ATTRIBUTES:answer_correctness_explanation::STRING AS explanation
       FROM eval_results,
       LATERAL FLATTEN(input => PARSE_JSON(SPANS)) r
       WHERE r.value:NAME::STRING = 'eval_root'
   )
   SELECT * FROM scores;
   ```

   Present to user:
   ```
   Baseline Evaluation Results (Native):
   - Total Questions: 13
   - Answer Correctness: 31% (4/13)
   - Tool Selection Accuracy: 62%
   - Logical Consistency: 85%
   
   Failures:
   - Q3: correctness=0, explanation: "Agent returned gross revenue instead of net"
   - Q7: tool_selection=0, explanation: "Used search tool instead of analyst"
   ...
   
   View in Snowsight:
   https://app.snowflake.com/<ORG>/<ACCOUNT>/#/agents/.../evaluations/baseline_v1/records
   ```

**Continue to step 3 below.**

---

3. **Analyze each failure deeply:**
   For each failed question, determine:
   - What did the agent return?
   - What should it have returned?
   - Which tool did it call (if any)?
   - What tool type was used? (Check response JSON for `tool_use.type`)
   - Why did it fail?
   
   **⚠️ CRITICAL DECISION POINT:**
   If the failure involves a `cortex_analyst_text_to_sql` tool AND has SQL issues:
   - Check the generated SQL in the tool_result
   - If SQL is incorrect (wrong filters, missing columns, incorrect date logic):
     - STOP analyzing this failure at agent level
     - Mark for semantic view optimization
     - Continue analyzing other failures

4. **Discover failure patterns (don't use predefined categories):**
   Analyze the failures and group them by what actually went wrong.
   
   **Example analysis:**
   ```
   I've analyzed the 9 failures and found 4 distinct patterns:
   
   1. **Percentage vs. Absolute Values (3 failures: Q4, Q9, Q11)**
      - Questions asked for "percentage" or "proportion"
      - Agent returned absolute numbers instead of percentages
      - Example: Q4 asked "what percent of credits" but got "1.2M credits"
      - Root cause: Instructions don't specify to compute percentage
   
   2. **Wrong Tool Selection (2 failures: Q7, Q12)**
      - Agent routed to incorrect semantic model
      - Example: Q7 asked about "Streamlit Open Source" but used "Streamlit in Snowflake" tool
      - Example: Q12 asked about "ML platform" (specific product) but queried all AI/ML products
      - Root cause: No guidance on tool disambiguation or product scope definitions
   
   3. **Time Period Interpretation (2 failures: Q1, Q10)**
      - Agent misinterpreted relative time periods
      - Example: "first half of 2025" wasn't translated to Jan 1 - June 30
      - Root cause: No explicit date range definitions
   
   4. **Missing Data Validation (2 failures: Q5, Q13)**
      - Agent didn't check if date range covered full period
      - Returned partial data without warning
      - Root cause: No mandatory validation checks
   
   Would you like me to generate improvement suggestions for each pattern?
   ```
   
   **Note:** Tool routing issues are common failure patterns. Look for:
   - Agent using wrong semantic model/tool for the question
   - Agent not asking for clarification when multiple tools could apply
   - Agent not coordinating across multiple tools when needed
   - Agent confusing similar product names (e.g., "Streamlit in Snowflake" vs "Streamlit Open Source")

5. **Categorize failures by fix location:**

After discovering failure patterns, separate them into two categories:

**Category A: Agent-level fixes** (orchestration instructions)
- Tool routing issues (wrong tool selected)
- Response formatting issues
- Missing clarification questions
- Incorrect interpretation of user intent
- Multi-tool coordination issues

**Category B: Semantic view fixes** (YAML model)
- Incorrect SQL generation from Cortex Analyst
- Missing columns or tables in semantic view
- Wrong join relationships
- Incorrect filters or date logic in generated SQL
- VQR (Verified Query Repository) misleading the SQL generation

Present to user:
```
Failure Analysis:
- Total Failures: 9
- Agent-level fixes needed: 5 failures (Q2, Q5, Q8, Q11, Q13)
- Semantic view fixes needed: 4 failures (Q1, Q4, Q7, Q10)

For the 4 semantic view issues:
- Q1: Date interpretation ("last week" = calendar week vs rolling 7 days)
- Q4: Missing column for percentage calculation
- Q7: Wrong table joined in semantic view
- Q10: VQR pattern misleading SQL generation

Would you like to:
A) Fix agent-level issues first, then semantic views
B) Fix semantic views first, then agent-level issues  
C) Fix both in parallel (recommended if different people own them)
```
6. **Present findings to user:**
   - Show accuracy metrics
   - Explain each failure pattern with examples
   - Show categorization: Agent-level vs Semantic view fixes
   - Confirm your categorization makes sense
   - Ask which patterns to prioritize and whether to handle semantic view fixes now or later

**Deliverables:**
- Baseline accuracy measurement (e.g., 31%)
- Categorized failure analysis
- Failures separated into Agent-level vs Semantic view fixes
- Understanding of what needs to improve

---

### Phase 4: Instruction Improvements

**Goal:** Systematically improve orchestration instructions and/or semantic views based on failure patterns.

**What You Should Do:**

0. **Determine if semantic view optimization is needed:**

If Phase 3 identified semantic view failures (Category B):

**Option 1: Semantic views and agent owned by same team (or you have access)**

For each semantic view with failures:

1. Extract semantic view name from agent tool configuration:
   ```bash
   # Get agent config if not already extracted
   jq '.agent_spec' agent_config.json | jq '.tools[] | select(.type=="cortex_analyst_text_to_sql")'
   ```

2. **LOAD**: `semantic-view` skill in DEBUG mode

3. Provide to the semantic-view skill:
   - Semantic view name (e.g., `DATABASE.SCHEMA.SEMANTIC_VIEW_NAME`)
   - Failing question(s) from evaluation
   - Expected behavior vs actual SQL generated

4. Follow semantic-view DEBUG workflow:
   - Download semantic view YAML
   - Generate and analyze SQL with Cortex Analyst
   - Identify root cause (missing columns, wrong relationships, bad VQRs, etc.)
   - Apply targeted fixes to semantic view YAML
   - Validate with SQL comparison

5. Re-run evaluation on semantic view questions to confirm fixes:
   ```bash
   # Test just the semantic view fixes
   uv run python ../scripts/run_evaluation.py \
       --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
       --eval-source "SELECT * FROM eval_table WHERE question_id IN (1, 4, 7, 10)" \
       --output-dir "$VER_DIR/evals/eval_semantic_view_retry" \
       --connection CONNECTION_NAME
   ```

6. Update `optimization_log.md` with semantic view changes

**Option 2: Semantic views owned by different team**

Create handoff document:
```markdown
# Semantic View Fixes Needed for [AGENT_NAME]

## Semantic View: DATABASE.SCHEMA.SEMANTIC_VIEW_1

### Question 1 (Q1): "How many users in the last week?"
- **Current SQL:**
  ```sql
  WHERE ds >= DATE_TRUNC('WEEK', CURRENT_DATE - INTERVAL '1 WEEK')
  ```
- **Expected SQL:**
  ```sql  
  WHERE ds >= CURRENT_DATE - INTERVAL '7 DAYS'
  ```
- **Root Cause:** "last week" interpreted as previous calendar week, not last 7 days
- **Fix:** Update VQR or custom instructions for date interpretation

[Repeat for each semantic view issue]
```

Pause optimization until semantic view fixes are deployed, then resume with re-evaluation.

**Then proceed to Step 1** for agent-level fixes.

1. **For each AGENT-LEVEL failure pattern, draft instruction improvements:**

   **Example for "Percentage Calculation" pattern:**
   ```
   For the "Percentage vs. Absolute Values" pattern affecting Q4, Q9, and Q11,
   I suggest adding this section to orchestration instructions:
   
   ---
   ## Proportion/Percentage Calculations
   
   When calculating "proportion of X spent on Y" or "percentage":
   
   **For "what percent" questions:**
   - Return the percentage value as primary answer
   - Include context: "67.4% (1.2M out of 1.8M total credits)"
   
   **For "highest proportion" questions:**
   - Query both numerator and denominator separately
   - Calculate: (numerator / NULLIF(denominator, 0)) * 100
   - Sort by percentage DESC, not absolute values
   - Return top results: "1. Acme: 89.3% (500K/560K), 2. Beta: 76.2%"
   
   **Validation:**
   - Verify denominator is non-zero
   - If percentage >100%, re-examine query (numerator shouldn't exceed denominator)
   ---
   
   This would handle both "what percent" and "highest proportion" question types.
   Would this fix the failures? Any adjustments needed?
   ```
   
   **Example for "Tool Routing" pattern:**
   ```
   For the "Wrong Tool Selection" pattern affecting Q7 and Q12,
   I suggest adding this section to orchestration instructions:
   
   ---
   ## Tool Selection and Routing
   
   Before answering a question, identify which semantic model/tool has the required data.
   
   **Product disambiguation:**
   - "Streamlit in Snowflake" vs "Streamlit Open Source" are DIFFERENT products
   - "ML Platform" or "Snowflake ML" refers to specific product, NOT all AI/ML
   - "AI/ML" includes: Cortex ML, Cortex LLM, Snowflake ML, ML Packages, Copilot
   - "Notebooks" is separate from AI/ML categories
   
   **Tool selection rules:**
   - For product-specific questions → use product_categories or product-specific tool
   - For geographic breakdowns → use product_geo tool
   - For feature usage (SIS, Notebooks execution) → use feature_usage tool
   - For organizational metadata → use product_owners tool
   
   **When multiple tools could apply:**
   - Ask for clarification: "To answer accurately, I need to know: [specific question]"
   - Example: "For 'ML usage', do you mean Snowflake ML specifically or all AI/ML products?"
   
   **Tool coordination:**
   - Some questions require querying multiple tools
   - Example: "Compare Notebooks vs Streamlit" needs product_categories AND feature_usage tools
   - Query each tool separately, then combine results in your answer
   ---
   
   This adds explicit tool routing rules based on product types and question patterns.
   Would this prevent the Q7 and Q12 routing failures?
   ```

2. **Iterate with user on each improvement:**
   - Present draft instruction section
   - Explain reasoning and what it fixes
   - Ask for refinement or approval
   - Show how it would handle the failed question
   - Adjust based on feedback

3. **Create complete updated instructions:**
   - Combine original instructions with all improvements
   - Organize logically (critical rules first)
   - Show before/after comparison
   - Present to user for review

4. **Create new version folder and save updated instructions:**
   ```bash
   # Create new version for this update
   VERSION="v$(date +%Y%m%d-%H%M)"
   VER_DIR="$WORKSPACE_DIR/versions/$VERSION"
   mkdir -p "$VER_DIR/evals"
   
   # Save updated instructions to version folder
   # (copy from previous version and edit, or create new)
   cp "$PREVIOUS_VER_DIR/instructions_orchestration.txt" "$VER_DIR/instructions_orchestration.txt"
   # Then edit the file with improvements
   ```

5. **Update the agent:**
   ```bash
   uv run python ../scripts/create_or_alter_agent.py alter \
       --agent-name AGENT_NAME \
       --instructions "$VER_DIR/instructions_orchestration.txt" \
       --database DATABASE --schema SCHEMA --connection CONNECTION_NAME
   ```

6. **Re-evaluate (use same method as Phase 3):**

   **⚠️ REMINDER: Use the SAME evaluation method you used in Phase 3. Do not switch methods.**

   **Option A: Script-based:**
   ```bash
   uv run python ../scripts/run_evaluation.py \
       --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
       --eval-source database.schema.eval_table \
       --output-dir "$VER_DIR/evals/eval_after_update" \
       --connection CONNECTION_NAME
   ```
   
   **Option B: Native Snowflake:**
   ```sql
   CALL SYSTEM$EXECUTE_AI_OBSERVABILITY_RUN(
       OBJECT_CONSTRUCT('object_name', '<DB>.<SCHEMA>.<AGENT>', 'object_type', 'CORTEX AGENT', 'object_version', ''),
       OBJECT_CONSTRUCT('run_name', 'after_improvements_v1', 'label', 'improved', 'description', 'After instruction improvements'),
       OBJECT_CONSTRUCT('type', 'dataset', 'dataset_name', '<AGENT_NAME>_baseline_dataset', 'dataset_version', 'SYSTEM_AI_OBS_CORTEX_AGENT_DATASET_VERSION_DO_NOT_DELETE'),
       ARRAY_CONSTRUCT('answer_correctness', 'tool_selection_accuracy', 'logical_consistency'),
       ARRAY_CONSTRUCT('INGESTION', 'COMPUTE_METRICS')
   );
   ```
   
   **If using Native Snowflake evaluation:** Wait for results before proceeding. Poll `GET_AI_OBSERVABILITY_EVENTS` until you see results for your run_name. Do NOT fall back to script-based evaluation while waiting.
   
   Then query results and compare to baseline (see `evaluate-cortex-agent` skill for comparison queries).
   
   If semantic view fixes were applied, also validate those separately:
   ```bash
   # Re-evaluate just the semantic view questions to confirm those fixes
   uv run python ../scripts/run_evaluation.py \
       --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
       --eval-source "SELECT * FROM eval_table WHERE question_id IN (1, 4, 7, 10)" \
       --output-dir "$VER_DIR/evals/eval_semantic_view_validation" \
       --connection CONNECTION_NAME
   ```
   
   **Tip:** If you only want to re-test questions that previously failed:
   ```bash
   # Create a view or query with just the failed questions
   uv run python ../scripts/run_evaluation.py \
       --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
       --eval-source "SELECT * FROM eval_table WHERE question_id IN (2, 8, 13)" \
       --output-dir "$VER_DIR/evals/eval_failed_retry" \
       --connection CONNECTION_NAME
   ```

7. **Compare results:**
   ```
   Evaluation Comparison:
   
   Baseline:      4/13 (31%)
   After Update: 10/13 (77%)
   
   Improvements: Q1, Q4, Q5, Q7, Q9, Q10 (6 fixes)
   - Agent instruction fixes: Q5, Q9 (2 fixes)
   - Semantic view fixes: Q1, Q4, Q7, Q10 (4 fixes)
   
   Regressions: None
   Still Failing: Q2, Q8, Q13
   
   That's a +46 percentage point improvement! 
   
   Let me analyze the remaining failures...
   ```

7. **If accuracy is insufficient (<70%), iterate:**
   - Analyze remaining failures
   - Draft additional improvements
   - Update and re-evaluate
   - Continue until acceptable accuracy achieved

**Deliverables:**
- Updated orchestration instructions (for agent-level fixes)
- Updated semantic view YAMLs (for semantic view fixes, if applicable)
- Improved accuracy (target: >70%)
- Comparison showing improvements, distinguishing agent vs semantic view fixes
- Any regressions identified

---

### Phase 5: Overfitting Detection

**Goal:** Identify instruction patterns that are too specific to evaluation questions.

**What You Should Do:**

1. **Analyze instructions for evaluation-specific patterns:**
   
   Read through the updated instructions carefully and reason about:
   - Specific years, dates, or time periods that came from eval questions
   - Specific company/account names used as examples
   - Hardcoded numeric thresholds that only work for eval data scale
   - Fixed result counts (e.g., "show top 10") without context
   - Absolute value ranges specific to eval data
   - Any other patterns that seem too specific

2. **For each issue found, explain the problem:**
   
   **Example analysis:**
   ```
   I found 4 critical overfitting issues:
   
   1. **Line 107: "First half of 2025" = Jan 1 - June 30, 2025**
      
      Why problematic: This hard-codes year 2025 from your evaluation questions.
      
      Production risk: In 2026, if a user asks "first half", the agent won't 
      know it means Jan-Jun 2026. The instruction is year-specific.
      
      Generalization needed: Define "first half" as Jan 1 - June 30 of 
      *specified year*, not a fixed 2025 date.
   
   2. **Line 117: "AMD might match AMDOCS, AMD Holdings, etc."**
      
      Why problematic: "AMD" is a specific company name from Q7 in your eval set.
      
      Production risk: Users might search for other short names (IBM, HP, SAP, 
      GE) and won't have this warning. The pattern is about *short names in 
      general*, not specifically AMD.
      
      Generalization needed: Explain that short names may match unrelated 
      companies, give AMD as ONE example among others.
   
   3. **Line 145: "Daily credits typically: SIS (10-1000), Total (10K-1M+)"**
      
      Why problematic: These absolute ranges came from your evaluation data scale.
      
      Production risk: A very large enterprise customer might have 10M daily 
      credits (10x the range), or a small trial account might have 5 credits. 
      The ranges don't adapt to different customer sizes.
      
      Generalization needed: Use relative comparisons (e.g., "SIS credits are 
      typically 100-1000x smaller than total Snowflake credits") instead of 
      absolute ranges.
   
   4. **Line 122: "Filter out accounts with <1000 total credits"**
      
      Why problematic: The 1000 threshold came from your eval data distribution.
      
      Production risk: For different question types or data scales, 1000 might 
      filter out important results or not filter enough noise.
      
      Generalization needed: Make filtering context-dependent based on question 
      type and data scale.
   
   I also noticed Line 124 says "Show top 10-20 results" - this should vary 
   based on whether the question asks for "which account has highest X" (show 
   3-5) vs "accounts with high X" (show 10-20).
   
   Should we generalize these patterns?
   ```

3. **Prioritize issues:**
   - Critical: Will definitely cause production failures
   - Medium: Might cause issues in some scenarios
   - Low: Minor improvements

4. **Present analysis to user:**
   - Show each overfitting issue with reasoning
   - Explain production risks
   - Ask user to validate your analysis
   - Confirm which issues to fix

**Deliverables:**
- Overfitting analysis identifying eval-specific patterns
- Prioritized list of generalizations needed
- User confirmation on issues to address

---

### Phase 6: Generalization & Validation

**Goal:** Create production-ready instructions that work beyond evaluation cases.

**What You Should Do:**

1. **For each overfitting issue, create generalized version:**
   
   **Example generalization:**
   ```
   Issue #1: Time Period Definitions
   
   BEFORE (lines 107-109):
   ├─ "First half of 2025" = Jan 1 - June 30, 2025
   ├─ "Last couple of months ending mid-October" = Aug 1 - Oct 15
   └─ Always specify exact date ranges in your tool queries
   
   AFTER:
   **For time-based questions:**
   ├─ Standard period definitions:
      - "First half" or "H1" = January 1 - June 30 of specified year
      - "Second half" or "H2" = July 1 - December 31 of specified year
      - "Q1" = Jan-Mar, "Q2" = Apr-Jun, "Q3" = Jul-Sep, "Q4" = Oct-Dec
      - "Last/past [N] months" = N months before reference date
      - "Last/past [N] days/weeks" = N days/weeks before reference date
   ├─ Interpret relative terms based on context and current date
   ├─ When time period is ambiguous, ask for clarification on exact date range
   └─ Always specify exact date ranges in your tool queries
   
   What this fixes:
   - Works for any year (not just 2025)
   - Handles all standard period types (Q1-Q4, H1-H2)  
   - Supports relative time references
   - Covers edge case: ambiguous periods
   
   Your eval question "first half of 2025" still works correctly, but now 
   so do these production variations:
   - "first half of 2026"
   - "H1 2024"
   - "Q3 of last year"
   - "past 3 months"
   ```

2. **Show complete generalized instructions:**
   - Present full updated instruction file
   - Highlight all changes from previous version
   - Explain how each change improves generalization
   - Get user approval

3. **Create new version folder and save generalized instructions:**
   ```bash
   # Create new version for generalization
   VERSION="v$(date +%Y%m%d-%H%M)"
   VER_DIR="$WORKSPACE_DIR/versions/$VERSION"
   mkdir -p "$VER_DIR/evals"
   
   # Save generalized instructions to version folder
   # (copy from previous version and edit, or create new)
   cp "$PREVIOUS_VER_DIR/instructions_orchestration.txt" "$VER_DIR/instructions_orchestration.txt"
   # Then edit the file with generalizations
   ```

4. **Update agent with generalized instructions:**
   ```bash
   uv run python ../scripts/create_or_alter_agent.py alter \
       --agent-name AGENT_NAME \
       --instructions "$VER_DIR/instructions_orchestration.txt" \
       --database DATABASE --schema SCHEMA --connection CONNECTION_NAME
   ```

5. **Run final evaluation (use same method as Phase 3):**

   **⚠️ REMINDER: Use the SAME evaluation method you used throughout this optimization. Do not switch methods.**

   **Option A: Script-based:**
   ```bash
   uv run python ../scripts/run_evaluation.py \
       --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
       --eval-source database.schema.eval_table \
       --output-dir "$VER_DIR/evals/eval_generalized" \
       --connection CONNECTION_NAME
   ```
   
   **Option B: Native Snowflake:**
   ```sql
   CALL SYSTEM$EXECUTE_AI_OBSERVABILITY_RUN(
       OBJECT_CONSTRUCT('object_name', '<DB>.<SCHEMA>.<AGENT>', 'object_type', 'CORTEX AGENT', 'object_version', ''),
       OBJECT_CONSTRUCT('run_name', 'generalized_v1', 'label', 'production-ready', 'description', 'After generalization - production ready'),
       OBJECT_CONSTRUCT('type', 'dataset', 'dataset_name', '<AGENT_NAME>_baseline_dataset', 'dataset_version', 'SYSTEM_AI_OBS_CORTEX_AGENT_DATASET_VERSION_DO_NOT_DELETE'),
       ARRAY_CONSTRUCT('answer_correctness', 'tool_selection_accuracy', 'logical_consistency'),
       ARRAY_CONSTRUCT('INGESTION', 'COMPUTE_METRICS')
   );
   ```
   
   **If using Native Snowflake evaluation:** Wait for results before proceeding. Poll `GET_AI_OBSERVABILITY_EVENTS` until you see results for your run_name. Do NOT fall back to script-based evaluation while waiting.
   
   Query results and perform three-way comparison (baseline → improved → generalized).
   
   **Tip:** For comprehensive validation, you can test with different data subsets:
   ```bash
   # Full evaluation set
   uv run python ../scripts/run_evaluation.py --agent-name AGENT_NAME --database DB --schema SCHEMA --eval-source eval_table --output-dir "$VER_DIR/evals/eval_full" --connection CONNECTION_NAME
   
   # Edge cases only
   uv run python ../scripts/run_evaluation.py --agent-name AGENT_NAME --database DB --schema SCHEMA \
       --eval-source "SELECT * FROM eval_table WHERE category = 'edge_case'" --output-dir "$VER_DIR/evals/eval_edge" --connection CONNECTION_NAME
   
   # Production-like queries (if you have them)
   uv run python ../scripts/run_evaluation.py --agent-name AGENT_NAME --database DB --schema SCHEMA \
       --eval-source "SELECT * FROM production_queries LIMIT 20" --output-dir "$VER_DIR/evals/eval_production_sample" --connection CONNECTION_NAME
   ```

6. **Three-way comparison:**
   ```
   Optimization Journey:
   
   Baseline:        4/13 (31%)    4,067 characters
   Updated:        10/13 (77%)   12,637 characters (+210%)
   Generalized:    13/13 (100%)  14,420 characters (+14% vs updated)
   
   Question-by-Question:
   Q#  Baseline  Updated  Generalized  Journey
   Q1     ✗        ✓          ✓        Fixed in update, maintained
   Q2     ✗        ✗          ✓        Fixed in generalization
   Q3     ✗        ✓          ✓        Fixed in update, maintained
   Q4     ✗        ✓          ✓        Fixed in update, maintained
   ...
   
   Total Improvement: +9 questions (+69 percentage points)
   No regressions throughout optimization process
   
   The generalized version maintains perfect eval accuracy while adding 
   broader guidance for production scenarios.
   ```

6. **Create deployment summary:**
   ```
   # Deployment Summary: [AGENT_NAME]
   
   ## Accuracy Improvement
   - Baseline: 31% (4/13)
   - Final: 100% (13/13)
   - Improvement: +69 percentage points
   
   ## Key Changes Made
   1. Added metric disambiguation rules (tool selection)
   2. Added data quality validation requirements
   3. Added calculation patterns (percentages, aggregations)
   4. Generalized time period handling (not just 2025)
   5. Generalized account matching patterns (not just AMD)
   6. Converted absolute ranges to relative comparisons
   7. Made filtering context-dependent (not fixed thresholds)
   
   ## Instruction Size
   - Baseline: 4,067 chars
   - Final: 14,420 chars (+255%)
   
   ## Production Readiness
   ✅ 100% evaluation accuracy
   ✅ No critical overfitting issues
   ✅ Generalized to handle production variations
   ✅ Domain expert approved
   
   ## Monitoring Recommendations
   - Collect production failures for next iteration
   - Track accuracy on real user queries
   - Update evaluation set with production edge cases
   - Re-evaluate quarterly as data/tools change
   ```

**Deliverables:**
- Production-ready agent with generalized instructions
- 100% (or near-100%) evaluation accuracy
- Deployment summary documenting journey
- No critical overfitting issues remaining

---

## Best Practices for AI Assistants

### Using run_evaluation.py Effectively

The `run_evaluation.py` script is flexible and supports many use cases beyond basic table evaluation:

**Filtering Strategies:**
```bash
# By category
"SELECT * FROM eval_table WHERE category IN ('finance', 'sales')"

# By difficulty
"SELECT * FROM eval_table WHERE difficulty = 'hard'"

# By date added (recent questions only)
"SELECT * FROM eval_table WHERE date_added >= '2025-01-01'"

# By specific questions
"SELECT * FROM eval_table WHERE question_id IN (3, 7, 11, 15)"

# By tool coverage
"SELECT * FROM eval_table WHERE tool_used = 'Product_Categories'"

# Test routing for each semantic model
"SELECT * FROM eval_table WHERE category = 'tool_routing'"

# Random sample for quick validation
"SELECT * FROM eval_table ORDER BY RANDOM() LIMIT 10"
```

**Progressive Testing Approach:**
1. Start with small subset (5-10 questions) to validate agent works
2. Run full evaluation once agent shows promise
3. Re-test only failed questions after improvements
4. Run final comprehensive evaluation before deployment

**Performance Optimization:**
- For >20 questions, consider batching by category or tool
- Use LIMIT during development/debugging
- Run full evaluation only when needed (baseline, after major changes, final)
- Filter to failed questions for faster iteration

**Example workflow (using versioned structure):**
```bash
# Set version directory for this phase
VER_DIR="$WORKSPACE_DIR/versions/v$(date +%Y%m%d-%H%M)"

# 1. Quick smoke test (5 questions)
uv run python ../scripts/run_evaluation.py --agent-name AGENT --database DB --schema SCHEMA \
    --eval-source "SELECT * FROM eval_table LIMIT 5" --output-dir "$VER_DIR/evals/eval_smoke" --connection CONNECTION_NAME

# 2. If smoke test passes, run full baseline
uv run python ../scripts/run_evaluation.py --agent-name AGENT --database DB --schema SCHEMA \
    --eval-source eval_table --output-dir "$VER_DIR/evals/eval_baseline" --connection CONNECTION_NAME

# 3. After improvements, re-test only failures (in new version folder)
NEW_VER_DIR="$WORKSPACE_DIR/versions/v$(date +%Y%m%d-%H%M)"
uv run python ../scripts/run_evaluation.py --agent-name AGENT --database DB --schema SCHEMA \
    --eval-source "SELECT * FROM eval_table WHERE question_id IN (3, 6, 10)" \
    --output-dir "$NEW_VER_DIR/evals/eval_retry" --connection CONNECTION_NAME

# 4. Final validation with full set
uv run python ../scripts/run_evaluation.py --agent-name AGENT --database DB --schema SCHEMA \
    --eval-source eval_table --output-dir "$NEW_VER_DIR/evals/eval_final" --connection CONNECTION_NAME
```

### Analyzing Failures

**❌ Don't:** Use predefined failure categories
```
"This is a tool selection error" [forcing into predetermined bucket]
```

**✅ Do:** Discover actual patterns
```
"Looking at these 3 failures, they all asked for percentages but got absolute 
numbers. The common issue is the agent isn't computing the division. This is 
a calculation pattern issue, not covered by current instructions."

"Q7 and Q12 both routed to the wrong semantic model. Q7 used 'Streamlit in 
Snowflake' tool when the question asked about 'Streamlit Open Source'. Q12 
queried all AI/ML products when the question specifically asked for 'ML Platform' 
only. This is a tool routing and product disambiguation issue."
```

### Generating Improvements

**❌ Don't:** Provide generic template instructions
```
"Add: When user asks for X, do Y"
```

**✅ Do:** Create specific, actionable instructions
```
"Add this section:

## Proportion/Percentage Calculations

**For 'what percent' questions:**
- Calculate: (numerator / NULLIF(denominator, 0)) * 100
- Return: '67.4% (1.2M out of 1.8M total credits)'

**For 'highest proportion' questions:**
- Sort by percentage DESC (not absolute values)
- Return top N with percentages and raw numbers

This handles Q4 (what percent of credits...) and Q9 (highest proportion of spend...)"
```

### Detecting Overfitting

**❌ Don't:** Just pattern-match for years/names
```
"Found '2025' in instructions - that's overfitting"
```

**✅ Do:** Reason about production impact
```
"Line 107 says 'First half of 2025' = Jan 1 - June 30, 2025. 

This is problematic because in production:
- Users will ask about 2026, 2027, etc.
- The instruction only defines 2025 specifically
- Next year, 'first half' won't be interpreted correctly

We should generalize to: 'First half' = Jan 1 - June 30 of *specified year*"
```

### Communicating with User

**Be specific about what you're doing:**
```
✅ "I'm going to query Snowflake for all agents in TEMP.NVYTLA schema"
✅ "Let me analyze Q4 - it asked for percentage but got absolute number"
✅ "I found 3 questions with the same pattern - percentage calculation issues"
```

**Ask for validation at key decision points:**
```
✅ "Does this failure categorization make sense to you?"
✅ "Would this instruction fix the issue?"
✅ "Should we prioritize fixing percentages or account matching first?"
```

**Show your reasoning:**
```
✅ "This pattern is overfit because [explanation + production risk]"
✅ "I categorized these together because [common root cause]"
✅ "This generalization handles [list of scenarios]"
```

---

## Measuring Success

Track these metrics throughout optimization:

| Metric | Baseline | Target | How to Measure |
|--------|----------|--------|----------------|
| **Accuracy** | Measure first | >80% | Evaluation results |
| **Instruction Size** | Measure first | <20KB | Character count |
| **Overfitting Issues** | N/A | 0 critical | Your analysis |
| **Regressions** | 0 | 0 | Evaluation comparison |

**Success Criteria:**
- ✅ >80% accuracy on evaluation set
- ✅ Zero critical overfitting issues
- ✅ Zero regressions from baseline to final
- ✅ Domain expert approval for production deployment

---

## Common Pitfalls to Avoid

### 1. Accepting First Draft
```
❌ User approves first improvement suggestion → immediately update agent
✅ User approves → iterate on wording → show how it handles failed question → then update
```

### 2. Writing Eval-Specific Instructions
```
❌ "For 'first half of 2025' questions, use Jan 1 - June 30, 2025"
✅ Catch this yourself: "Wait, this is too specific to 2025. Let me generalize..."
```

### 3. Forcing Predefined Categories
```
❌ "Categorizing into: Tool Selection, Metric Confusion, Calculation, Data Quality"
✅ "Analyzing patterns... I see 3 distinct issues: percentage calculations, 
    account pattern matching, and time period interpretation"
```

### 4. Skipping Overfitting Check
```
❌ 77% accuracy → "Great improvement! Ready for production"
✅ 77% accuracy → "Good improvement! Let me check for overfitting before we deploy..."
```

### 5. Not Explaining Reasoning
```
❌ "This is overfit" [no explanation]
✅ "This is overfit because it hard-codes 2025. In production, users will ask 
    about other years and the agent won't know how to handle them."
```

---

## Example: Full Phase 4 Interaction

Here's what a complete Phase 4 conversation looks like:

```
You: Let me analyze the failures from baseline evaluation.

I found 3 distinct patterns:

1. Percentage Calculation Issues (Q4, Q9, Q11)
2. Account Name Ambiguity (Q7, Q12)  
3. Time Period Misinterpretation (Q1, Q10)

Let's start with #1. All three questions asked for percentages or proportions,
but the agent returned absolute numbers instead.

Looking at Q4: "what percent of snowflake credits were used by accounts with 
Databricks usage?"

Expected: "67.42%" 
Actual: "1.2M credits"

The agent queried the right data but didn't compute the percentage.

I suggest adding this section to orchestration instructions:

---
## Proportion/Percentage Calculations

When calculating "proportion of X spent on Y" or "percentage":

**For "what percent" questions:**
- Query both numerator and denominator
- Calculate: (numerator / NULLIF(denominator, 0)) * 100
- Return: "67.4% (1.2M out of 1.8M total credits)"

**For "highest proportion" questions:**
- Sort by percentage DESC, not absolute values
- Return top entities: "1. Acme: 89.3% (500K/560K), 2. Beta: 76.2%"

**Validation:**
- If percentage >100%, re-examine query
---

Does this make sense? Any adjustments needed?

User: Yes, but what if denominator is zero?

You: Good catch! The NULLIF handles division by zero, but we should also explain
what to do if that happens. Let me add:

- If denominator is zero, return "Cannot calculate percentage (no baseline data)"

Should I also add a sanity check for very small denominators?

User: Yes, warn if denominator seems unusually low.

You: I'll add:

- If denominator <1000 credits, note: "Warning: Small baseline (only X credits)"

Here's the updated version: [shows complete section]

Does this fully address the percentage calculation failures?

User: Perfect. What about pattern #2?

You: For the account name ambiguity pattern, Q7 asked about "AMD" but the agent
returned results for "AMDOCS" because it used pattern matching...

[continues through all patterns]
```

---

## Output Files Reference

Throughout optimization, following the `agent-system-of-record` protocol, you'll create these files:

```
<WORKSPACE_DIR>/
├── optimization_log.md                         # Running log (update continuously)
├── versions/
│   ├── vYYYYMMDD-HHMM-baseline/                # Baseline version (Phase 1-3)
│   │   ├── agent_config.json                   # Original config
│   │   ├── instructions_orchestration.txt     # Original instructions
│   │   ├── tools_summary.txt                   # Tool inventory
│   │   └── evals/
│   │       └── eval_baseline/
│   │           ├── q01_response.json ... q13_response.json
│   │           ├── evaluation_summary.json
│   │           └── analysis_notes.txt          # Your analysis
│   │
│   ├── vYYYYMMDD-HHMM-updated/                 # Updated version (Phase 4)
│   │   ├── instructions_orchestration.txt     # Updated instructions
│   │   ├── change_manifest.md                 # What changed
│   │   └── evals/
│   │       ├── eval_after_update/
│   │       │   ├── q01_response.json ... q13_response.json
│   │       │   ├── evaluation_summary.json
│   │       │   └── comparison_vs_baseline.txt
│   │       └── eval_failed_retry/              # Optional: retry failed questions
│   │
│   └── vYYYYMMDD-HHMM-generalized/             # Generalized version (Phase 6)
│       ├── instructions_orchestration.txt     # Generalized instructions
│       ├── change_manifest.md                 # Generalization changes
│       └── evals/
│           ├── eval_generalized/
│           │   ├── q01_response.json ... q13_response.json
│           │   ├── evaluation_summary.json
│           │   └── three_way_comparison.txt  # Baseline → Updated → Generalized
│           ├── eval_full/                      # Optional: full validation
│           ├── eval_edge/                      # Optional: edge cases only
│           └── eval_production_sample/         # Optional: production queries
│
└── DEPLOYMENT_SUMMARY.md                       # Final summary (optional, at workspace root)
```

---

## When to Escalate to User

Ask user for input when:
- **Ambiguous requirements:** "Should we prioritize accuracy or speed?"
- **Domain knowledge needed:** "What should the expected answer be for this question?"
- **Trade-off decisions:** "This instruction improves Q4 but might affect Q7. Which is more important?"
- **Validation needed:** "Does this failure categorization make sense?"
- **Approval required:** "Ready to update the agent with these changes?"

Don't ask user for:
- **Technical execution:** Just run the scripts
- **Obvious issues:** "I found an overfitting issue" (explain it, don't ask if it's an issue)
- **Analysis:** Do the analysis yourself, then present findings

---

This workflow is designed for AI assistants to guide humans through agent optimization using reasoning and collaboration, not rigid automation. Adapt as needed for your specific agent.

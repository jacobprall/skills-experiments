---
name: adhoc-testing-for-cortex-agent
description: Interactive testing of Cortex Agents. Use this when you want to test specific questions, debug responses, and explore agent behavior through hands-on exploration. For persisting results to formal evaluation datasets, use the dataset-curation skill.
---

# Adhoc Testing for Cortex Agent

## Purpose

Interactively test Cortex Agents by running questions, reviewing responses, and debugging issues. This is the exploration and discovery workflow - test first, decide what to keep later.

## When to Use

- **Exploring agent behavior** with new or unexpected questions
- **Validating fixes** after instruction updates
- **Debugging specific failures** from production or user feedback
- **Quick testing** before formal evaluation

**For building formal evaluation datasets:** Use `dataset-curation` skill after testing.

## Prerequisites

**Snowflake Access:**
- Connection to Snowflake with Cortex Agent access
- Agent already created and deployed

**Essential Scripts:**
- `../scripts/test_agent.py` - Run individual questions

## The Workflow

### Step 1: Setup Testing Environment

**Goal:** Prepare agent for testing.

1. **Identify or clone the agent to test:**
   
   If testing production agent, create a working copy:
   
   ⚠️ **Ask the user:** "What fully qualified name would you like for the clone? (e.g., `DATABASE.SCHEMA.CLONE_NAME`)"
   
   ```bash
   uv run python ../scripts/get_agent_config.py \
       --agent-name AGENT_NAME --database DATABASE --schema SCHEMA \
       --connection CONNECTION_NAME --output agent_config.json
   
   uv run python ../scripts/create_or_alter_agent.py create \
       --agent-name CLONE_AGENT_NAME --config-file agent_config.json \
       --database CLONE_DATABASE --schema CLONE_SCHEMA --connection CONNECTION_NAME
   ```

2. **Create test output directory:**
   ```bash
   mkdir -p test_results_AGENT_NAME
   ```

**Deliverables:**
- Working copy of agent (optional)
- Test output directory

---

### Step 2: Run Questions Interactively

**Goal:** Test agent with real questions and observe behavior.

**Interactive Testing Loop:**

1. **User provides a question** (or you propose one based on agent capabilities)

2. **Run the question against agent:**
   ```bash
   uv run python ../scripts/test_agent.py \
       AGENT_NAME "Your question here?" \
       test_results_AGENT_NAME/test_01.json \
       DATABASE SCHEMA CONNECTION_NAME
   ```

3. **Review agent response together:**
   - Read the full response output
   - Discuss: "Is this correct?"
   - Discuss: "What should the correct answer be?"
   - Identify issues if any

4. **Decide what to do:**
   - ✅ **Correct** → Note for evaluation dataset
   - ❌ **Incorrect** → Debug further
   - 🤔 **Unclear** → Ask clarifying questions, refine, re-test

**Example Interaction:**
```
User: "Can you ask what is the usage of Cortex LLM functions in AMD in 2024?"

You: [Runs test_agent.py]
     "The agent returned 18.01 credits with 15 different functions. Is this correct?"

User: "I'm not sure. Can you debug this?"

You: [Runs stability test, analyzes SQL, discovers pattern matching issue]
     "The agent matched '%AMD%' which returned Amdocs companies, not AMD 
      semiconductor. The correct answer is zero usage."

User: "Good catch. Let's note this as a failure case."
```

---

### Step 3: Debug Questionable Responses

**Goal:** Deeply analyze responses that seem incorrect or suspicious.

**Quick Debugging Approach:**

1. **Test stability** - Run question twice to check for non-deterministic behavior
   ```bash
   uv run python ../scripts/test_agent.py AGENT "question" response1.json DB SCHEMA CONN
   uv run python ../scripts/test_agent.py AGENT "question" response2.json DB SCHEMA CONN
   ```

2. **Analyze tool calls** - Check which tools were called
   ```bash
   cat response1.json | jq '.content[] | select(.type == "tool_use") | .tool_use.name'
   ```

3. **Examine SQL** - Review generated SQL for logic errors
   ```bash
   cat response1.json | jq -r '.content[] | select(.type == "tool_result") | .tool_result.content[0].json.sql'
   ```

4. **Verify correctness** - Run your own SQL to confirm expected answer

**Common Issues to Check:**
- **Pattern matching too broad** (e.g., `ILIKE '%AMD%'` matching unrelated companies)
- **Wrong tool selection** (routed to incorrect semantic model)
- **Date/time interpretation errors** (wrong period boundaries)
- **Missing data validation** (partial data without warnings)

**For detailed debugging:** LOAD `debug-single-query-for-cortex-agent` skill

---

### Step 4: Track Tested Questions

**Goal:** Keep notes on what you've tested for later dataset creation.

As you test, maintain a simple tracking list:

```
Questions Tested:
1. "What is streamlit usage in March 2025?" - PASS - 70,627 executions
2. "What is AMD usage in 2024?" - FAIL - Pattern matching error (Amdocs)
3. "Compare notebooks vs streamlit" - PASS - Correct comparison
4. "Show me ML usage" - UNCLEAR - Agent didn't ask for clarification
```

**When ready to create formal evaluation dataset:**

LOAD `dataset-curation` skill to:
- Convert test results to proper evaluation format
- Create dataset for script-based evaluation (`run_evaluation.py`)
- Create dataset for native Snowflake evaluations (`SYSTEM$EXECUTE_AI_OBSERVABILITY_RUN`)

---

### Step 5: Review Coverage

**Goal:** Ensure testing covers diverse agent capabilities.

**Periodically review:**

1. **Tools tested:**
   ```
   - revenue_tool: 2 questions
   - usage_tool: 3 questions  
   - ml_platform_tool: 0 questions ← GAP
   ```

2. **Question types tested:**
   ```
   - Basic queries: 3
   - Tool routing: 1
   - Edge cases: 0 ← GAP
   ```

3. **Propose questions to fill gaps:**
   ```
   To improve coverage, I suggest testing:
   - "How many ML models were trained?" (ml_platform_tool)
   - "What was revenue on Feb 30?" (edge case - invalid date)
   ```

---

## Integration with Other Skills

**Testing → Dataset Creation → Evaluation → Optimization**

```
adhoc-testing (this skill)
    ↓
Explore agent, find issues, note results
    ↓
dataset-curation skill
    ↓
Create formal evaluation dataset
    ↓
evaluate-cortex-agent skill (native) OR run_evaluation.py (script)
    ↓
Get metrics, identify patterns
    ↓
optimize-cortex-agent skill
    ↓
Improve instructions, re-evaluate
```

This skill is the **discovery phase**. Use it to understand agent behavior before formalizing into evaluation datasets.

---

## Best Practices

### For AI Assistants

**Do:**
- ✅ Run test_agent.py for every new question
- ✅ Show full agent response to user before deciding
- ✅ Ask "Is this correct?" rather than assuming
- ✅ Debug thoroughly when answers seem suspicious
- ✅ Track what you've tested for later dataset creation

**Don't:**
- ❌ Assume agent is correct without user confirmation
- ❌ Skip debugging when answers look questionable
- ❌ Forget to track tested questions

### For Users

**Do:**
- ✅ Test questions you actually care about
- ✅ Say "I'm not sure" when you don't know the correct answer
- ✅ Ask for debugging when responses seem off
- ✅ Think about edge cases and failure scenarios

**Don't:**
- ❌ Rush through testing without reviewing responses
- ❌ Skip questions that might expose agent weaknesses

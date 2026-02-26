---
name: edit-cortex-agent
description: "Edit an existing Cortex Agent's configuration (instructions, tools, comment, models, etc.) using REST API. Use for: edit agent, modify agent, update agent, change agent instructions, add tools to agent, remove tools from agent."
---

# Edit Cortex Agent

## Prerequisites

- Active Snowflake connection
- Agent must already exist
- USAGE privilege on the agent's schema
- Appropriate role with permissions to modify the agent

Whenever running scripts, make sure to use `uv`.

## User Configuration Required

The following information will be requested during the workflow:

**Step 1 - Agent Identification:**

- **Database**: Where the agent is located (e.g., `MY_DATABASE`)
- **Schema**: Schema containing the agent (e.g., `AGENTS`)
- **Agent Name**: Name of the agent to edit (e.g., `MY_SALES_AGENT`)
- **Role**: A role with privileges to modify the agent (e.g., `MY_AGENT_EDITOR_ROLE`)
- **Connection Name**: Snowflake connection to use (default: `snowhouse`)

**Step 2 - Edit Selection:**

- **What to edit**: Instructions, tools, comment, models, orchestration, etc.

## Workflow Overview

This workflow edits an existing agent's configuration:

1. **Step 1:** Identify agent and setup workspace
2. **Step 2:** Get current agent configuration
3. **Step 3:** Select what to edit
4. **Step 4:** Gather changes based on selection
5. **Step 5:** Apply changes via REST API
6. **Step 6:** Verify changes were applied

## Workflow Steps

### Step 1: Identify Agent and Setup Workspace

**Goal:** Locate the agent to edit and create a working directory

**Actions:**

1. **Ask the user for agent location:**

   ```
   Which agent would you like to edit?
   - Database: [e.g., MY_DATABASE]
   - Schema: [e.g., AGENTS]
   - Agent Name: [e.g., MY_SALES_AGENT]
   - Connection: [default: snowhouse]
   
   What role should I use for editing?
   - Role: [e.g., MY_AGENT_EDITOR_ROLE]
   Note: This role must have privileges to modify the agent on <DATABASE>.<SCHEMA>
   ```

   If the user only provides the agent name, help them find it:

   ```sql
   SHOW AGENTS LIKE '%<AGENT_NAME>%' IN ACCOUNT;
   ```

2. **Construct Fully Qualified Agent Name:**

   - Format: `<DATABASE>.<SCHEMA>.<AGENT_NAME>`
   - Example: `MY_DATABASE.AGENTS.MY_SALES_AGENT`

3. **Create workspace (MANDATORY - do NOT create directories manually):**

   **⚠️ ALWAYS use `init_agent_workspace.py` to create the workspace. Do NOT manually create directories with `mkdir`. The script creates required files including `metadata.yaml`.**

```bash
uv run python ../scripts/init_agent_workspace.py --agent-name <AGENT_NAME> --database <DATABASE> --schema <SCHEMA>

# Example:
uv run python ../scripts/init_agent_workspace.py --agent-name MY_SALES_AGENT --database MY_DATABASE --schema AGENTS
```

**Expected Directory Structure After Running Script:**

```
{DATABASE}_{SCHEMA}_{AGENT_NAME}/
├── metadata.yaml          ← REQUIRED: Created by init_agent_workspace.py
├── optimization_log.md    ← Created by init_agent_workspace.py
├── versions/
│   └── vYYYYMMDD-HHMM/
│       ├── agent_config.json   ← Will contain current agent spec
│       ├── edit_spec.json      ← Will contain changes to apply
│       └── evals/
```

**Verify after running:** Check that `metadata.yaml` exists in the workspace root before proceeding.

**IMPORTANT:** After completing step 1, proceed to step 2. 

### Step 2: Get Current Agent Configuration

**Goal:** Retrieve and display the current agent configuration

**Actions:**

1. **Fetch current configuration:**

   ```bash
   uv run python ../scripts/get_agent_config.py --agent-name <AGENT_NAME> \
     --database <DATABASE> --schema <SCHEMA> --connection <CONNECTION> \
     --workspace <WORKSPACE_DIR> \
     --output-name current_agent_spec.json

   # Example:
   uv run python ../scripts/get_agent_config.py --agent-name MY_SALES_AGENT \
     --database MY_DATABASE --schema AGENTS --connection snowhouse \
     --workspace MY_DATABASE_AGENTS_MY_SALES_AGENT \
     --output-name current_agent_spec.json
   ```

2. **Read and present a summary** of the current configuration to the user:
   - Current instructions (orchestration, response, system, sample_questions)
   - Current tools and their descriptions
   - Current comment
   - Current model configuration

**IMPORTANT:** After completing Step 2, proceed to Step 3.

### Step 3: Select What to Edit

**Goal:** Understand what the user wants to modify

**Actions:**

1. **Present configurable options:**

   ```
   What would you like to edit?

   1. instructions - Agent instructions
      - orchestration: How the agent orchestrates responses
      - response: Response formatting instructions
      - system: System-level instructions
      - sample_questions: Example questions

   2. comment - Agent description

   3. models - Model configuration

   4. orchestration - Orchestration settings (budget, tokens)

   5. tools - Add, modify, or remove tool definitions

   6. tool_resources - Modify tool resources configuration

   7. experimental - Experimental flags

   8. profile - Agent profile settings

   Select option(s) or describe your changes:
   ```

2. **Route based on selection:**
   - **instructions** → Go to **Branch A**
   - **comment** → Go to **Branch B**
   - **tools / tool_resources** → Go to **Branch C**
   - **models / orchestration / experimental / profile** → Go to **Branch D**

### Branch A: Edit Instructions

**Goal:** Modify agent instructions

**Actions:**

1. **Ask which instruction field(s) to modify:**
   - `orchestration`: How the agent should orchestrate responses
   - `response`: Response formatting instructions
   - `system`: System-level instructions
   - `sample_questions`: Example questions the agent can answer

2. **Ask for the new value(s)** for the selected field(s).

3. **Build the agent spec JSON** with only the instructions changes:

   ```json
   {
     "instructions": {
       "<sub_key>": "<new_value>"
     }
   }
   ```

   **Example - Edit orchestration instructions:**
   ```json
   {
     "instructions": {
       "orchestration": "You are a helpful data analyst. Always explain your reasoning step by step."
     }
   }
   ```

   **Example - Edit multiple instruction fields:**
   ```json
   {
     "instructions": {
       "orchestration": "You are a sales analytics assistant.",
       "response": "Be concise. Use bullet points for lists.",
       "system": "Always verify data accuracy before presenting results."
     }
   }
   ```

4. **Save the edit spec to file (MANDATORY before applying):**

   Use `save_edit_spec.py` to save the changes - this ensures correct file naming:

   ```bash
   uv run python ../scripts/save_edit_spec.py --workspace $WORKSPACE_DIR \
     --spec '{"instructions": {"orchestration": "Your new orchestration instructions here"}}'
   ```

   **Example:**
   ```bash
   uv run python ../scripts/save_edit_spec.py --workspace MY_DATABASE_AGENTS_MY_SALES_AGENT \
     --spec '{"instructions": {"orchestration": "You are a helpful data analyst. Always explain your reasoning step by step."}}'
   ```

   The script will:
   - Create `edit_spec.json` in the latest version directory
   - Print the file path and contents for verification

5. **Go to Step 5** to apply changes.

### Branch B: Edit Comment

**Goal:** Update the agent's description/comment

**Actions:**

1. **Ask for the new comment text.**

2. **Build the agent spec JSON:**

   ```json
   {
     "comment": "<NEW_COMMENT>"
   }
   ```

3. **Save the edit spec to file (MANDATORY before applying):**

   Use `save_edit_spec.py` to save the changes:

   ```bash
   uv run python ../scripts/save_edit_spec.py --workspace $WORKSPACE_DIR \
     --spec '{"comment": "Your new comment here"}'
   ```

4. **Go to Step 5** to apply changes.

### Branch C: Edit Tools or Tool Resources

**Goal:** Add, modify, or remove tools from the agent

**Actions:**

1. **Ask the user what they want to do:**
   - Add an existing tool (from Snowflake)
   - Create a new tool (Semantic View, Cortex Search Service, or Stored Procedure)
   - Modify an existing tool's description
   - Remove a tool
   - Modify tool resources (warehouse, semantic view, etc.)

2. **If the user wants to add an existing tool:**

   a. **Ask for tools location:**

   ```
   Where are your semantic views and search services located?
   - Tools Database: [e.g., DATA_DB]
   - Tools Schema: [e.g., ANALYTICS]
   ```
   
   b. Query available **Cortex Search Services**:

   ```sql
   SHOW CORTEX SEARCH SERVICES IN SCHEMA <TOOLS_DATABASE>.<TOOLS_SCHEMA>;
   ```

   c. Query available **Semantic Views**:

   ```sql
   SHOW SEMANTIC VIEWS IN SCHEMA <TOOLS_DATABASE>.<TOOLS_SCHEMA>;
   ```

   d. Query available **Stored Procedures** (if the user wants custom tools):

   ```sql
   SHOW PROCEDURES IN SCHEMA <TOOLS_DATABASE>.<TOOLS_SCHEMA>;
   ```

   e. Present available tools to the user:

   - Show name and description/comment for each tool
   - Group by type (Cortex Search Services, Semantic Views, Stored Procedures)

   f. Ask the user to select which tool(s) to add

   g. For the selected tool, ask for:
   - **name**: Tool name for the agent
   - **description**: Tool description
   - **For cortex_analyst_text_to_sql**: warehouse
   - **For cortex_search**: id_column, title_column, max_results

3. **If the user wants to create a new tool:**

   - **Read the file `TOOL_CREATION.md`** in the `create-cortex-agent` directory for detailed instructions on creating:
     - Semantic Views
     - Cortex Search Services
     - Custom Tools (Stored Procedures)
   - After creating the tool, return to step 2 to add the newly created tool

4. **Read current tools** from `<WORKSPACE_DIR>/current_agent_spec.json`

5. **Build the complete tools and tool_resources arrays** including existing tools plus changes:

   **Example - Add cortex_analyst_text_to_sql tool:**
   ```json
   {
     "tools": [
       // ... existing tools ...
       {
         "tool_spec": {
           "type": "cortex_analyst_text_to_sql",
           "name": "query_sales",
           "description": "Query sales data using natural language"
         }
       }
     ],
     "tool_resources": {
       // ... existing tool_resources ...
       "query_sales": {
         "execution_environment": {
           "type": "warehouse",
           "warehouse": "MY_WAREHOUSE"
         },
         "semantic_view": "MY_DATABASE.MY_SCHEMA.SALES_VIEW"
       }
     }
   }
   ```

   **Example - Add cortex_search tool:**
   ```json
   {
     "tools": [
       // ... existing tools ...
       {
         "tool_spec": {
           "type": "cortex_search",
           "name": "search_docs",
           "description": "Search documentation"
         }
       }
     ],
     "tool_resources": {
       // ... existing tool_resources ...
       "search_docs": {
         "search_service": "MY_DATABASE.MY_SCHEMA.DOCS_SEARCH",
         "id_column": "DOC_ID",
         "title_column": "TITLE",
         "max_results": 5
       }
     }
   }
   ```

6. **Save the edit spec to file (MANDATORY before applying):**

   Use `save_edit_spec.py` to save the changes. For complex JSON, use stdin:

   ```bash
   cat << 'EOF' | uv run python ../scripts/save_edit_spec.py --workspace $WORKSPACE_DIR --stdin
   {
     "tools": [
       {
         "tool_spec": {
           "type": "cortex_search",
           "name": "search_docs",
           "description": "Search documentation"
         }
       }
     ],
     "tool_resources": {
       "search_docs": {
         "search_service": "MY_DATABASE.MY_SCHEMA.DOCS_SEARCH",
         "id_column": "DOC_ID",
         "title_column": "TITLE",
         "max_results": 5
       }
     }
   }
   EOF
   ```

7. **Go to Step 5** to apply changes.

### Branch D: Edit Models, Orchestration, Experimental, or Profile

**Goal:** Modify model configuration, orchestration settings, experimental flags, or profile

**Actions:**

1. **Ask for the specific changes** based on selection:

   **For models:**
   ```json
   {
     "models": {
       "orchestration": "claude-3-5-sonnet"
     }
   }
   ```

   **For orchestration (budget settings):**
   ```json
   {
     "orchestration": {
       "budget": {
         "seconds": 900,
         "tokens": 400000
       }
     }
   }
   ```

   **For experimental:**
   ```json
   {
     "experimental": {
       "flag_name": "value"
     }
   }
   ```

   **For profile:**
   ```json
   {
     "profile": {
       "setting_name": "value"
     }
   }
   ```

2. **Save the edit spec to file (MANDATORY before applying):**

   Use `save_edit_spec.py` to save the changes:

   ```bash
   uv run python ../scripts/save_edit_spec.py --workspace $WORKSPACE_DIR \
     --spec '{"models": {"orchestration": "claude-3-5-sonnet"}}'
   ```

3. **Go to Step 5** to apply changes.

### Pre-Step-5 Checklist (MANDATORY)

**⛔ STOP - Do NOT proceed to Step 5 until you verify:**

The `save_edit_spec.py` script should have printed:
- ✓ The path to the created `edit_spec.json` file
- The contents of the file

If you did NOT see this output, go back to Step 4 and run the `save_edit_spec.py` command.

**If `edit_spec.json` does not exist, the workflow will fail.**

### Step 5: Apply Changes via REST API

**Goal:** Apply the changes to the agent

**⚠️ CHECKPOINT**: Before applying changes, show the user what will be changed:

```
I will apply the following changes to agent <DATABASE>.<SCHEMA>.<AGENT_NAME>:

[Show the contents of edit_spec.json]
```

**If the user has already given explicit permission to apply changes** (e.g., "apply the changes", "I give you permission", "proceed with the edit"), **proceed immediately without asking for confirmation.**

Otherwise, ask: "Do you want to proceed? (yes/no)" and wait for confirmation. If user says "no", return to Step 3.

**⚠️ CRITICAL - PUT REPLACE BEHAVIOR:**

The REST API uses PUT semantics, which **REPLACES** the entire field you send. To preserve existing values when making partial changes, use the `--merge-with` flag to merge your `edit_spec.json` with the current configuration.

**How the merge works:**
- For nested objects like `instructions`: Your changes are deep-merged with existing values
- For arrays like `tools`: Your array replaces the existing array (include ALL tools)
- For simple values like `comment`: Your value replaces the existing value

**Example - Updating only `response` instructions:**
```
edit_spec.json:           {"instructions": {"response": "new value"}}
current_agent_spec.json:  {"instructions": {"orchestration": "existing", "response": "old"}}
                                    ↓ merge
Result sent to API:       {"instructions": {"orchestration": "existing", "response": "new value"}}
```

**⚠️ WARNING:** Do NOT include empty or null values in `edit_spec.json`:
```json
{"instructions": {"response": "new value", "orchestration": ""}}
```
This will **CLEAR** the orchestration instructions even with merge!

**Actions:**

1. **Apply changes using create_or_alter_agent.py with --merge-with:**

   ```bash
   uv run python ../scripts/create_or_alter_agent.py alter --agent-name <AGENT_NAME> \
     --config-file $WORKSPACE_DIR/versions/$VERSION/edit_spec.json \
     --merge-with $WORKSPACE_DIR/versions/$VERSION/current_agent_spec.json \
     --database <DATABASE> --schema <SCHEMA> --connection <CONNECTION>

   # Example:
   uv run python ../scripts/create_or_alter_agent.py alter --agent-name MY_SALES_AGENT \
     --config-file MY_DATABASE_AGENTS_MY_SALES_AGENT/versions/v20260216-1430/edit_spec.json \
     --merge-with MY_DATABASE_AGENTS_MY_SALES_AGENT/versions/v20260216-1430/current_agent_spec.json \
     --database MY_DATABASE --schema AGENTS --connection snowhouse
   ```

   **If the user has a specific role to use:**
   ```bash
   uv run python ../scripts/create_or_alter_agent.py alter --agent-name <AGENT_NAME> \
     --config-file $WORKSPACE_DIR/versions/$VERSION/edit_spec.json \
     --merge-with $WORKSPACE_DIR/versions/$VERSION/current_agent_spec.json \
     --database <DATABASE> --schema <SCHEMA> --role <ROLE> --connection <CONNECTION>
   ```

2. **Check the output** for success or error messages.

**IMPORTANT:** After completing Step 5, proceed to Step 6.

### Step 6: Verify Changes

**Goal:** Confirm the edit was applied successfully

**Actions:**

1. **Fetch updated configuration:**

   ```bash
   uv run python ../scripts/get_agent_config.py --agent-name <AGENT_NAME> \
     --database <DATABASE> --schema <SCHEMA> --connection <CONNECTION> \
     --workspace <WORKSPACE_DIR> \
     --output-name updated_agent_spec.json

   # Example:
   uv run python ../scripts/get_agent_config.py --agent-name MY_SALES_AGENT \
     --database MY_DATABASE --schema AGENTS --connection snowhouse \
     --workspace MY_DATABASE_AGENTS_MY_SALES_AGENT \
     --output-name updated_agent_spec.json
   ```

2. **Compare** with previous configuration to confirm changes were applied.

3. **Optionally test the agent** with a simple query:

   ```bash
   uv run python ../scripts/test_agent.py --agent-name <AGENT_NAME> \
     --question "What can you do?" \
     --workspace <WORKSPACE_DIR> \
     --output-name test_verification.json \
     --database <DATABASE> --schema <SCHEMA> --connection <CONNECTION>

   # Example:
   uv run python ../scripts/test_agent.py --agent-name MY_SALES_AGENT \
     --question "What can you do?" \
     --workspace MY_DATABASE_AGENTS_MY_SALES_AGENT \
     --output-name test_verification.json \
     --database MY_DATABASE --schema AGENTS --connection snowhouse
   ```

**Verification Checklist:**

- ✅ Command succeeded without errors
- ✅ Changes reflected in updated agent spec
- ✅ Agent responds correctly to test query (if tested)

**Agent edit complete.**

## Valid Agent Spec Keys

| Key | Type | Description |
|-----|------|-------------|
| `instructions` | object | Agent instructions |
| `models` | object | Model configuration |
| `orchestration` | object | Orchestration settings |
| `tools` | array | Tool definitions |
| `tool_resources` | object | Resources for tools |
| `comment` | string | Agent description |
| `profile` | object | Agent profile settings |
| `experimental` | object | Experimental flags |

### Instructions Sub-Keys

| Key | Description |
|-----|-------------|
| `orchestration` | How the agent should orchestrate responses |
| `response` | Response formatting instructions |
| `system` | System-level instructions |
| `sample_questions` | Example questions the agent can answer |

## Technical Notes

### Using create_or_alter_agent.py alter

The `alter` subcommand modifies an existing agent:

- **Full spec update**: Pass `--config-file` with complete specification
- **Instructions-only update**: Pass `--instructions` with text or file path
- **Combined**: Pass both to override instructions in a full spec

```bash
# Full spec update
uv run python ../scripts/create_or_alter_agent.py alter --agent-name MY_AGENT \
  --config-file edit_spec.json --database MY_DATABASE --schema AGENTS

# Instructions-only update (lightweight)
uv run python ../scripts/create_or_alter_agent.py alter --agent-name MY_AGENT \
  --instructions "You are a helpful assistant." --database MY_DATABASE --schema AGENTS
```

### Partial Updates

When editing, you only need to include the fields you want to change. The REST API will merge your changes with the existing configuration.

**Example - Only update instructions:**
```json
{
  "instructions": {
    "response": "Always include a summary at the end."
  }
}
```

**Example - Only update comment:**
```json
{
  "comment": "Sales analytics agent - v2.0"
}
```

### Tool Types Reference

| Type | Use Case | Required tool_resources |
|------|----------|------------------------|
| `cortex_analyst_text_to_sql` | Semantic views | `semantic_view`, `execution_environment` |
| `cortex_search` | Search services | `search_service`, `id_column`, `title_column`, `max_results` |
| `generic` | Stored procedures | `type: "procedure"`, `identifier`, `execution_environment`, `input_schema` |

## Troubleshooting

### Agent Not Found

**Symptom:** "agent does not exist" or HTTP 404

**Solution:**

```sql
SHOW AGENTS LIKE '%<AGENT_NAME>%' IN ACCOUNT;
```

Verify the database, schema, and agent name are correct.

### Permission Issues

**Symptom:** HTTP 401/403 or "insufficient privileges"

**Solution:**

1. Verify your role has appropriate privileges:
   ```sql
   SHOW GRANTS ON AGENT <DATABASE>.<SCHEMA>.<AGENT_NAME>;
   ```

2. If needed, request grants from admin:
   ```sql
   GRANT USAGE ON AGENT <DATABASE>.<SCHEMA>.<AGENT_NAME> TO ROLE <your_role>;
   ```

### Invalid Keys Error

**Symptom:** "Invalid keys: <key>"

**Solution:** Only use valid keys: `comment`, `experimental`, `instructions`, `models`, `orchestration`, `profile`, `tool_resources`, `tools`

### JSON Validation Failed

**Symptom:** "JSON validation failed" with specific errors

**Solution:** Check the error message and fix the JSON structure:
- `instructions` must be an object, not a string
- `tools` must be an array with `tool_spec` wrappers
- `tool_resources` must be a top-level object, not nested in tools

## Examples

### Edit Instructions Only

```json
{
  "instructions": {
    "orchestration": "You are a helpful data analyst. Always explain your reasoning.",
    "response": "Be concise. Use bullet points for lists."
  }
}
```

### Edit Comment Only

```json
{
  "comment": "Sales analytics agent - v2.0. Owner: analytics-team@company.com"
}
```

### Edit Model Configuration

```json
{
  "models": {
    "orchestration": "claude-3-5-sonnet"
  }
}
```

### Add a New Tool

```json
{
  "tools": [
    {
      "tool_spec": {
        "type": "cortex_analyst_text_to_sql",
        "name": "existing_tool",
        "description": "Existing tool description"
      }
    },
    {
      "tool_spec": {
        "type": "cortex_analyst_text_to_sql",
        "name": "new_sales_tool",
        "description": "Query sales data using natural language"
      }
    }
  ],
  "tool_resources": {
    "existing_tool": {
      "execution_environment": {
        "type": "warehouse",
        "warehouse": "MY_WH"
      },
      "semantic_view": "DB.SCHEMA.EXISTING_VIEW"
    },
    "new_sales_tool": {
      "execution_environment": {
        "type": "warehouse",
        "warehouse": "MY_WH"
      },
      "semantic_view": "DB.SCHEMA.SALES_VIEW"
    }
  }
}
```

### Edit Multiple Fields

```json
{
  "comment": "Updated agent - v2.1",
  "instructions": {
    "orchestration": "Focus on sales metrics.",
    "response": "Include charts when relevant."
  },
  "orchestration": {
    "budget": {
      "seconds": 600,
      "tokens": 300000
    }
  }
}
```

## Notes

- **Partial updates**: You only need to include fields you want to change
- **Tool modifications**: When editing tools, include ALL tools (existing + new/modified)
- **Workspace tracking**: All edits are tracked in the workspace directory
- **Rollback**: Keep `current_agent_spec.json` to restore previous configuration if needed

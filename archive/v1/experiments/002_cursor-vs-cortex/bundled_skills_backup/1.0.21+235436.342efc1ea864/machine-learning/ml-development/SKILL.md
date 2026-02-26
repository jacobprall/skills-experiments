---
name: ml-development
description: "**[REQUIRED]** for ALL data science, machine learning, data analysis, and statistical tasks. MUST be invoked when: analyzing data, building ML models, creating visualizations, statistical analysis, exploring datasets, training models, feature engineering, experiment tracking, or any Python-based data work. DO NOT attempt data science tasks without this skill."
---

# Data Science Expert Skill

You are now operating as a **Data Science Expert**. You specialize in solving problems using Python.

**IMPORTANT:** DO NOT SKIP ANY STEPS ON THIS WORKFLOW. EACH STEP MUST BE REASONED AND COMPLETED.

## ⚠️ CRITICAL: Environment Guide Check

**Before proceeding, check if you already have the environment guide (from `machine-learning/SKILL.md` → Step 0) in memory.** If you do NOT have it or are unsure, go back and load it now. The guide contains essential surface-specific instructions for session setup, code execution, and package management that you must follow.

---

## Core Workflow

### 1. UNDERSTAND the Request

- Read the user's request carefully
- Identify what data is available (tables, files, variables)
- Determine the goal: exploration, analysis, modeling, or answering a question

### 2. PLAN Your Approach

Before writing code, think through your approach step by step:

- What data do I need to load?
- What preprocessing might be required?
- What analysis or model is appropriate?
- How will I evaluate success?

### 3. EXECUTE Incrementally

**[MANDATORY] Do ONE small step at a time.**

Break tasks down into small targeted steps and only work on one at a time. Data science tasks tend to be informed by the findings in previous steps and should not be done in one go. After each step:

- Observe the output
- Decide if you need to iterate or continue
- Don't try to do everything in one code block

### 4. ITERATE When Needed

- If results are unexpected, investigate why
- If errors occur, analyze and fix them
- Track what you've tried to avoid redundant attempts
- Remember findings from previous steps

### 5. COMPLETE with Quality

When providing a final solution:

- Include a summary of what was accomplished
- Report all evaluation metrics
- Provide end-to-end executable code

---

## Data Access Patterns

**CRITICAL: Prefer Snowpark Pushdown Operations**

Always start with quick data inspection WITHOUT loading full tables:

```python
# Get row count
row_count = session.table("MY_TABLE").count()

# Preview first 5 rows
sample = session.table("MY_TABLE").limit(5).to_pandas()
```

### Efficient Data Access

```python
from snowflake.snowpark.functions import col

# PREFERRED: Filter and aggregate in Snowflake
df = session.table("MY_TABLE").filter(col("STATUS") == "ACTIVE").select(["COL1", "COL2"]).limit(10000).to_pandas()

# AVOID: Loading entire large tables
# df = session.table("MY_TABLE").to_pandas()  # Only for small tables (<100k rows)
```

**Always use Snowpark Session, NOT snowflake.connector.**

---

## CLI Workflow Steps

Use when operating on the CLI. Code is written as a local script. See your environment guide for execution details.

### Step 1: Ask About Experiment Tracking (for model training)

Check if the user has specified if they want to use experiment tracking.
If unspecified check with the user (using `ask_user_question` tool if available) if they want to use Snowflake's experiment tracking framework.
You should always check even if you feel it is a simple example or not directly related to snowflake.

**MANDATORY ASK:**

```markdown
Would you like to track this experiment using Snowflake's experiment tracking framework?
1. Yes - Track this model training experiment
2. No - Just train and evaluate
```

If the user mentions that they want to use experiment tracking you will need to do a few different things.

**IF THE USER SAYS YES**
You will need to ask a for the following information. Once again please use the `ask_user_question` tool if it is available.
Ask user for:

1) Database and schema for storing runs
2) Experiment name
3) Model framework if autologging or What parameters/metrics to track if manual

You can check what experiments are available by using either of the following commands

```SQL
SHOW EXPERIMENTS IN SCHEMA DATABASE.SCHEMA;
```

Below is provided an example question to prompt the user in order to ask them which of their experiments they want to use based on ones they have access to.

**Note:** If there are too many experiments in the schema (10+) you can instead just provide a few of the most relevant ones.

```markdown
What experiment name should be used for this experiment?
1. EXAMPLE_EXP_1
2. EXAMPLE_EXP_2
3. EXAMPLE_EXP_3
...
N. Other - You will be prompted to provide a name
```

Once you have collected this information load in the information from the skill `../experiment-tracking/SKILL.md`.

When the experiment is finished please share the URL with the user so that they can see it.

**Note:** For naming the runs please use conventions that are clear and readable and matches other ones the user has requested if applicable.

### Step 2: Ask About Model Serialization (for model training)

**⚠️ IMPORTANT:** This is about SAVING locally, NOT deployment.

**Do NOT ask:**

- "How would you like to deploy the model?"
- "Local only vs Register in Snowflake?"

**Do ask:**

```markdown
Would you like to save the trained model to a file (using `ask_user_question` tool if available)?
1. Yes - Save as pickle file (.pkl) for later use
2. No - Just train and evaluate

If yes, where should I save it? (default: ./model.pkl)
```

### Step 3: Analyze Data First

**⚠️ MANDATORY:** Understand data before writing code:

```sql
DESCRIBE TABLE <table_name>;
SELECT COUNT(*) FROM <table_name>;
SELECT * FROM <table_name> LIMIT 10;
```

### Step 4: Plan and Present

Plan the COMPLETE approach:

- Data loading strategy
- Data Visualization (Snowsight notebooks only; on CLI, save plots to files instead)
- Preprocessing steps
- Model selection
- Evaluation metrics

**Present your plan to the user before writing code.**

### Step 5: Write Complete Code

Set up the session following your loaded environment guide, then write the code:

```python
# Session setup per environment guide
# ...

# Load data using Snowpark
df = session.table("MY_TABLE").to_pandas()
# OR with filtering
df = session.table("MY_TABLE").select(["COL1", "COL2"]).filter(...).to_pandas()
```

#### Data Visualization Notes

- Ensure Visualizations are coherent, well labeled, and aesthetically pleasing
- **Snowsight only:** Render visualizations inline in notebook cells
- **CLI only:** Save visualizations to files (e.g., `plt.savefig("plot.png")`) — do NOT use notebooks on CLI
- Well done Visualizations help the user follow along the code and better understand the data and should be used frequently

### Step 6: Ask Before Executing

**⚠️ MANDATORY:** Before executing, ask user:

```markdown
I've written the complete script with:
- [Summary of what it does]
- [Data: X rows, Y columns]
- [Model: algorithm choice]
- [Expected output: metrics to report]
- [Model serialization: Yes/No, path if yes]

Ready to execute? (Yes/No)
```

### Step 7: Execute

Follow the execution instructions in your loaded environment guide.

### Step 8: Report Model Artifacts and Offer Next Steps

**⚠️ IMPORTANT:** After successful execution, if a model was saved:

1. **Report details:**

   ```markdown
   Model saved successfully:
   - File path: /absolute/path/to/model.pkl
   - Framework: sklearn/xgboost/lightgbm/pytorch/tensorflow
   - Sample input schema: [columns and types]
   ```

2. **Offer next step:**

   ```markdown
   The model has been saved locally. Would you like to register it to Snowflake Model Registry?
   ```

3. **If user says yes:**
   - Load `model-registry/SKILL.md`
   - Pass along context: model file path, framework, sample input schema
   - Tell model-registry: "User just trained this model, use this context"

---


### For Model Tasks

- [ ] Train/test split is proper (no data leakage)
- [ ] Appropriate metrics are used
- [ ] Model is evaluated on holdout data
- [ ] Feature importance is analyzed
- [ ] Performance is clearly reported

---

## Memory and Context

### Track Your Progress

- Remember what code you've executed
- Keep track of variables in memory
- Note what approaches you've tried
- Don't repeat failed attempts

### Reference Previous Work

When the user asks about previous experiments:

- Reference specific findings with metrics
- Mention which approach worked best
- Provide context from earlier analysis

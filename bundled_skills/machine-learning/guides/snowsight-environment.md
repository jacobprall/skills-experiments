# Snowsight Environment Guide

This guide applies when you are operating inside **Snowsight**. Follow these instructions for session setup, code execution, and package management across all ML sub-skills.

---

## Prerequisites

**Before starting any data science task, verify the following:**

1. **Check that the user is working in a Snowflake Notebook environment.**
   - The user must have an active notebook (`.ipynb`) open and connected to a Snowflake workspace.

2. **If no notebook is detected:**
   - **Do NOT proceed** with the data science task.
   - Politely ask the user to:
     1. Navigate to their Snowflake workspace.
     2. Create or open a Notebook.
     3. Ensure the notebook is connected to a running compute resource.
   - Once the user confirms the notebook is open and connected, proceed with the task.

3. **If a notebook is detected:**
   - Proceed directly with the task — do not ask for confirmation.

---

## Session Setup

Always obtain a Snowflake session using:

```python
from snowflake.snowpark.context import get_active_session
session = get_active_session()
```

**Tool usage guidance:**
- **SQL queries** (verification, status checks, SHOW commands): Use your `execute_sql` tool directly
- **Python code** (model operations, complex logic): Use notebook actions

---

## Code Execution

### Execution Strategy Decision Tree

**Before executing any cells, determine the notebook state:**

1. **Check kernel connection**: Use `get_notebook_state` to check `connectionState` and `sessionState`
2. **Check for existing variables**: Use `get_variables` to see if variables exist from prior execution
3. **Check cell execution history**: Look at `executionCounter` and `hasResultsFromPreviousRun` in cell results

**Decision Matrix:**

| Notebook State | Variables Exist? | Action |
|----------------|------------------|--------|
| Fresh notebook (no prior runs) | No | Run all cells (`run_type: 'all'`) |
| Connected kernel, variables exist | Yes | Run only NEW/MODIFIED cells (`run_type: 'single'`) |
| Disconnected/new kernel session | Stale (`hasResultsFromPreviousRun: true`) | Run all cells to rebuild state |
| Editing existing cells | Yes (want to preserve) | Run only the edited cell (`run_type: 'single'`) |

### Why This Matters

- **Avoid re-training models**: Training cells can take minutes/hours. Never re-run them unnecessarily.
- **Preserve expensive computations**: Data loading, transformations, and model objects persist in memory.
- **Incremental development**: Add new cells and run only those to build on existing state.

### Workflow Pattern

```python
# Step 1: Check notebook state FIRST
get_notebook_state(notebook_path)  # Check connectionState, sessionState
get_variables(notebook_path)        # Check if df, model, etc. already exist

# Step 2: Decide execution strategy
if variables_exist and kernel_connected:
    # Only run newly added/modified cells
    run_notebook(run_type='single', cell_id='new_cell_id')
else:
    # Fresh start - run all cells
    run_notebook(run_type='all')
```

### Rules

- **Always import all necessary packages at the start of your code**
- Check the execution environment (CPU/GPU) before running compute-intensive code
- Write direct executable code (no function wrappers)
- Reference variables from previous executions (they persist)
- Use `print()` statements to observe outputs
- Build incrementally on previous results
- Check the workspace for all existing .py and .ipynb files to better understand the workspace
- Show a bias for working with existing notebooks rather than creating new notebooks

### Detecting Modified Cells

Use `get_notebook_state` to check each cell's `isModified` field:
- `isModified: true` → Cell has changes that need re-running
- `isModified: false` → Cell output is current

Only re-run cells where `isModified: true` when preserving existing state.

### Do NOT

- Use `if __name__ == "__main__":` blocks
- Use argparse or command-line arguments
- Try to save files or modify the filesystem
- Attempt to install packages (use pre-installed ones)

---

## Pre-installed Libraries

You have access to these packages **without installation**:

**Machine Learning:** scikit-learn, xgboost, lightgbm, shap

**Time Series & Statistics:** statsmodels, prophet, scipy

**Data Processing:** pandas, numpy, snowflake-snowpark-python

**Deep Learning:** torch, transformers

**Data Visualization:** plotly, seaborn, matplotlib

---

## Working with Snowflake Data

### Prefer Snowpark Pushdown Operations

**Avoid loading entire tables into pandas unless necessary.** Use Snowpark pushdown operations to filter, aggregate, and transform data in Snowflake before pulling to Python.

#### Quick Data Inspection (ALWAYS start here)

```python
# Get row count without loading data
row_count = session.table("MY_TABLE").count()
print(f"Total rows: {row_count}")

# Get column names
columns = session.table("MY_TABLE").columns
print(f"Columns: {columns}")

# Preview first 5 rows
sample = session.table("MY_TABLE").limit(5).to_pandas()
print(sample)
```

#### Efficient Data Access

```python
from snowflake.snowpark.functions import col

# PREFERRED: Push down filters and aggregations to Snowflake
table = session.table("MY_TABLE")
df = table.filter(col("STATUS") == "ACTIVE").select(["COL1", "COL2"]).limit(10000).to_pandas()

# Aggregate in Snowflake, not pandas
summary = table.group_by("CATEGORY").agg({"AMOUNT": "sum", "COUNT": "count"}).to_pandas()

# AVOID: Loading entire large tables
# df = session.table("MY_TABLE").to_pandas()  # Only for small tables
```

#### Loading Full Datasets

Use the DataConnector API for large data:

```python
df = session.table("MY_DATASET")
pandas_df = DataConnector.from_dataframe(df).to_pandas()
```

Only load full data when:
- The table is small (< 100k rows)
- You need the entire dataset for model training
- Pushdown operations cannot achieve the goal

---

## GPU Check

Before running compute-intensive tasks, check available hardware:

```python
import torch

if torch.cuda.is_available():
    device = torch.device("cuda")
    print(f"GPU available: {torch.cuda.get_device_name(0)}")
    print(f"GPU memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
else:
    device = torch.device("cpu")
    print("Running on CPU")
```

---

## Container Runtime

- Container Runtime provides preconfigured, customizable environments for machine learning on Snowpark Container Services, supporting both interactive experimentation and batch ML workloads.
- It includes popular ML and deep learning frameworks, and lets you install additional packages from PyPI or internal repositories.
- Workloads run on CPU or GPU compute pools, with distributed processing that automatically uses all available resources.
- The DataConnector API makes it easy to load Snowflake data into frameworks like TensorFlow, PyTorch, or Pandas.
- You can use distributed training APIs for LightGBM, PyTorch, and XGBoost.

For more details, search the product documentation for "Container Runtime".

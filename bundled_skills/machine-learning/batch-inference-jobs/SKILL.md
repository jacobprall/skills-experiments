---
name: batch-inference-jobs
description: "Run batch inference on models in Snowflake Model Registry. Covers BOTH approaches: (1) Native SQL batch using run() on warehouses for SQL pipelines/dbt, and (2) Job-based batch using run_batch() on SPCS compute pools for large-scale/unstructured data. Triggers: batch inference, bulk predictions, run_batch, run(), offline scoring, score dataset, batch predictions on table, image inference, audio transcription, multimodal."
parent_skill: machine-learning
---

# Batch Inference Jobs

Run inference on registered models for batch workloads. Snowflake offers **two batch inference approaches**:

| Approach | API | Compute | Best For |
|----------|-----|---------|----------|
| **Native SQL Batch** | `mv.run()` | Virtual Warehouse | SQL pipelines, dbt, Dynamic Tables, Snowpark |
| **Job-based Batch** | `mv.run_batch()` | SPCS Compute Pool | Large-scale processing, unstructured data (images/audio/video) |

> **Documentation**: [Model Inference in Snowflake](https://docs.snowflake.com/en/developer-guide/snowflake-ml/inference/inference-overview)

---

## ⚠️ CRITICAL: Environment Guide Check

**Before proceeding, check if you already have the environment guide (from `machine-learning/SKILL.md` → Step 0) in memory.** If you do NOT have it or are unsure, go back and load it now. The guide contains essential surface-specific instructions for session setup, code execution, and package management that you must follow.

## Step 0: Choose Inference Approach

**MANDATORY:** Before proceeding, ask the user which batch inference approach they need:

```
For batch inference, there are two approaches:

1. **Warehouse-based** (`mv.run()`) - Runs on virtual warehouses
   - Best for: SQL pipelines, dbt models, Dynamic Tables, Snowpark DataFrames
   - Simpler setup, no compute pool required
   - Ideal for tabular data and lightweight models

2. **SPCS Job-based** (`mv.run_batch()`) - Runs on SPCS compute pools
   - Best for: Large-scale processing, GPU models, unstructured data (images/audio/video)
   - Requires compute pool setup
   - Supports parallel replicas for high throughput

Which approach do you need?
```

**⚠️ STOP**: Wait for user response.

**Routing based on response:**

- **Warehouse-based** → Refer user to the **model-registry** skill which covers `mv.run()` inference in detail. Do NOT continue with this skill.
- **SPCS Job-based** → Continue to Step 1 below.

---

## Job-based Batch Inference (`run_batch()`)

Run large-scale inference jobs on SPCS compute pools. Best for unstructured data (images/audio/video), GPU models, large-scale backfills.

> Requires `snowflake-ml-python>=1.26.0`.

**For unstructured data** (images, audio, video, multimodal LLMs):
→ Load `unstructured-data/SKILL.md`

## Prerequisites

- `snowflake-ml-python>=1.26.0`
- Model registered in Snowflake Model Registry
- Compute pool (CPU or GPU depending on model)
- Stage for output files (with SSE encryption)

## Limitations

- For multi-modal use cases, encryption is only supported on the server side
- Partitioned models are not supported

## Workflow

### Step 1: Identify Model and Version

**Ask user:**
```
To run batch inference, I need:

1. **Model name**: What model do you want to use? (from Model Registry)
2. **Database/Schema**: Where is the model registered?
```

**⚠️ STOP**: Wait for user response.

**After user responds, verify model exists:**
If multiple versions exist, ask user which version to use. Otherwise, use the latest.

**Get available functions:**

```python
mv.show_functions()
```

Note the function names (e.g., `predict`, `encode`, `__call__`). If the model has **multiple functions**, you'll need to specify which one to use in JobSpec. If the model has only **one function**, you can omit `function_name` from JobSpec.

### Step 2: Identify Input Data

**Ask user:**
```
What data do you want to run inference on?

1. **Snowflake table** - Tabular data (e.g., MY_DB.SCHEMA.INPUT_TABLE)
2. **Inline data** - Small dataset to create as DataFrame
3. **Unstructured data (non-template)** - Images/audio/video for models expecting raw bytes
   - Use with: Whisper, ViT, ResNet, YOLO, custom image/audio models
   - Best for: Focused tasks like image classification, audio transcription, object detection
4. **Unstructured data (template/LLM)** - Multimodal LLMs with OpenAI chat format
   - Use with: Qwen-VL, LLaVA, MedGemma, other vision-language LLMs
   - Best for: Image captioning, visual Q&A, multimodal reasoning
```

**⚠️ STOP**: Wait for user response.

**Routing based on response:**
- **Option 3 (non-template)** → Load `non-template/SKILL.md`
- **Option 4 (template/LLM)** → Load `template/SKILL.md`

**For Snowflake table:**
```python
input_df = session.table("<DATABASE>.<SCHEMA>.<TABLE_NAME>")
```

**For inline data:**
```python
input_df = session.create_dataframe([
    (5.1, 3.5, 1.4, 0.2),
    (4.9, 3.0, 1.4, 0.2),
], schema=["feature_1", "feature_2", "feature_3", "feature_4"])
```

### Step 3: Configure Output Stage

Batch inference writes results as Parquet files to a Snowflake stage. The user must provide an output stage location.

**Ask user:**
```
Where should I write the inference results?

Provide a stage location (e.g., @MY_DB.MY_SCHEMA.OUTPUT_STAGE/results/)
```

**⚠️ STOP**: Wait for user response.

**If user doesn't have a stage, create one:**

**⚠️ IMPORTANT**: The stage **must** use `SNOWFLAKE_SSE` encryption (server-side encryption). Client-side encryption is not supported for batch inference output.

**Output location format:**
```
@<DATABASE>.<SCHEMA>.<STAGE_NAME>/<optional_path>/
```

Examples:
- `@MY_DB.ML_SCHEMA.INFERENCE_STAGE/predictions/`
- `@MY_DB.ML_SCHEMA.OUTPUT_STAGE/batch_2024_01/`

### Step 4: Configure Compute Pool

**Query available compute pools:**

You can view available compute pool families at `https://docs.snowflake.com/en/sql-reference/sql/create-compute-pools` if needed.
**Recommend compute pool based on model type:**

**Ask user to confirm or create compute pool:**
```
Based on your model, I recommend:
- **Compute Pool**: <`POOL_NAME`> (<INSTANCE_FAMILY>)

Do you want to use this pool, or specify a different one?
```

**If user needs a new compute pool:**
Offer to create a new compute pool with appropriate instance family (CPU vs GPU)

### Step 5: Configure Job Parameters

**Configure JobSpec for scaling:**
```python
from snowflake.ml.model.batch import JobSpec

# Basic (single replica, model has only one function)
job_spec = JobSpec()

# Basic (single replica, model has multiple functions - must specify which one)
job_spec = JobSpec(function_name="<FUNCTION_NAME>")

# Scaled (multiple replicas)
job_spec = JobSpec(
    function_name="<FUNCTION_NAME>",  # Optional if model has only one function
    replicas=2,           # Number of replicas / instances
    num_workers=2,        # Workers per replica
)
```

> **Note**: `function_name` is only required when the model has multiple functions. If the model has a single function, it will be used automatically.

### Step 6: Present Configuration Summary

**⚠️ MANDATORY CHECKPOINT**: Before submitting, present summary:

```
I will submit a batch inference job with these settings:

- **Model**: <DATABASE>.<SCHEMA>.<MODEL_NAME> (version: <VERSION>)
- **Function**: <FUNCTION_NAME or "default (only one function)">
- **Input**: <INPUT_SOURCE> (<ROW_COUNT> rows)
- **Compute Pool**: <POOL_NAME>
- **Output**: @<DATABASE>.<SCHEMA>.<STAGE>/output/
- **Replicas**: <N>

Ready to submit? (Yes/No)
```

**⚠️ STOP**: Wait for explicit user approval.

### Step 7: Generate and Execute Batch Inference Code

Set up the session following your loaded environment guide, then generate the batch inference code.

**Template: Basic Tabular Inference**

```python
from snowflake.ml.registry import Registry
from snowflake.ml.model.batch import JobSpec, OutputSpec, SaveMode

# Session setup per environment guide
# e.g., create_snowpark_session() or get_active_session()
session = <SESSION_SETUP>
session.use_database("<DATABASE>")
session.use_schema("<SCHEMA>")

reg = Registry(session=session)
mv = reg.get_model("<MODEL_NAME>").version("<VERSION>")

input_df = session.table("<INPUT_TABLE>")
output_location = "@<DATABASE>.<SCHEMA>.<STAGE>/output/"

job = mv.run_batch(
    X=input_df,
    compute_pool="<COMPUTE_POOL>",
    output_spec=OutputSpec(
        stage_location=output_location,
        mode=SaveMode.OVERWRITE,
    ),
    job_spec=JobSpec(),  # Omit function_name if model has only one function
)

print(f"Job submitted. Waiting for completion...")
job.wait()
print(f"Job completed with status: {job.status}")
```

**Template: Scaled Inference with Multiple Replicas**

```python
job = mv.run_batch(
    X=input_df,
    compute_pool="<COMPUTE_POOL>",
    output_spec=OutputSpec(
        stage_location=output_location,
        mode=SaveMode.OVERWRITE,
    ),
    job_spec=JobSpec(
        function_name="<FUNCTION_NAME>",  # Optional if model has only one function
        replicas=<N>,
        num_workers=2,
    ),
)
```

### Step 8: Retrieve and Present Results

**After job completes, show output location:**
```sql
LS @<DATABASE>.<SCHEMA>.<STAGE>/output/;
```

**Read results as DataFrame:**
```python
results_df = session.read.option("pattern", ".*\\.parquet").parquet(output_location)
results_df.show(10)
```

**Save results to table (optional):**
```python
output_table = "<OUTPUT_TABLE_NAME>"
results_df.write.mode("overwrite").save_as_table(output_table)
print(f"Results saved to {output_table}")
```

**Present to user:**
```
Batch inference completed!

- **Status**: DONE
- **Output Location**: @<DATABASE>.<SCHEMA>.<STAGE>/output/
- **Files**: <N> parquet files

Would you like me to:
1. Show sample results
2. Save results to a table
3. Clean up resources
```

## Common Use Cases

### Classification/Regression (sklearn, xgboost, lightgbm)

```python
# Input: DataFrame with feature columns matching model signature
input_df = session.table("MY_DB.MY_SCHEMA.FEATURES_TABLE")

job = mv.run_batch(
    X=input_df,
    compute_pool="CPU_POOL",
    output_spec=OutputSpec(stage_location=output_location, mode=SaveMode.OVERWRITE),
    job_spec=JobSpec(),
)
```

### Text Embeddings (SentenceTransformer)

```python
# Input: DataFrame with text column
input_df = session.create_dataframe([
    ("The quick brown fox",),
    ("Snowflake is great",),
], schema=["input_feature_0"])

job = mv.run_batch(
    X=input_df,
    compute_pool="CPU_POOL",
    output_spec=OutputSpec(stage_location=output_location, mode=SaveMode.OVERWRITE),
    job_spec=JobSpec(function_name="encode"),  # SentenceTransformer uses encode
)
```

## Reading Output

Batch inference writes results as **Parquet files** to the specified output stage location.

### Handling Partial Output

A job can fail midway, leaving partial data. Batch inference writes a `_SUCCESS` sentinel file upon completion.

**Best practices:**
- Only read output after `_SUCCESS` file exists
- Use an empty output directory
- Use `SaveMode.ERROR` to fail if directory not empty (safer for production)

```python
# Safe production pattern
output_spec=OutputSpec(
    stage_location=output_location,
    mode=SaveMode.ERROR,  # Fail if output exists (prevents overwriting)
)
```

| SaveMode | Behavior |
|----------|----------|
| `OVERWRITE` | Replace existing output |
| `ERROR` | Fail if output directory not empty |

### Output Structure

The output contains:
- **All original input columns** - Your input data is preserved
- **Prediction column(s)** - Model outputs appended with names like `output_feature_0`, `predictions`, etc.

The exact output column name depends on the model's signature. Common patterns:

| Model Type | Output Column | Format |
|------------|---------------|--------|
| XGBoost/sklearn classifiers | `output_feature_0` | Integer (class label) |
| XGBoost/sklearn regressors | `output_feature_0` | Float (predicted value) |
| SentenceTransformer | `output_feature_0` | Array of floats (embedding vector) |

### Reading Results

```python
# List output files
session.sql(f"LS {output_location}").show()

# Read all parquet files
results_df = session.read.option("pattern", ".*\\.parquet").parquet(output_location)
results_df.show()

# Save to table for easier access
results_df.write.mode("overwrite").save_as_table("PREDICTION_RESULTS")
```

## Troubleshooting

### Job Management

```python
from snowflake.ml.jobs import list_jobs, delete_job, get_job

# View logs to troubleshoot
job.get_logs()

# Cancel a running job
job.cancel()

# List all jobs
list_jobs().show()

# Get handle to existing job by name
job = get_job("my_db.my_schema.job_name")

# Delete a job
delete_job(job)
```

> **Note**: The `result()` function from ML Job APIs is **not supported** for Batch Inference Jobs.

### Job Status

Check job status programmatically:
```python
print(f"Status: {job.status}")
print(f"Job ID: {job.id}")
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Model not found` | Wrong model name or schema | Verify with `SHOW MODELS IN SCHEMA` |
| `Compute pool not ready` | Pool is starting/suspended | Wait or run `ALTER COMPUTE POOL ... RESUME` |
| `Permission denied` | Missing grants | Grant usage on compute pool and stage |
| `Column mismatch` | Input doesn't match model signature | Check `mv.show_functions()` for expected inputs |

### Checking Model Signature

```python
# View model functions and their signatures
mv.show_functions()
```

## Stopping Points

- ✋ Step 0: After asking warehouse vs SPCS approach
- ✋ Step 1: After asking for model name/database
- ✋ Step 2: After asking for input data source
- ✋ Step 3: After asking for output stage location

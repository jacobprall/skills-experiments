---
name: machine-learning
description: "**[REQUIRED]** For **ALL** data science and machine learning tasks. This skill should ALWAYS be loaded in even if only a portion of the workflow is related to machine learning. Use when: analyzing data, training models, deploying models to Snowflake, registering models, working with ML workflows, running ML jobs on Snowflake compute, model registry, model service, model inference, log model, deploy pickle file, experiment tracking, model monitoring, ML observability, tracking drift, and model performance analysis. Routes to specialized sub-skills."
---

# Data Science & Machine Learning Skills

This skill routes to specialized sub-skills for data science and machine learning tasks.
This skill provides valuable information about all sorts of data science, machine learning, and mlops tasks.
It MUST be loaded in if any part of the user query relates to these topics❗❗❗

## Step 0: Load Environment Guide

**⚠️ CRITICAL: Before routing to any sub-skill, you MUST load the environment guide for your surface.**

Your system prompt indicates which surface you are operating on. Load the matching guide:

| Surface | Condition | Guide to Load |
|---------|-----------|---------------|
| **Snowsight** | You are operating inside the Snowflake Snowsight web interface | `guides/snowsight-environment.md` |
| **CLI / IDE** | You are operating in a command line terminal or IDE environment | `guides/cli-environment.md` |

The environment guide provides surface-specific instructions for **session setup, package management, and code execution** that apply to ALL sub-skills below. Sub-skills will reference these patterns rather than repeating them.

## Routing Behavior

**⚠️ CRITICAL: Route AUTOMATICALLY based on the user's request. Do NOT ask the user which sub-skill to use or how they want to deploy.**

When a user asks to "train a model", "build a model" or inquires about a similar task:

- **IMMEDIATELY** load `ml-development/SKILL.md` and start working
- Do NOT ask about deployment options upfront
- Do NOT ask "Local only vs Register in Snowflake vs End-to-end"
- Training and deployment are SEPARATE tasks - handle them sequentially if needed

## Intent Detection

### Dynamic Service Detection (Model Inference Services)

**⚠️ CRITICAL:** When a user mentions a **service name**, check if it's a model inference service:

1. Run `DESCRIBE SERVICE <DB>.<SCHEMA>.<SERVICE_NAME>`
2. If `managing_object_domain = 'Model'` → Route to `spcs-inference/SKILL.md`

This applies to ANY task involving the service (testing, REST API calls, latency profiling, benchmarking, debugging, management).

---

### Disambiguation: batch-inference vs spcs-inference (Online)

**⚠️ CRITICAL:** When user mentions "inference" without clear signals, you MUST ask for clarification. 
There is a decision matrix located in the public docs `https://docs.snowflake.com/en/developer-guide/snowflake-ml/inference/inference-overview`.

**Inference Disambiguation Workflow:**

When user says something like "run inference on my model" or "inference" without batch/online signals:

```
I can help you run inference on your model. There are three approaches:

1. **Native Batch Inference (SQL)** - Embed inference in SQL pipelines
   - <add decision points from docs matrix here>
   
2. **Job-Based Batch (SPCS)** - Run large-scale inference jobs
   - <add decision points from docs matrix here>

3. **Real-Time Inference (SPCS)** - Deploy a REST endpoint
   - <add decision points from docs matrix here>

Which approach fits your use case?
```

**⚠️ STOP**: Wait for user response before routing.

### Disambiguation: batch-inference vs ml-jobs

**⚠️ CRITICAL:** These two skills are commonly confused. Use this logic:

| User Intent | Key Signals | Route To |
|-------------|-------------|----------|
| Run inference on a **registered model** | "model registry" + ("inference", "predictions", "scoring", "run()", "run_batch()") | `batch-inference-jobs/SKILL.md` |
| Run a **Python script** on Snowflake compute | "script", "submit", "file", "directory", training code | `ml-jobs/SKILL.md` |

**Decision tree:**
1. Does the user want to run inference on an **existing model in the registry**?
   - **YES** → `batch-inference-jobs/SKILL.md` (covers both `mv.run()` and `mv.run_batch()`)
   - **NO** → Continue to step 2
2. Does the user want to run **custom Python code** (training, processing, or scripts) on Snowflake compute?
   - **YES** → `ml-jobs/SKILL.md` (uses `submit_file()` or `submit_directory()`)
   - **NO** → Ask clarifying question

### Routing Table

| User Says | Route To | Action |
|-----------|----------|--------|
| "analyze data", "train model", "build model", "feature engineering", "predict", "classify", "regression" | `ml-development/SKILL.md` | Load immediately, start training |
| "register model", "model registry", "log model", "pickle to snowflake", "save model to snowflake", "upload model", ".pkl file", ".ubj file" | `model-registry/SKILL.md` | Load immediately, start registration (Workflow A) |
| "deploy model", "deploy model for inference", "deploy for inference" | `model-registry/SKILL.md` | Load immediately, ask deployment target (Workflow B) |
| "create inference service", "inference endpoint", "serve model", "snowpark container services", "model endpoint", "deploy in container", "deploy model service", "real-time inference", "online inference" | `spcs-inference/SKILL.md` | Load immediately, create SPCS service |
| "batch inference", "bulk predictions", "run_batch", "run()", "offline scoring", "score dataset", "batch predictions", "inference on registered model", "run predictions on registry model", "score with registered model", "offline inference", "SQL inference", "dbt inference", "dynamic table inference" | `batch-inference-jobs/SKILL.md` | Load immediately, set up batch inference |
| **"inference", "run inference"** (ambiguous, no batch/online signals) | **ASK USER** | Use disambiguation workflow above to clarify batch vs online |
| "ml job", "ml jobs", "run on snowflake compute", "submit job", "submit script", "submit file", "remote execution", "GPU training", "run python script on snowflake" | `ml-jobs/SKILL.md` | Load immediately, set up job |
| "experiment tracking", "track experiment", "log metrics", "log parameters", "autolog", "training callback", "XGBoost callback", "LightGBM callback" | `experiment-tracking/SKILL.md` | Load immediately, set up experiment tracking |
| "model monitor", "monitor model", "add monitoring", "enable monitoring", "ML observability", "track drift", "model performance", "monitor predictions", "observability" | `model-monitor/SKILL.md` | Load immediately, set up monitoring |

**Sub-skill path aliases** (for routing resolution):

- `ml-job` → `ml-jobs/SKILL.md` (singular form routes to plural directory)
- `ml-jobs` → `ml-jobs/SKILL.md`
- `mljob` → `ml-jobs/SKILL.md`
- `mljobs` → `ml-jobs/SKILL.md`

## Workflow

```markdown
User Request → Load Environment Guide → Detect Intent → Load appropriate sub-skill → Execute

Examples:
- "Train a classifier" → Load ml-development → Train locally → Done
- "Deploy my model.pkl" → Load model-registry → Register to Snowflake → Done  
- "Train AND deploy" → Load ml-development → Train → Save model → Report artifacts → Ask about deployment → If yes, load model-registry WITH CONTEXT (file path, framework, schema)
```

**Key principle**: Complete ONE task at a time. Only ask about the next step after the current step is done.

## Context Preservation Between Skills

**⚠️ CRITICAL:** When transitioning from ml-development to model-registry:

**Information to preserve and pass along:**

- Model file path (absolute path to serialized model file)
- Framework used (sklearn, xgboost, lightgbm, pytorch, tensorflow, etc.)
- Sample input schema (columns and types from training data)
- Any other relevant training context

**Why this matters:**

- Avoids asking the user to repeat information they just provided
- Prevents accidental retraining of the model
- Prevents modification of the training script
- Improves user experience with seamless workflow

**How to do it:**

1. When ml-development saves a model, it reports all details
2. When loading model-registry, explicitly mention this context
3. Model-registry checks for this context before asking questions
4. Use the preserved context instead of asking user again

**Example handoff:**

```markdown
ml-development: "Model saved to /path/to/model.pkl (sklearn). Would you like to register it?"
User: "Yes"
[Load model-registry with context: path=/path/to/model.pkl, framework=sklearn, schema=[...]]
model-registry: "I see you just trained a sklearn model. What should I call it in Snowflake?"
```

## Sub-Skills

### ml-development

Data exploration, statistical analysis, model training, and evaluation. Covers the full ML development workflow from data loading to model evaluation.

### model-registry

Deploy serialized models to Snowflake Model Registry. Supports various model formats (`.pkl`, `.ubj`, `.json`, `.pt`, etc.) depending on framework. Routes to `spcs-inference` sub-skill for inference service creation.

### experiment-tracking

Skills for tracking model training experiments using Snowflake's experiment tracking framework.
Routes to `experiment-tracking` sub-skill for experiment tracking understanding.

### spcs-inference

Deploy registered models to Snowpark Container Services for real-time inference. Handles compute pool selection, GPU/CPU configuration, num_workers, and service creation. Part of the Model Registry workflow.

### batch-inference-jobs (Batch Inference Jobs)

Run batch inference on models **already registered** in the Snowflake Model Registry. Covers **two approaches**:
- **Native SQL Batch** (`mv.run()`): Warehouse-based, integrates with SQL pipelines (dbt, Dynamic Tables)
- **Job-based Batch** (`mv.run_batch()`): SPCS compute pools, for large-scale and unstructured data

Best for: bulk predictions on tables, scoring with registered models, SQL pipeline integration, processing images/audio/video.

**Key differentiator:** User wants to use an **existing registered model** to make predictions (not deploy an endpoint).

### ml-jobs

Transform local **Python scripts** into Snowflake ML Jobs that run on Snowflake compute pools. Uses `submit_file()` or `submit_directory()` to run custom code. Best for: custom training scripts, data processing pipelines, any Python code that needs Snowflake compute.

**Key differentiator:** User has a **Python script/file** they want to execute on Snowflake compute.

**Aliases:** ml-job, mljob, mljobs all route here.

### model-monitor
Set up ML Observability for models in the Snowflake Model Registry. Track drift, performance metrics, and prediction statistics over time. Supports segmentation for monitoring across data subsets and baseline comparison for drift detection.

## Reminders & Common Mistakes

### ❌ Don't assume a database/schema — always ask

When the workflow involves creating or writing to any Snowflake object (table, stage, model registry entry, experiment, etc.), **never silently pick a database/schema**. Always confirm with the user first.

- If a `DATABASE.SCHEMA` has already been used in this session, offer it as the default:
  ```
  I'll need to create [object] in Snowflake. I see we've been working with `<DATABASE>.<SCHEMA>`.
  Should I use that, or would you prefer a different database/schema?
  ```
- If no database/schema has been used yet, ask explicitly:
  ```
  Which database and schema should I use for [object]? (format: DATABASE.SCHEMA)
  ```
- **Carry the confirmed choice forward** — reuse it for subsequent objects in the session, but still confirm each time.
- **⚠️ Personal databases (e.g. `USER$VINAY`) are not supported** for ML workflows. If the user picks a personal database, warn them:
  ```
  Personal databases like `USER$<USERNAME>` don't support creating tables, model registry operations, or inference services. Please provide a standard database/schema instead.
  ```
- **⚠️ STOP**: Wait for the user's response before proceeding with any object creation.

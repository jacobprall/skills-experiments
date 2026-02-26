# Pipeline Sub-Skill

Set up automated document processing pipelines using Snowflake streams and tasks.

## When to Load

Load this reference when user wants to:
- Set up continuous document processing
- Automate extraction/parsing for new files
- Build production pipelines

---

## Post-Processing Options

**After any extraction/parsing/analysis completes, ask:**

```
What would you like to do next?
1. Done - one-time extraction (no pipeline needed)
2. Store results in a Snowflake table
3. Set up a pipeline for continuous processing
```

| Selection | Action |
|-----------|--------|
| Done | End workflow |
| Store results | Create table, insert results, then suggest pipeline |
| Pipeline | Continue to Pipeline Setup |

---

## Store Results in Table

### For AI_EXTRACT results:

```sql
CREATE TABLE IF NOT EXISTS db.schema.extraction_results (
  result_id INT AUTOINCREMENT,
  file_name STRING,
  extracted_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  -- Add user's extraction fields here
  field1 STRING,
  field2 STRING,
  raw_response VARIANT
);

INSERT INTO db.schema.extraction_results (file_name, field1, field2, raw_response)
SELECT 
  SPLIT_PART(relative_path, '/', -1),
  result:field1::STRING,
  result:field2::STRING,
  result
FROM DIRECTORY(@stage_name),
LATERAL (
  SELECT AI_EXTRACT(
    file => TO_FILE('@stage_name', relative_path),
    responseFormat => {'field1': 'description', 'field2': 'description'}
  ) AS result
)
WHERE relative_path LIKE '%.pdf';
```

### For AI_PARSE_DOCUMENT results:

```sql
CREATE TABLE IF NOT EXISTS db.schema.parsed_documents (
  doc_id INT AUTOINCREMENT,
  file_name STRING,
  content TEXT,
  parsed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

INSERT INTO db.schema.parsed_documents (file_name, content)
SELECT 
  SPLIT_PART(relative_path, '/', -1),
  AI_PARSE_DOCUMENT(TO_FILE('@stage_name', relative_path), {'mode': 'LAYOUT'}):content::STRING
FROM DIRECTORY(@stage_name)
WHERE relative_path LIKE '%.pdf';
```

### For Visual Analysis results:

```sql
CREATE TABLE IF NOT EXISTS db.schema.visual_analysis_results (
  result_id INT AUTOINCREMENT,
  image_path STRING,
  analysis_result TEXT,
  analyzed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

INSERT INTO db.schema.visual_analysis_results (image_path, analysis_result)
SELECT 
  relative_path,
  AI_COMPLETE('claude-3-5-sonnet', 'Analyze this image...', TO_FILE('@images_stage', relative_path))
FROM DIRECTORY(@images_stage)
WHERE relative_path LIKE '%.png';
```

**After storing results, ALWAYS suggest pipeline:**

```
Results stored successfully!

Would you like to set up an automated pipeline to process new documents as they arrive?
```

---

## Pipeline Setup

### Step 1: Page Range Configuration [WAIT]

**For AI_PARSE_DOCUMENT pipelines, ask:**

```
Do you want to parse the entire document or specific pages?

a. Entire document (all pages)
b. First page only
c. Specific page range (e.g., pages 1-10)
```

Wait for user response before proceeding.

**For AI_EXTRACT pipelines, ask:**

```
Do any of your files exceed 125 pages?
AI_EXTRACT has a limit of 125 pages per call.

a. No - all files are within 125 pages
b. Yes - some files may exceed 125 pages (needs chunking)
c. Not sure
```

Then ask:

```
Do you want to extract from the entire document or specific pages?

a. Entire document (all pages)
b. First page only (common for invoices/forms)
c. Specific page range (e.g., pages 1-5)
```

Wait for user response before proceeding.

### Step 2: Pipeline Configuration [WAIT]

**Ask user:**

```
Configure your pipeline:
1. Warehouse name: [e.g., COMPUTE_WH]
2. Schedule frequency:
   - Every 1 minute
   - Every 5 minutes (recommended)
   - Every 15 minutes
   - Every hour
```

---

## Pipeline Templates

### Template A: AI_EXTRACT Pipeline

```sql
-- 1. Create results table
CREATE TABLE IF NOT EXISTS db.schema.extraction_results (
  result_id INT AUTOINCREMENT,
  file_path STRING,
  file_name STRING,
  extracted_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  field1 STRING,
  field2 STRING,
  raw_response VARIANT
);

-- 2. Create stream on stage
CREATE OR REPLACE STREAM db.schema.doc_stream 
  ON STAGE db.schema.my_stage;

-- 3. Create processing task
CREATE OR REPLACE TASK db.schema.extract_task
  WAREHOUSE = MY_WAREHOUSE
  SCHEDULE = '5 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('db.schema.doc_stream')
AS
  INSERT INTO db.schema.extraction_results (file_path, file_name, field1, field2, raw_response)
  SELECT 
    relative_path,
    SPLIT_PART(relative_path, '/', -1),
    result:field1::STRING,
    result:field2::STRING,
    result
  FROM db.schema.doc_stream,
  LATERAL (
    SELECT AI_EXTRACT(
      file => TO_FILE('@db.schema.my_stage', relative_path),
      responseFormat => {'field1': 'description', 'field2': 'description'}
    ) AS result
  )
  WHERE METADATA$ACTION = 'INSERT'
    AND relative_path LIKE '%.pdf';

-- 4. Resume task
ALTER TASK db.schema.extract_task RESUME;
```

### Template B: AI_PARSE_DOCUMENT Pipeline

```sql
-- 1. Create results table
CREATE TABLE IF NOT EXISTS db.schema.parsed_documents (
  doc_id INT AUTOINCREMENT,
  file_path STRING,
  file_name STRING,
  content TEXT,
  parsed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 2. Create stream on stage
CREATE OR REPLACE STREAM db.schema.parse_stream 
  ON STAGE db.schema.my_stage;

-- 3. Create processing task
CREATE OR REPLACE TASK db.schema.parse_task
  WAREHOUSE = MY_WAREHOUSE
  SCHEDULE = '5 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('db.schema.parse_stream')
AS
  INSERT INTO db.schema.parsed_documents (file_path, file_name, content)
  SELECT 
    relative_path,
    SPLIT_PART(relative_path, '/', -1),
    AI_PARSE_DOCUMENT(TO_FILE('@db.schema.my_stage', relative_path), {'mode': 'LAYOUT'}):content::STRING
  FROM db.schema.parse_stream
  WHERE METADATA$ACTION = 'INSERT'
    AND relative_path LIKE '%.pdf';

-- 4. Resume task
ALTER TASK db.schema.parse_task RESUME;
```

### Template C: Visual Analysis Pipeline

```sql
-- 1. Create results table
CREATE TABLE IF NOT EXISTS db.schema.visual_results (
  result_id INT AUTOINCREMENT,
  image_path STRING,
  analysis_result TEXT,
  analyzed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 2. Create stream on images stage
CREATE OR REPLACE STREAM db.schema.images_stream 
  ON STAGE db.schema.images_stage;

-- 3. Create processing task
CREATE OR REPLACE TASK db.schema.analyze_task
  WAREHOUSE = MY_WAREHOUSE
  SCHEDULE = '5 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('db.schema.images_stream')
AS
  INSERT INTO db.schema.visual_results (image_path, analysis_result)
  SELECT 
    relative_path,
    AI_COMPLETE('claude-3-5-sonnet', 'Analyze this image...', TO_FILE('@db.schema.images_stage', relative_path))
  FROM db.schema.images_stream
  WHERE METADATA$ACTION = 'INSERT'
    AND (relative_path LIKE '%.png' OR relative_path LIKE '%.jpg');

-- 4. Resume task
ALTER TASK db.schema.analyze_task RESUME;
```

---

## Pipeline Management

### Monitor Status

```sql
-- Check task history
SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
  TASK_NAME => 'extract_task',
  SCHEDULED_TIME_RANGE_START => DATEADD('hour', -24, CURRENT_TIMESTAMP())
)) ORDER BY SCHEDULED_TIME DESC;

-- Check stream status
SHOW STREAMS LIKE '%stream%';

-- View pending files
SELECT * FROM db.schema.doc_stream;
```

### Pause/Resume

```sql
ALTER TASK db.schema.extract_task SUSPEND;  -- Pause
ALTER TASK db.schema.extract_task RESUME;   -- Resume
```

### Modify Schedule

```sql
ALTER TASK db.schema.extract_task SET SCHEDULE = '15 MINUTE';
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Task not running | Check if resumed: `SHOW TASKS LIKE 'task_name';` |
| Stream shows no data | Refresh stage: `ALTER STAGE stage_name REFRESH;` |
| Extraction errors | Check task history for error messages |

---

## Stopping Points

| After Step | Wait For |
|------------|----------|
| Post-processing options | User choice (Done/Store/Pipeline) |
| Store results | User confirmation to set up pipeline |
| 125-page question (AI_EXTRACT only) | User response |
| Page optimization (AI_EXTRACT only) | User response |
| Page range (AI_PARSE_DOCUMENT only) | User response |
| Pipeline configuration | Warehouse and schedule selection |

## Output

Automated pipeline with stream, task, and results table for continuous document processing.

# SQL Dynamic Analysis Helper

Python tool for analyzing SSC-EWI-0030 patterns from SnowConvert Issues.csv.

**Script:** `scripts/sql_dynamic_analyzer_helper.py`

## Commands

### generate

Create tracking JSON from Issues.csv:

**MANDATORY REQUIREMENTS**

All three inputs are **required**:

```bash
python3 scripts/sql_dynamic_analyzer_helper.py generate Issues.csv \
  --top-level-code-units TopLevelCodeUnits.csv \
  --source-dir path/to/source \
  --output sql_dynamic_analysis.json
```

**Required Parameters:**
- **Issues.csv** (positional, required): SnowConvert Issues.csv file containing SSC-EWI-0030 occurrences
- `--top-level-code-units FILE` (required): Path to TopLevelCodeUnits.csv file
- `--source-dir DIR` (required): Path to source code directory for extracting procedure code

**Optional Parameters:**
- `--code CODE`: Filter by issue code (default: SSC-EWI-0030)
- `--output FILE`: Output filename (default: sql_dynamic_analysis.json)

**Output Structure:**

The generated JSON contains code units with metadata and occurrences:

- **Global Metadata** (`metadata`):
  - `generated_at`: ISO timestamp
  - `total_occurrences`: Total dynamic SQL occurrences
  - `total_code_units`: Total code units
  - `files`: Paths used to generate the analysis JSON
    - `issues_csv`: Issues CSV file (input)
    - `top_level_code_units_csv`: TopLevelCodeUnits CSV file (input)
    - `source_dir`: Source directory (input) used to extract procedure text

- **Code Unit Metadata** (per procedure/function):
  - `procedure_name`: Name of the procedure/function
  - `filename`: Source file path
  - `code_unit_start_line`: Starting line number in source file
  - `lines_of_code`: Number of non-empty lines in the procedure
  - `procedure`: Full procedure code with line numbers (UTF-8)

- **Occurrence Fields** (per dynamic SQL instance):
  - `id`: Unique occurrence identifier
  - `line`: Line number where dynamic SQL occurs
  - `status`: PENDING (initial) / REVIEWED (after analysis)
  - `category`: Pattern name(s) - empty initially
  - `complexity`: low/medium/high/critical - empty initially
  - `notes`: JSON with analysis sections - empty initially
  - `generated_sql`: Actual SQL statement - empty initially
  - `sql_classification`: DQL/DML/DDL/DCL/TCL/UNKNOWN - empty initially

**Why Each Input is Required:**

**Issues.csv:**
- Contains all SSC-EWI-0030 dynamic SQL occurrences detected by SnowConvert
- Provides file paths, line numbers, and code unit associations
- Source of all records to be analyzed

**TopLevelCodeUnits.csv:**
- Provides procedure/function names for context
- Supplies exact code unit boundaries (start line, lines of code)
- Enables focused analysis of individual procedures instead of entire files
- Essential for accurate pattern classification

**Source Directory:**
- Extracts actual procedure code from source files
- Stores procedure code in JSON metadata for easy reference
- Only non-empty lines are counted and extracted
- Formatted with line numbers for precise code location
- Required for complete analysis workflow

### show-file

Display all occurrences grouped by code unit:

```bash
python3 scripts/sql_dynamic_analyzer_helper.py show-file sql_dynamic_analysis.json --id 1
```

**Options:**
- `--id ID`: Show all code units in the file containing this record ID
- `--filename FILE`: Show all code units in a specific file path

**Output:**
- Groups occurrences by code unit (procedure/function)
- Shows code unit metadata: name, start line, lines of code, occurrence count
- Lists all record IDs within each code unit
- Displays status, category, complexity for each occurrence

**Use for:** Viewing all code units in a file before analyzing each one

### update

Update record fields:

```bash
python3 scripts/sql_dynamic_analyzer_helper.py update sql_dynamic_analysis.json \
  --id 1 \
  --status REVIEWED \
  --category "Identifier-Driven" \
  --complexity "medium" \
  --generated-sql "SELECT * FROM sys.tables WHERE name = @TableName" \
  --sql-classification "DQL" \
  --notes '{
    "justification": "...",
    "complexity": "...",
    "migration_considerations": "..."
  }'
```

**Options:**
- `--id ID`: Record to update (required)
- `--status STATUS`: REVIEWED, PENDING, BLOCKED, IN_PROGRESS
- `--category CATEGORY`: Pattern name(s) from PATTERNS.md (pipe-separated for multiple)
- `--complexity LEVEL`: low, medium, high, critical
- `--generated-sql SQL`: The actual SQL statement that would be executed
- `--sql-classification CLASS`: SQL type - DQL, DML, DDL, DCL, TCL, or UNKNOWN
- `--notes JSON`: Analysis data in JSON format with keys: justification, complexity, migration_considerations

**Behavior:** Unspecified fields remain unchanged

### show

Display single record:

```bash
python3 scripts/sql_dynamic_analyzer_helper.py show sql_dynamic_analysis.json --id 5
```

### stats

Show analysis progress:

```bash
python3 scripts/sql_dynamic_analyzer_helper.py stats sql_dynamic_analysis.json
```

**Output:** Total records, status distribution, category distribution


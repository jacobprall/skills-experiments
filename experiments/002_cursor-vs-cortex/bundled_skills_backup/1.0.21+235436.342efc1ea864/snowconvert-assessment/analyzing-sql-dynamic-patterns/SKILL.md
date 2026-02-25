---
name: sql-dynamic-pattern-analyzer
description: Analyzes Dynamic SQL occurrences from SnowConvert issues, classifies patterns, scores complexity, provides migration considerations. Use for analyzing dynamic SQL patterns in SQL Server to Snowflake migrations.
parent_skill: snowconvert-assessment
---

# Analyzing SQL Dynamic Patterns

Analyzes Dynamic SQL occurrences from SnowConvert issues, classifies patterns, add complexity, provides migration considerations to Snowflake.

## Critical Rules

**NO CUSTOM SCRIPTS:** ONLY use `scripts/sql_dynamic_analyzer_helper.py`. Never create bash loops, automation scripts, or batch processing tools.

**NO BATCH UPDATES:** Each `update` command processes **ONE** record with **ONE** unique analysis.
- Do **not** “walk IDs” sequentially (e.g., 15, 16, 17, …) as a batch just because they are adjacent.
- Do **not** use bash loops / one-liners (e.g., `for id in ...; do python ... update ...; done`) to apply updates across many records.
- Do **not** copy/paste the same notes across multiple IDs; even within the same code unit, each occurrence must have its own specific rationale.

**CODE-UNIT-BASED WORKFLOW:** Use `show-file` to view all occurrences within a code unit (procedure/function). Analyze each code unit separately by reading its source code.
- The generated `sql_dynamic_analysis.json` stores the **full code unit text inside each record’s `metadata`** (e.g., `metadata.procedure`, plus location context like `metadata.filename` and `metadata.code_unit_start_line`). Treat the JSON as the “source bundle” for analysis.

**QUALITY OVER SPEED:** This work is often fast, but do not “rush” by batching, reusing notes, or skipping code review. Total time depends on the number of occurrences and how complex the code units are; aim for consistent, defensible analyses.

## Prerequisites

Before running this analysis, ensure you have:

1. **Issues.csv** - SnowConvert assessment output with SSC-EWI-0030 dynamic SQL occurrences
2. **TopLevelCodeUnits.csv** - SnowConvert assessment output with code unit metadata
3. **Source code directory** - Original SQL Server source files (as converted by SnowConvert)

All three are **required** for the analysis workflow.

## Workflow

Follow these steps for the workflow:

1. **Generate:** `generate Issues.csv --top-level-code-units TopLevelCodeUnits.csv --source-dir /path/to/source` → Creates sql_dynamic_analysis.json with  metadata and code
2. **Show file:** `show-file --id N` → View all occurrences within the code unit containing record N
3. **Analyze:** Review the procedure code (stored in metadata), classify patterns
4. **Update:** `update --id N --status REVIEWED --category "X" --complexity "Y" --notes "Z"` → For each occurrence in that code unit
5. **Track:** `stats` → Check progress
6. **Repeat:** Steps 2-4 for next code unit until ALL rows have status 'REVIEWED'

### 1. Generate JSON

Generate `sql_dynamic_analysis.json` containing all dynamic SQL occurrences with procedure code extracted from source files.

**Command:**
```bash
python scripts/sql_dynamic_analyzer_helper.py generate Issues.csv \
  --top-level-code-units TopLevelCodeUnits.csv \
  --source-dir path/to/source \
  --output sql_dynamic_analysis.json
```

**What This Creates:**
- JSON file with code units (procedures/functions) as top-level groups
- Each code unit contains metadata (name, location, full procedure code)
- Each code unit lists all dynamic SQL occurrences within it
- All occurrences start with status `PENDING` - ready for analysis

### 2. View Code Units

View all occurrences grouped by code unit (procedure/function) to organize your analysis.

```bash
python scripts/sql_dynamic_analyzer_helper.py show-file sql_dynamic_analysis.json --id N
```

**What This Shows:**
- The code unit in the file containing record N
- For each code unit: start line in the file, lines of code and number of occurrences.
- All record IDs within each code unit with their line where the dynamic sql happens, status (PENDING/REVIEWED), categories and complexity.

**How to view the procedure/function code (recommended):**

```bash
# Include procedure code for each code unit shown in the file output
python scripts/sql_dynamic_analyzer_helper.py show-file sql_dynamic_analysis.json --id N --include-code
```

**Analysis Approach:**
1. Use `show-file` to view all code units in a file
2. Select one code unit to analyze
3. Review the procedure code output (from `show-file --include-code`)
4. **Open** `reference/PATTERNS.md` and classify the dynamic SQL patterns you see
5. Update each occurrence individually
6. Move to next code unit

### 3. Classify Pattern & Analyze

**Reference (must-read):** `reference/PATTERNS.md` for ALL pattern definitions.

**Process:**
1. Read ALL pattern definitions from `PATTERNS.md`
2. Compare the source code against EACH pattern
3. Identify ALL patterns that apply (multiple patterns can apply to one occurrence)
4. Collect analysis information for notes (see guidelines below)
5. List patterns as pipe-separated values in the `--category` field

**Analysis Guidelines:**

While analyzing the code, collect the following information:

**generated_sql:**
- Extract the actual SQL string that would be executed at runtime
- Include the dynamic SQL construction logic to show what gets generated
- Use representative values for variables where applicable
- Provide a complete best-effort SQL statement; avoid ellipses (...) or vague/incomplete output

**sql_classification:**
- Classify the type of SQL operation: DQL (SELECT), DML (INSERT/UPDATE/DELETE), DDL (CREATE/ALTER/DROP), DCL (GRANT/REVOKE), TCL (COMMIT/ROLLBACK), or UNKNOWN
- This helps prioritize migration based on SQL operation type
- **Pattern tagging is separate**: use `reference/PATTERNS.md` to choose pattern names and record them in `--category` (pipe-separated). Do not infer patterns from `sql_classification`.

**justification (notes field):**
- Explain why this occurrence was classified into each identified pattern
- Reference specific code elements that demonstrate the pattern(s)
- Provide context about what the dynamic SQL accomplishes
- Minimum length: 40+ words; write full sentences (no terse bullets)
- Avoid “similar to occurrence ##”; restate the needed context explicitly

**complexity (notes field):**
- Identify technical factors that affect migration difficulty
- Document any deviations from the base pattern complexity score
- Focus on observable code characteristics
- Minimum length: 30+ words; write full sentences (no terse bullets)
- Avoid “similar to occurrence ##”; restate the needed context explicitly

**migration_considerations (notes field):**
- Recommend Snowflake-specific migration approaches
- Identify alternative implementation strategies where applicable
- Estimate migration effort based on code complexity
- Minimum length: 40+ words; write full sentences (no terse bullets)
- Avoid “similar to occurrence ##”; restate the needed context explicitly

### 4. Score Complexity

**Scale:** low (0-30), medium (31-60), high (61-85), critical (86-100)

**Base Scoring:**
- Each pattern in `PATTERNS.md` has a default risk level, effort estimation, and complexity score
- Start with the base score from the identified pattern(s)

**Process:**
1. Review base complexity from pattern definition in `PATTERNS.md`
2. Analyze actual code context thoroughly
3. Apply override **only if** code materially differs from pattern baseline
4. Document override reasoning in notes under `COMPLEXITY` section

### 5. Update CSV

```bash
python scripts/sql_dynamic_analyzer_helper.py update \
  sql_dynamic_analysis.json \
  --id <id> \
  --status REVIEWED \
  --category "Pattern-Name | Additional-Pattern" \
  --complexity medium \
  --generated-sql "CREATE TABLE dbo.TempTable (ID INT, Name VARCHAR(100))" \
  --sql-classification "DDL" \
  --notes '{
    "justification": "Line X uses dynamic SQL to construct table names based on user input variables...",
    "complexity": "- Deep concatenation chains (5+ levels)\n- No input validation detected\n- Cross-schema dynamic references",
    "migration_considerations": "- Recommend using Snowflake IDENTIFIER() function\n- Implement input validation before migration\n- Estimated effort: 4-6 hours per occurrence"
  }'
```

**Command Syntax:**
- First positional argument is the JSON file path
- `--id` is required to specify which record to update
- At least one of `--status`, `--category`, `--complexity`, `--notes`, `--generated-sql`, or `--sql-classification` must be provided

**Notes Format:**
- Use JSON with three required keys: `justification`, `complexity`, `migration_considerations`
- Escape quotes and newlines as needed for bash
- Use `\n` for line breaks within multi-line fields
- Single-quote the entire JSON to avoid bash interpretation issues

### 7. Monitor Progress

Check analysis progress at any time:

```bash
python scripts/sql_dynamic_analyzer_helper.py stats sql_dynamic_analysis.json
```

**Important Notes:**
- Total time depends on the number of occurrences and code-unit complexity.
- **DO NOT attempt to accelerate or batch process** — focus on consistent, defensible analyses.

## Notes Structure

Each update must include notes in **JSON format** with 3 required keys:

```json
{
  "justification": "Why this is dynamic SQL, what it does, context",
  "complexity": "Technical factors affecting migration difficulty",
  "migration_considerations": "Snowflake-specific recommendations, alternatives, effort estimate"
}
```

**Formatting:**
- Use `\n` for line breaks within multi-line fields
- Keep content factual and based on code analysis
- Avoid generic statements; be specific to the analyzed code

## Reference Files

- `reference/SQL_DYNAMIC_ANALYSIS_HELPER.md` - Helper script commands
- `reference/PATTERNS.md` - Pattern definitions with examples
## AI Summary Guide (SSIS to Snowflake Assessment)

Use this guide to **draft** an AI summary that gives a high-level, decision-ready overview of the SSIS workload before readers dive into individual packages. The audience is data engineers and solution architects preparing a migration to Snowflake.

### Summary Command (single source of truth)
Use this command to extract all signals in one place. It returns a well‑formatted text summary with:
1) AI analysis text per package
2) Classification counts
3) Top‑level summary (packages, connection managers, control flow components, data flow components, not supported elements)
4) Connection managers (name + creationName)

```bash
uv run python -m scai_assessment_analyzer etl <JSON_PATH> summary
```

### Step: Draft AI Summary (HTML)
Add this step after generating `etl_assessment_analysis.json`:

1. Review the output signals (classifications, complexity, scripts, connection managers).
2. Write a medium AI summary in HTML using the template below.
3. Save it as `ai_ssis_summary.html` so it can be embedded into the SSIS report later.
4. Update the assessment JSON to point to the summary HTML:
```bash
uv run python -m scai_assessment_analyzer etl <JSON_PATH> ai-summary ai_ssis_summary.html
```

### What to Look For
Focus on the most impactful signals:

**1) Sources and destinations**
- Top source systems (SQL Server, Oracle, APIs, files, SFTP, SharePoint, etc.)
- Data movement patterns (batch loads, incremental, CDC, staging to core)
- Target patterns (warehouse, reporting, operational, outbound)

**2) Data domains**
- Identify domains (e.g., finance, customer, operations, marketing)
- Call out any sensitive or regulated domains (PII, PCI, HIPAA)

**3) Package mix and complexity**
- Distribution by classification: Ingestion / Data Transformation / Configuration & Control
- Complexity drivers: script tasks, third-party components, dynamic SQL, external calls
- High-risk package patterns (nested loops, orchestration-heavy, large dataflows)

**4) Migration approach**
- Which parts are good candidates for dbt
- Which parts should map to Snowflake Tasks/Scripting
- What should be re-architected (if applicable)

**5) Key risks and dependencies**
- External dependencies (APIs, file drops, connectors)
- Missing or undocumented sources
- Performance or reliability concerns

### Connection Managers Overview (all packages)
The summary output already includes connection managers (name + creationName).
Use it to:
- Identify dominant connection types (OLEDB, FLATFILE, FTP/SFTP, HTTP/API, etc.).
- Highlight external systems and file-based integrations.
- Summarize common source/destination patterns for the AI summary.

### Writing Guidance
- Keep it 2-4 short paragraphs or 5-7 bullet highlights
- Use concrete counts and percentages when available
- Avoid package-by-package detail
- Keep tone factual, clear, and migration-focused

### HTML Template (example)
Use this structure so it can be embedded into the HTML report later:

```html
<section id="ai-summary" class="section">
  <h2>AI Summary</h2>
  <p>
    <strong>Workload Overview:</strong> Summarize scope (package count, components, major purpose).
  </p>
  <p>
    <strong>Sources and Destinations:</strong> Summarize key source types and load patterns.
  </p>
  <p>
    <strong>Connection Managers:</strong> Highlight dominant connection types and notable external systems (e.g., OLEDB, FLATFILE, FTP/SFTP, HTTP APIs).
  </p>
  <p>
    <strong>Complexity Drivers:</strong> Summarize top contributors to migration complexity.
  </p>
  <p>
    <strong>Recommended Migration Approach:</strong> Explain dbt vs Tasks/Scripting vs re-architecture.
  </p>
  <p>
    <strong>Key Risks:</strong> List 2-4 major risks or dependencies.
  </p>
</section>
```

### Output File
Write the summary as an HTML snippet file (not a full HTML page) so it can be embedded into the SSIS report:

- `ai_ssis_summary.html`


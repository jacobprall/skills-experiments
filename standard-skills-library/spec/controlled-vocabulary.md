# Controlled Vocabulary

Canonical terms, domain taxonomy, and naming conventions for the Standard Skills Library.

## Naming Conventions

- Directory names: `kebab-case`, lowercase only
- No underscores in directory or file names
- Skill names in front-matter must match directory names exactly
- Abbreviations: use full words unless the abbreviation is more recognized than the expansion (e.g., `spcs` is acceptable because "Snowpark Container Services" is rarely spoken in full; `dt` is not acceptable — use `dynamic-tables`)

## Domain Taxonomy

Every skill declares a `domain` in its front-matter. Valid domains:

| Domain | Scope | Example Concepts |
|--------|-------|------------------|
| `data-transformation` | Moving and reshaping data within Snowflake | Dynamic tables, streams, tasks, materialized views |
| `data-security` | Protecting, classifying, and auditing data access | Masking policies, row access policies, data classification, governance queries |
| `app-deployment` | Building and deploying applications on Snowflake | SPCS deployment, Streamlit in Snowflake |
| `cost-ops` | Understanding and controlling Snowflake spend | Warehouse credits, serverless costs, Cortex AI costs, budgets, anomalies |
| `ai-analytics` | Text and document analysis using Cortex AI functions | AI_CLASSIFY, AI_EXTRACT, AI_COMPLETE, AI_SENTIMENT, document processing |
| `data-observability` | Data quality monitoring, lineage, and impact analysis | DMFs, quality scores, upstream/downstream lineage, table comparison |

Reserved for future use:

| Domain | Scope |
|--------|-------|
| `data-integration` | External connectors, stages, pipes, ingestion beyond OpenFlow |
| `migration` | SnowConvert, workload assessment, wave planning |
| `semantic-modeling` | Semantic views for Cortex Analyst |

## Canonical Terms

Use these exact terms. Do not use synonyms.

| Canonical Term | Do Not Use |
|----------------|------------|
| dynamic table | DT, dynamic tbl |
| masking policy | mask policy, data mask |
| row access policy | RAP, row-level security, RLS |
| projection policy | column-level security |
| data classification | PII detection, sensitive data scan |
| compute pool | SPCS pool |
| image repository | SPCS repo, container registry |
| service | SPCS service, container service |
| warehouse | virtual warehouse, VW |
| target lag | refresh lag, DT lag |
| stage | external stage, internal stage (qualify when needed) |
| AI_CLASSIFY | ai classify, classify function |
| AI_EXTRACT | ai extract, extract function |
| AI_COMPLETE | ai complete, complete function |
| ACCOUNT_USAGE | account usage views |
| credits | compute credits (unless distinguishing from token credits) |

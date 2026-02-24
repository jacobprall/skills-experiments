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
| `data-integration` | Connecting external systems and ingesting data | Stages, pipes, integrations, OpenFlow, connectors |
| `cost-operations` | Understanding and controlling Snowflake spend | Warehouse sizing, billing views, metering, resource monitors |
| `ml-ai` | Machine learning and AI workflows on Snowflake | Model registry, batch inference, ML jobs, SPCS inference, Cortex agents |
| `app-development` | Building and deploying applications | SPCS deployment, Streamlit in Snowflake |
| `migration` | Moving workloads to Snowflake | SnowConvert, assessment, wave planning |
| `semantic-modeling` | Structured data models for Cortex Analyst | Semantic views, semantic model creation, validation |

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
| model registry | ML registry |
| batch inference | batch prediction, batch scoring |
| semantic view | semantic model (when referring to the Snowflake object) |
| warehouse | virtual warehouse, VW |
| target lag | refresh lag, DT lag |
| integration | external integration |
| stage | external stage, internal stage (qualify when needed) |

## Version Conventions

- Format: `"major.minor"` (string, quoted in YAML)
- Major bump: breaking changes to structure, renamed sections, removed content
- Minor bump: added examples, clarified constraints, new parameters documented
- Initial version: `"1.0"`

# Standard Skills Library

Structured Snowflake knowledge for coding agents. A strict DAG of routers, playbooks, and primitives that any agent can traverse to complete Snowflake tasks with expert-level precision.

## Quick Install (Cursor)

1. Copy or symlink `standard-skills-library/` into your project
2. Add `SKILL.md` as a Cursor skill (it auto-discovers via the `name: snowflake-ops` frontmatter)
3. Set up your Snowflake CLI connection:

```bash
snow connection add
snow sql -q "SELECT CURRENT_ACCOUNT()" -c <connection>
```

That's it. The agent reads `SKILL.md`, routes to the right domain, and follows the playbook or primitive.

## Architecture

Four-layer DAG. Edges point downward only.

```
SKILL.md → Domain Routers → Playbooks → Primitives
```

| Layer | Purpose | Count |
|-------|---------|-------|
| **SKILL.md** | Entry point. Routes to domain routers. | 1 |
| **Domain Routers** | Classify intent within a domain. | 6 |
| **Playbooks** | Step-by-step workflows composing primitives. | 9 |
| **Primitives** | Factual SQL reference for one Snowflake concept. | 19 |

## Domains

| Domain | What It Covers |
|--------|----------------|
| `data-transformation` | Dynamic tables, dbt, OpenFlow, streaming pipelines |
| `data-security` | Masking, row access, projection policies, classification, governance |
| `app-deployment` | Streamlit in Snowflake, SPCS containers, React apps |
| `cost-ops` | Warehouse credits, serverless costs, Cortex AI costs, budgets |
| `ai-analytics` | AI_CLASSIFY, AI_EXTRACT, AI_COMPLETE, document processing |
| `data-observability` | DMFs, lineage, table comparison, impact analysis |

## File Structure

```
standard-skills-library/
├── SKILL.md                          # Entry point (Cursor skill)
├── index.yaml                        # Discovery manifest
├── README.md
├── scripts/
│   └── snow-sql                      # SQL execution wrapper
├── routers/
│   ├── data-transformation/router.md
│   ├── data-security/router.md
│   ├── app-deployment/router.md
│   ├── cost-ops/router.md
│   ├── ai-analytics/router.md
│   └── data-observability/router.md
├── playbooks/
│   ├── build-streaming-pipeline/playbook.md
│   ├── secure-sensitive-data/playbook.md
│   ├── build-react-app/playbook.md
│   ├── investigate-cost-spike/playbook.md
│   ├── set-up-cost-monitoring/playbook.md
│   ├── enrich-text-data/playbook.md
│   ├── analyze-documents/playbook.md
│   ├── investigate-data-issue/playbook.md
│   └── assess-change-impact/playbook.md
├── primitives/
│   ├── dynamic-tables/skill.md
│   ├── dbt-snowflake/skill.md
│   ├── openflow/skill.md
│   ├── masking-policies/skill.md
│   ├── row-access-policies/skill.md
│   ├── projection-policies/skill.md
│   ├── data-classification/skill.md
│   ├── account-usage-views/skill.md
│   ├── warehouse-costs/skill.md
│   ├── serverless-costs/skill.md
│   ├── cortex-ai-costs/skill.md
│   ├── ai-classify/skill.md
│   ├── ai-extract/skill.md
│   ├── ai-complete/skill.md
│   ├── data-metric-functions/skill.md
│   ├── lineage-queries/skill.md
│   ├── table-comparison/skill.md
│   ├── spcs-deployment/skill.md
│   └── streamlit-in-snowflake/skill.md
└── spec/
    ├── standard-skills-library.md    # Architecture & principles
    ├── skill-schema.md               # Frontmatter schema
    ├── authoring-guide.md            # How to write skills
    ├── controlled-vocabulary.md      # Domain taxonomy & naming
    └── extending-routers.md          # Adding new domains
```

## Prerequisites

- [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) (`snow`) installed and configured
- At least one connection in `~/.snowflake/connections.toml`
- For cost queries: a role with `IMPORTED PRIVILEGES` on the `SNOWFLAKE` database

## For Skill Authors

See `spec/authoring-guide.md` for templates and `spec/skill-schema.md` for the frontmatter schema. The canonical spec is `spec/standard-skills-library.md`.

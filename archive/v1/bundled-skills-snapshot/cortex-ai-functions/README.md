# Cortex AI Functions

Snowflake Cortex AI Functions skills bundle for text, image, & document analytics.

## Taxonomy

The `cortex-ai-functions` skills exosystem consists of a main problem-to-solution router for intention detections (either atomic function(s) or custom workflow(s)), elevated high-level refs/ with curated functions docs, and nested purpose-built workflows with their own decomposed refs/ for clarifying nuances.

```
cortex-ai-functions/
├── SKILL.md                          # Main routing skill
├── README.md                         # For humans.. ;)
└── references/                       # AI Functions docs & tips
|   ├── ai-classify.md
|   ├── ai-complete.md
|   ├── ai-extract.md
|   ├── ai-filter.md
|   ├── ai-parse-doc.md
|   └── ai-summ-agg.md
└── document-intelligence/            # "Document intelligence" wofklows -- extraction, parsing, vis-analytics
└── content-insight/                  # "Content insightt" workflow -- planned
```

### Functions (atomic)

| Function | Category | Input | Output | Use Case |
|----------|----------|-------|--------|----------|
| **AI_CLASSIFY** | Classification | text/image | label(s) | Categorize, tag, route tickets, sentiment |
| **AI_FILTER** | Filtering | text/image | boolean | Yes/no conditions, semantic joins |
| **AI_EXTRACT** | Extraction | text/file | JSON object | Structured fields from documents |
| **AI_PARSE_DOCUMENT** | Parsing | file | markdown/text | Full document OCR, layout preservation |
| **AI_AGG** | Aggregation | text column | summary | Custom multi-row aggregation |
| **AI_SUMMARIZE_AGG** | Aggregation | text column | summary | General-purpose summarization |
| **AI_COMPLETE** | Generation | prompt/image | text/JSON | Custom LLM tasks, vision analysis |

### Workflows -- nested sub-skills

| Workflow | Description | Route |
|----------|-------------|-------|
| Document Intelligence | End-to-end document processing pipelines | `document-intelligence/SKILL.md` |
| Content Insight | Label, summarize, analyze content at scale | `content-insight/SKILL.md` (planned) |

## Changelog

| PR + author |
|----------------|
| [[cortex-ai-functions] document-intelligence skill spec by neeraj](https://github.com/snowflakedb/cortex-code-skills/pull/268) -- @sfc-gh-nejain |
| [[cortex-ai-functions] taxonomy + router skill + funcs-docs](https://github.com/snowflakedb/cortex-code-skills/pull/269)  -- @sfc-gh-mgruszczynski |
| [[cortex-ai-functions] document-intelligence workflows refactor + eval cases + ai-extract/ai-complete/ai-parse-doc specs](https://github.com/snowflakedb/cortex-code-skills/pull/271) -- @sfc-gh-kcichor |
---
type: router
name: ai-analytics
domain: ai-analytics
routes_to:
  - primitives/ai-classify
  - primitives/ai-extract
  - primitives/ai-complete
  - playbooks/analyze-documents
  - playbooks/enrich-text-data
---

# AI Analytics

Single entry point for Snowflake Cortex AI functions: classify, extract, filter, summarize, sentiment, and custom LLM tasks. All functions run inside Snowflake — data never leaves the account.

## Decision Criteria

| Input | How to Determine | Example User Statements |
|-------|-----------------|------------------------|
| **Goal** | What does the user want the AI to do? | "Classify tickets", "Extract invoice fields", "Summarize reviews" |
| **Input type** | Text column in a table, or files on a stage? | "My support_tickets table", "PDFs in a stage" |
| **Scale** | Single row test, or batch across a table? | "Try it on one row", "Run on all 10k rows" |

## Routing Logic

```
Start
  ├─ User wants to PROCESS DOCUMENTS or FILES (PDFs, images, stage)?
  │   └─ YES → playbooks/analyze-documents
  │
  ├─ User wants to ENRICH TABLE DATA (classify + extract + sentiment pipeline)?
  │   └─ YES → playbooks/enrich-text-data
  │
  ├─ User wants to CLASSIFY text/images into categories?
  │   └─ YES → primitives/ai-classify
  │
  ├─ User wants to EXTRACT structured fields from text?
  │   └─ YES → primitives/ai-extract
  │
  ├─ User wants SENTIMENT analysis?
  │   └─ YES → primitives/ai-classify (sentiment pattern)
  │
  ├─ User wants to SUMMARIZE or AGGREGATE text across rows?
  │   └─ YES → primitives/ai-complete (AI_AGG / AI_SUMMARIZE_AGG section)
  │
  └─ User wants a CUSTOM LLM prompt or general AI task?
      └─ YES → primitives/ai-complete
```

Check for multi-step intent first. If the user describes a pipeline ("classify, extract product, run sentiment, build a summary"), route to the enrich-text-data playbook.

## Routes To

| Target | Mode | When Selected | What It Provides |
|--------|------|---------------|------------------|
| `playbooks/analyze-documents` | Playbook | Files/documents on a stage need processing | Stage setup → single-file test → batch extraction → result storage |
| `playbooks/enrich-text-data` | Playbook | Multi-step AI enrichment of a text table | Classify → extract → sentiment → summary pipeline with test-before-batch |
| `primitives/ai-classify` | Reference | Narrow: classify or categorize text/images | AI_CLASSIFY syntax, patterns, options |
| `primitives/ai-extract` | Reference | Narrow: extract fields from text or files | AI_EXTRACT syntax, TO_FILE patterns, response formats |
| `primitives/ai-complete` | Reference | Narrow: custom prompts, summarization, aggregation | AI_COMPLETE, AI_AGG, AI_SUMMARIZE_AGG syntax |

## Anti-patterns

| Mis-routing | Why It Happens | Correct Route |
|-------------|----------------|---------------|
| Sending "process my invoices" to ai-classify | Documents need AI_EXTRACT, not AI_CLASSIFY | Route to `playbooks/analyze-documents` |
| Running AI functions on full table without testing | Credits are consumed per-row — bad prompts waste money at scale | Always test on LIMIT 5-10 first, then batch |
| Using AI_COMPLETE for classification | AI_CLASSIFY is purpose-built and cheaper for categorization | Route classification tasks to `primitives/ai-classify` |
| Sending sentiment to AI_COMPLETE | AI_CLASSIFY with sentiment labels or AI_SENTIMENT is simpler | Use AI_CLASSIFY pattern for sentiment categories |

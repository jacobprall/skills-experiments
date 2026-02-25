---
name: cortex-ai-functions
description: "Use Snowflake Cortex AI Functions for text/image analytics. Use when: classifying content, extracting entities, sentiment analysis, summarizing text, translating, filtering, embedding, parsing documents, redacting PII, aggregating data, document intelligence workflows, content insight workflows. Triggers: AI_CLASSIFY, AI_COMPLETE, AI_EXTRACT, AI_FILTER, AI_SENTIMENT, AI_SUMMARIZE, AI_TRANSLATE, AI_EMBED, AI_AGG, AI_REDACT, AI_PARSE_DOCUMENT, classify text, data, documents, extract from text, extract text from document, extract text from PDF, extract text from image, extracting, invoices, sentiment, summarize, translate, which AI function, cortex function, process documents, label content, analyze text, OCR, read PDF, read document, get text from PDF, get text from document, pull text from file, extract data from files, extract from my files, process my files, my files, my documents, read my documents, get data from document, file extraction, document processing, file processing, get information from documents, analyze files, parse files, data from PDF, invoice processing, contract extraction, receipt extraction, form extraction, extract fields, document data, file data, stage files, files on stage, PDF extraction, image extraction, document OCR, scan documents, digitize documents."
---

# Snowflake Cortex AI Functions

Select the right Cortex AI Function or workflow for your analytics task on text, images, or documents.

## ⚠️ CRITICAL: Document/File Routing Rule

**ALL requests involving files or documents MUST route to `document-intelligence/SKILL.md` first.** Never route directly to function references for file/document tasks. This ensures pricing is displayed and test-before-batch safeguards are applied.

## Workflow

### Step 1: Detect Intent

**Check workflows FIRST (priority), then fall back to specific functions.**

#### Workflows (Check First)

| Intent | Triggers | Route |
|--------|----------|-------|
| DOCUMENT_INTELLIGENCE | process documents, extract data from docs, parse PDFs, invoice processing, contract analysis, document pipeline, files, my files, my documents, extract from file, PDF, image, OCR, stage files, extract fields, parse document, read document, get text from PDF, document extraction, file extraction, invoices, contracts, receipts, forms, digitize | `document-intelligence/SKILL.md` |
| CONTENT_INSIGHT | label content, summarize docs, analyze text, content moderation, tag articles, sentiment at scale | `<to-be-implemented>` |
| SELECT | which function, help me choose, compare functions | Step 2 |

#### Specific AI Functions (If No Workflow Match)

| Intent | Triggers | Route |
|--------|----------|-------|
| CLASSIFY | classify, categorize, label, tag content, route tickets | Load `references/ai-classify.md` |
| FILTER | filter, yes/no, true/false, match condition | Load `references/ai-filter.md` |
| EXTRACT | extract, parse entities, get info from text | Load `references/ai-extract.md` |
| SENTIMENT | sentiment, tone, positive/negative | `<to-be-implemented>` |
| SUMMARIZE | summarize, condense, tldr | Load `references/ai-summ-agg.md` |
| AGGREGATE | aggregate insights, combine rows, analyze across | Load `references/ai-summ-agg.md` |
| TRANSLATE | translate, localize, convert language | `<to-be-implemented>` |
| EMBED | embed, vector, similarity search, clustering | `<to-be-implemented>` |
| PARSE_DOC | parse document, OCR, extract from PDF/image | Load `references/ai-parse-doc.md` |
| REDACT | redact, mask PII, anonymize | `<to-be-implemented>` |
| TRANSCRIBE | transcribe, audio to text, video to text | `<to-be-implemented>` |
| COMPLETE | custom prompt, general LLM task, AI_COMPLETE | Load `references/ai-complete.md` |

### Step 2: Route

**If specific AI Function:** Load the corresponding reference from `references/` directory.

**If DOCUMENT_INTELLIGENCE:** Load `document-intelligence/SKILL.md`

**If CONTENT_INSIGHT:** Load `content-insight/SKILL.md`

**If SELECT or unclear**, ask: [WAIT]
```
What would you like to do?

AI Functions:
1. Classify - Categorize content into labels (AI_CLASSIFY)
2. Filter - Filter rows by natural language condition (AI_FILTER)
3. Extract - Extract structured data from text (AI_EXTRACT)
4. Sentiment - Analyze sentiment/tone (AI_SENTIMENT)
5. Summarize - Condense text (AI_SUMMARIZE_AGG)
6. Aggregate - Get insights across rows (AI_AGG)
7. Translate - Convert to another language (AI_TRANSLATE)
8. Embed - Generate vectors for search/clustering (AI_EMBED)
9. Parse Document - OCR and extract from PDFs/images (AI_PARSE_DOCUMENT)
10. Redact - Mask PII (AI_REDACT)
11. Transcribe - Audio/video to text (AI_TRANSCRIBE)
12. Complete - Custom LLM task (AI_COMPLETE)

Workflows:
A. Document Intelligence - Process & extract data from documents at scale
B. Content Insight - Label, summarize, and analyze content
```

## Function Quick Reference

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| AI_CLASSIFY | Categorize into labels | text/image, labels[] | label or label[] |
| AI_FILTER | Boolean condition check | text/image, condition | TRUE/FALSE |
| AI_EXTRACT | Extract structured data | text/file, fields | OBJECT |
| AI_SENTIMENT | Sentiment score | text | FLOAT (-1 to 1) |
| AI_SUMMARIZE_AGG | Summarize many rows | text column, prompt | VARCHAR |
| AI_AGG | Aggregate insights | text column, prompt | VARCHAR |
| AI_TRANSLATE | Language translation | text, from_lang, to_lang | VARCHAR |
| AI_EMBED | Generate embedding | text/image | VECTOR |
| AI_SIMILARITY | Compare embeddings | input1, input2 | FLOAT (0 to 1) |
| AI_PARSE_DOCUMENT | Parse docs/images | file, mode | OBJECT |
| AI_REDACT | Mask PII | text | VARCHAR |
| AI_TRANSCRIBE | Audio/video to text | file | OBJECT |
| AI_COMPLETE | General LLM task | prompt, model | VARCHAR/OBJECT |

## Stopping Points

- ✋ Step 2: After presenting menu (if SELECT intent) - wait for user selection

## Output

Routes user to appropriate sub-skill or function reference based on detected intent.

## Notes

- All functions run in Snowflake (data never leaves)
- Functions work in SELECT, WHERE, JOIN clauses
- Use batch processing for best throughput
- For interactive/low-latency: consider REST API instead

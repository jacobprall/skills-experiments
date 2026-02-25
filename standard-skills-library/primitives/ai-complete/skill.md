---
type: primitive
name: ai-complete
domain: ai-analytics
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/functions/ai_complete"
---

# AI_COMPLETE & Aggregation Functions

Run custom LLM prompts (AI_COMPLETE), summarize text across rows (AI_SUMMARIZE_AGG), and aggregate with custom instructions (AI_AGG). All run inside Snowflake.

## AI_COMPLETE

### Syntax

```sql
-- Simple text completion
AI_COMPLETE( model, prompt )

-- With options
AI_COMPLETE( model, prompt, options )

-- Image analysis (vision)
AI_COMPLETE( model, prompt, TO_FILE('@stage', 'image.png') [, options] )

-- Multi-turn conversation
AI_COMPLETE( model, conversation_array, options )
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | STRING | Yes | Model name (see models below) |
| `prompt` | STRING | Yes* | Text prompt |
| `file` | FILE | No | Image via TO_FILE for vision tasks |
| `conversation` | ARRAY | Yes* | Array of `{role, content}` objects for multi-turn |
| `options` | OBJECT | No | `max_tokens`, `temperature`, `response_format`, `guardrails` |

*One of `prompt` or `conversation` required.

### Common Models

| Model | Best For |
|-------|----------|
| `claude-3-5-sonnet` | General purpose, vision |
| `llama3.3-70b` | Fast, cost-effective text tasks |
| `mistral-large2` | European deployment |

### Core Patterns

**Basic text completion:**
```sql
SELECT AI_COMPLETE('claude-3-5-sonnet',
    'Summarize this text in one sentence: ' || text_column
) AS summary
FROM my_table
LIMIT 5;
```

**Structured JSON output:**
```sql
SELECT AI_COMPLETE('claude-3-5-sonnet', prompt, {
    'response_format': {
        'type': 'json',
        'schema': {
            'type': 'object',
            'properties': {
                'category': {'type': 'string'},
                'confidence': {'type': 'number'}
            },
            'required': ['category', 'confidence']
        }
    }
}) AS result
FROM my_table;
```

**Image/chart analysis:**
```sql
SELECT AI_COMPLETE('claude-3-5-sonnet',
    'Extract all data points from this chart as a table.',
    TO_FILE('@db.schema.stage', 'chart.png')
) AS analysis;
```

**Chain with AI_PARSE_DOCUMENT for large PDFs:**
```sql
WITH parsed AS (
    SELECT AI_PARSE_DOCUMENT(
        TO_FILE('@stage', 'report.pdf'),
        {'mode': 'LAYOUT'}
    ):content::STRING AS text
)
SELECT AI_COMPLETE('claude-3-5-sonnet',
    'Extract the key findings from this report:\n\n' || text
) AS findings
FROM parsed;
```

## AI_AGG — Custom Text Aggregation

Aggregate text across multiple rows with a custom instruction. No context window limits — handles datasets of any size via automatic chunking.

### Syntax

```sql
AI_AGG( text_expression, instruction )
```

### Patterns

**Extract recurring themes:**
```sql
SELECT AI_AGG(ticket_text,
    'Identify the top 5 recurring issues. Return as a numbered list.'
) AS top_issues
FROM support_tickets;
```

**Summarize by group:**
```sql
SELECT
    category,
    AI_AGG(review_text,
        'Summarize the key positive and negative points mentioned.'
    ) AS summary
FROM reviews
GROUP BY category;
```

**Extract structured insights:**
```sql
SELECT AI_AGG(
    'Priority: ' || priority || ' | ' || description,
    'Identify the most critical issues requiring immediate attention. Return as a list.'
) AS critical_issues
FROM support_tickets;
```

## AI_SUMMARIZE_AGG — General Summarization

Like AI_AGG but without a custom instruction — produces a general-purpose summary.

### Syntax

```sql
AI_SUMMARIZE_AGG( text_expression )
```

### Patterns

**Summarize all rows:**
```sql
SELECT AI_SUMMARIZE_AGG(review_text) AS summary
FROM customer_reviews;
```

**Summarize by group:**
```sql
SELECT product_id,
    AI_SUMMARIZE_AGG(review_text) AS product_summary
FROM reviews
GROUP BY product_id;
```

**Combine multiple columns:**
```sql
SELECT AI_SUMMARIZE_AGG(
    'Subject: ' || subject || '\nBody: ' || body
) AS ticket_summary
FROM support_tickets
WHERE created_at >= DATEADD('day', -7, CURRENT_DATE());
```

## When to Use Which

| Scenario | Function |
|----------|----------|
| Classify into categories | AI_CLASSIFY (not AI_COMPLETE) |
| Extract specific fields from text | AI_EXTRACT (not AI_COMPLETE) |
| Binary yes/no question | AI_FILTER (not AI_COMPLETE) |
| Custom prompt on a single row | AI_COMPLETE |
| Summarize text across many rows | AI_SUMMARIZE_AGG or AI_AGG |
| Aggregate with specific instruction | AI_AGG |
| Analyze images or charts | AI_COMPLETE with vision |
| Full text from a document | AI_PARSE_DOCUMENT, then AI_COMPLETE |

## Constraints

- AI_COMPLETE output is non-deterministic — same input may produce slightly different output
- AI_COMPLETE has context window limits per model; AI_AGG/AI_SUMMARIZE_AGG do not
- Image analysis requires vision-capable models and supported image formats
- Image size limit: 10 MB (3.75 MB for Claude models)
- Cannot be used in dynamic table definitions (non-deterministic)
- Requires SNOWFLAKE.CORTEX_USER database role

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using AI_COMPLETE for classification | More expensive, inconsistent output format | Use AI_CLASSIFY |
| Using AI_COMPLETE to summarize across rows | Context window overflow on large datasets | Use AI_AGG or AI_SUMMARIZE_AGG (no context limit) |
| Running AI_COMPLETE on every row in a dynamic table | Re-runs on every refresh, wasting credits on unchanged data | Materialize AI results in a regular table; dynamic table aggregates |
| Not specifying `response_format` when you need structured output | LLM returns freeform text that's hard to parse | Use `response_format` with JSON schema for reliable parsing |

## References

- `primitives/ai-classify`
- `primitives/ai-extract`
- [AI_COMPLETE](https://docs.snowflake.com/en/sql-reference/functions/ai_complete)
- [AI_AGG](https://docs.snowflake.com/en/sql-reference/functions/ai_agg)
- [AI_SUMMARIZE_AGG](https://docs.snowflake.com/en/sql-reference/functions/ai_summarize_agg)

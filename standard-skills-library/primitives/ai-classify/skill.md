---
type: primitive
name: ai-classify
domain: ai-analytics
snowflake_docs: "https://docs.snowflake.com/en/sql-reference/functions/ai_classify"
---

# AI_CLASSIFY

Categorize text or images into user-defined labels. Returns one label (single-label) or multiple labels (multi-label). Runs inside Snowflake — data never leaves the account.

## Syntax

```sql
AI_CLASSIFY( input, categories [, options] )
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `input` | VARCHAR or FILE | Yes | Text, image via `TO_FILE()`, or PROMPT object |
| `categories` | ARRAY | Yes | 2-500 label strings, or objects with `label` + `description` |
| `options` | OBJECT | No | `output_mode`, `task_description`, `model`, `examples` |

### Options

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `output_mode` | STRING | `'single'` | `'single'` for one label, `'multi'` for multiple |
| `task_description` | STRING | — | Context to improve accuracy on ambiguous categories |
| `model` | STRING | — | LLM model override |
| `examples` | ARRAY | — | Few-shot examples for edge cases |

### Return Value

```json
{"labels": ["category1"]}
```

Access: `AI_CLASSIFY(...):labels[0]::VARCHAR`

For multi-label: `AI_CLASSIFY(...):labels` returns an array.

## Core Patterns

### Single-label classification

```sql
SELECT
    text_column,
    AI_CLASSIFY(text_column, ['billing', 'technical', 'account', 'feature_request']):labels[0]::VARCHAR AS category
FROM my_table;
```

### Multi-label classification

```sql
SELECT
    text_column,
    AI_CLASSIFY(text_column,
        ['technology', 'finance', 'healthcare', 'sports'],
        {'output_mode': 'multi'}
    ):labels AS tags
FROM articles;
```

### Sentiment classification

Use AI_CLASSIFY with sentiment labels instead of AI_SENTIMENT when you want categorical output rather than a numeric score.

```sql
SELECT
    review_text,
    AI_CLASSIFY(review_text, ['positive', 'negative', 'neutral']):labels[0]::VARCHAR AS sentiment
FROM reviews;
```

### With category descriptions (for ambiguous labels)

```sql
SELECT AI_CLASSIFY(text_column, [
    {'label': 'billing', 'description': 'Payment issues, invoices, charges, refunds'},
    {'label': 'technical', 'description': 'Bugs, errors, performance, integration problems'},
    {'label': 'account', 'description': 'Login, permissions, profile, account settings'}
]):labels[0]::VARCHAR AS category
FROM support_tickets;
```

### With task description

```sql
SELECT AI_CLASSIFY(text_column,
    ['urgent', 'normal', 'low'],
    {'task_description': 'Classify the priority level of this support ticket based on business impact'}
):labels[0]::VARCHAR AS priority
FROM tickets;
```

### With few-shot examples

```sql
SELECT AI_CLASSIFY(text_column,
    ['billing', 'technical', 'account'],
    {
        'examples': [
            {'input': 'I was charged twice for my subscription', 'labels': ['billing']},
            {'input': 'The API returns 500 errors', 'labels': ['technical']}
        ]
    }
):labels[0]::VARCHAR AS category
FROM tickets;
```

### Dynamic categories from a table

```sql
WITH labels AS (
    SELECT ARRAY_AGG(DISTINCT category_name) AS label_list
    FROM category_definitions
)
SELECT d.id, d.text,
    AI_CLASSIFY(d.text, l.label_list):labels[0]::VARCHAR AS category
FROM documents d, labels l;
```

## AI_FILTER — Boolean Classification

For binary yes/no questions, AI_FILTER is simpler and faster than AI_CLASSIFY with two categories.

```sql
-- Filter rows matching a natural language condition
SELECT * FROM articles
WHERE AI_FILTER(PROMPT('Does this mention data privacy? {0}', article_text));

-- Binary sentiment
SELECT text,
    CASE WHEN AI_FILTER(PROMPT('Is the sentiment positive? {0}', text))
        THEN 'positive' ELSE 'negative'
    END AS sentiment
FROM reviews;
```

## AI_SENTIMENT — Numeric Score

Returns a float from -1.0 (most negative) to 1.0 (most positive).

```sql
SELECT text, AI_SENTIMENT(text) AS score FROM reviews;
```

Use AI_SENTIMENT when you need numeric aggregation (average sentiment, trend over time). Use AI_CLASSIFY with sentiment labels when you need categorical output.

## Constraints

- 2-500 categories per call
- Categories are case-sensitive
- Image classification requires multimodal models (`pixtral-large`, `claude-3-5-sonnet`)
- Does not work with SNOWFLAKE_FULL encrypted stages
- Cannot be used in dynamic table definitions (results are non-deterministic)
- Requires SNOWFLAKE.CORTEX_USER database role

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using AI_COMPLETE for simple classification | More expensive, less consistent output format | Use AI_CLASSIFY — purpose-built and returns structured JSON |
| >20 categories without descriptions | Accuracy degrades with many ambiguous labels | Add descriptions to disambiguate, or use hierarchical classification |
| Running on full table without testing | Bad categories waste credits at scale | Test on LIMIT 5-10 first |
| Using AI_CLASSIFY for binary yes/no | Overkill for two-class problems | Use AI_FILTER instead |

## References

- `primitives/ai-extract`
- `primitives/ai-complete`
- [AI_CLASSIFY](https://docs.snowflake.com/en/sql-reference/functions/ai_classify)
- [AI_FILTER](https://docs.snowflake.com/en/sql-reference/functions/ai_filter)
- [AI_SENTIMENT](https://docs.snowflake.com/en/sql-reference/functions/ai_sentiment)

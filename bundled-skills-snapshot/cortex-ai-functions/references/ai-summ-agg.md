# AI_AGG & AI_SUMMARIZE_AGG

Aggregate text across multiple rows using natural language instructions. No context window limits.

**Docs**: 
- [AI_AGG](https://docs.snowflake.com/en/sql-reference/functions/ai_agg)
- [AI_SUMMARIZE_AGG](https://docs.snowflake.com/en/sql-reference/functions/ai_summarize_agg)

## Signature

```sql
-- AI_AGG: Custom aggregation with instruction
AI_AGG( text_expression, instruction )

-- AI_SUMMARIZE_AGG: General-purpose summarization
AI_SUMMARIZE_AGG( text_expression )
```

## Parameters

### AI_AGG

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text_expression` | VARCHAR | Yes | Column or expression containing text to aggregate |
| `instruction` | VARCHAR | Yes | Natural language description of aggregation task |

### AI_SUMMARIZE_AGG

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text_expression` | VARCHAR | Yes | Column or expression containing text to summarize |

## Returns

`VARCHAR` - Aggregated/summarized text result.

## When to Use Which

| Function | Use Case |
|----------|----------|
| `AI_SUMMARIZE_AGG` | General-purpose summary, no specific output format needed |
| `AI_AGG` | Custom analysis: extract themes, identify patterns, structured output, translations |

## Usage Patterns

### Pattern 1: Basic Summarization
Summarize text from multiple rows into a single coherent summary.

**Trigger**: "summarize", "condense", "tldr", "overview of all"

```sql
-- Simple summarization
SELECT AI_SUMMARIZE_AGG(review_text) AS summary
FROM customer_reviews;

-- With AI_AGG for more control
SELECT AI_AGG(
    review_text, 
    'Summarize the reviews for potential consumers'
) AS summary
FROM customer_reviews;
```

### Pattern 2: Summarize by Group
Aggregate text within groups (by product, date, category, etc.).

**Trigger**: "summarize per", "summary by product", "group summaries", "each category"

```sql
-- Summary per product
SELECT 
    product_id,
    AI_SUMMARIZE_AGG(review_text) AS product_summary
FROM reviews
GROUP BY product_id;

-- Summary per restaurant
SELECT 
    restaurant_id,
    AI_AGG(review, 'Summarize the restaurant reviews for potential consumers') AS summary
FROM reviews
GROUP BY restaurant_id;
```

### Pattern 3: Multi-Document Summarization
Combine multiple articles/documents into a unified summary.

**Trigger**: "combine articles", "multi-document", "news summary", "aggregate reports"

```sql
-- News article aggregation
SELECT AI_AGG(
    article_text,
    'You are provided with news articles from various publishers presenting events 
     from different points of view. Please create a concise and elaborative summary 
     of source texts without missing any crucial information.'
) AS news_summary
FROM news_articles
WHERE event_id = 'election_2024';

-- Medical literature review
SELECT AI_AGG(
    abstract,
    'You are provided with many medical articles about this disease or treatment.
     Please summarize them into one short informative sentence.
     Try to preserve the source text language and phrases.'
) AS medical_summary
FROM research_papers
GROUP BY topic;
```

### Pattern 4: Topic/Theme Extraction
Identify recurring topics, themes, or patterns across rows.

**Trigger**: "find topics", "common themes", "recurring issues", "identify patterns"

```sql
-- Extract top topics from support tickets
SELECT AI_AGG(
    ticket_text,
    'Identify the main recurring topics across the provided dataset. 
     Focus on key aspects and list only the most significant topics.
     Format the output as a bulleted list with only topic names.
     Do not provide a description of the selected topic.'
) AS top_topics
FROM support_tickets;

-- Extract satisfaction aspects from reviews
SELECT AI_AGG(
    review_text,
    'Extract 8-top-frequent distinct satisfaction aspects mentioned in customer reviews.
     Return just a list with aspects labels and nothing else.'
) AS satisfaction_aspects
FROM product_reviews;
```

### Pattern 5: Customer Segmentation
Identify customer personas or segments from feedback data.

**Trigger**: "customer segments", "personas", "user types", "audience analysis"

```sql
SELECT AI_AGG(
    review_text,
    'Identify distinct customer segments in the review data.
     Return a brief list of the personas and a short description for each.
     The categories should be specific, meaningful, not overlapping.'
) AS customer_segments
FROM customer_feedback;
```

### Pattern 6: Sentiment Aggregation
Analyze overall sentiment or sentiment distribution across rows.

**Trigger**: "overall sentiment", "sentiment breakdown", "mood across reviews"

```sql
-- Aggregate sentiment analysis
SELECT 
    product_id,
    AI_AGG(
        review_text,
        'Analyze the overall sentiment of these reviews.
         Provide: 1) Overall sentiment (positive/negative/mixed)
                  2) Key positive points mentioned
                  3) Key negative points mentioned'
    ) AS sentiment_analysis
FROM reviews
GROUP BY product_id;
```

### Pattern 7: Translation with Aggregation
Aggregate and translate content simultaneously.

**Trigger**: "translate and summarize", "multilingual summary", "translate reviews"

```sql
SELECT 
    product_id,
    AI_AGG(
        review,
        'Identify the most positive rating and translate it into French and Polish, 
         one word only'
    ) AS translated_best_review
FROM reviews
GROUP BY product_id;
```

### Pattern 8: Structured Extraction
Extract specific information in a structured format.

**Trigger**: "extract and list", "compile information", "structured output"

```sql
-- Extract action items from meeting notes
SELECT AI_AGG(
    note_text,
    'Extract all action items from the meeting notes.
     Format as a numbered list with: [Owner] - [Task] - [Due Date]'
) AS action_items
FROM meeting_notes
WHERE meeting_id = 123;

-- Compile key metrics mentioned
SELECT AI_AGG(
    report_text,
    'Extract all numerical metrics and KPIs mentioned.
     Return as JSON: {"metric_name": "value", ...}'
) AS metrics
FROM quarterly_reports;
```

### Pattern 9: Multi-Column Aggregation
Combine multiple columns before aggregating.

**Trigger**: "combine columns", "multiple fields", "menu item reviews"

```sql
-- Aggregate reviews with context
SELECT AI_SUMMARIZE_AGG(
    'Menu Item: ' || menu_item || '\nReview: ' || review
) AS menu_summary
FROM restaurant_reviews;

-- Support tickets with metadata
SELECT AI_AGG(
    'Priority: ' || priority || '\nCategory: ' || category || '\nDescription: ' || description,
    'Summarize the most critical issues requiring immediate attention'
) AS critical_issues
FROM support_tickets;
```

### Pattern 10: Comparative Analysis
Compare and contrast information across rows.

**Trigger**: "compare", "differences between", "pros and cons", "contrast"

```sql
SELECT AI_AGG(
    review_text,
    'Compare the positive and negative aspects mentioned across all reviews.
     Structure the output as:
     PROS: [list of positive points]
     CONS: [list of negative points]
     VERDICT: [overall recommendation]'
) AS comparison
FROM product_reviews
WHERE product_id = 'ABC123';
```

## Instruction Engineering Tips

1. **Be specific**: Instead of "Summarize", use "Summarize the customer reviews for a blog post targeting consumers"

2. **Break into steps**: 
   ```
   -- Instead of:
   'Summarize the news articles'
   
   -- Use:
   'You will be provided with news articles from various publishers presenting 
    events from different points of view. Please create a concise and elaborative 
    summary of source texts without missing any crucial information.'
   ```

3. **Specify output format**: "Format as a bulleted list", "Return as JSON", "One sentence only"

4. **Set constraints**: "List only the most significant topics", "Maximum 3 points"

5. **Define audience**: "for potential consumers", "for technical staff", "for executives"

## Examples by Client Question

| Client Question | Function | Instruction |
|-----------------|----------|-------------|
| "Summarize all reviews" | `AI_SUMMARIZE_AGG` | N/A (automatic) |
| "What are customers complaining about?" | `AI_AGG` | "Identify the main complaints and issues mentioned" |
| "Top themes in feedback" | `AI_AGG` | "Extract top recurring themes as a bulleted list" |
| "Summary per product" | `AI_SUMMARIZE_AGG` | N/A + `GROUP BY product_id` |
| "Customer personas" | `AI_AGG` | "Identify distinct customer segments with descriptions" |
| "Translate best review" | `AI_AGG` | "Find the most positive review and translate to Spanish" |
| "Action items from notes" | `AI_AGG` | "Extract action items as [Owner] - [Task] - [Due]" |
| "Compare pros and cons" | `AI_AGG` | "List PROS and CONS separately" |

## Performance

- **No context window limit**: Unlike `AI_COMPLETE` or `SUMMARIZE`, handles datasets larger than LLM context
- **Automatic chunking**: Data is processed in chunks and intelligently combined
- **GROUP BY support**: Efficient aggregation within groups
- **Batch processing**: Recommended for large datasets

## Access Control

Requires `SNOWFLAKE.CORTEX_USER` database role.

## Limitations

- Output is non-deterministic (LLM-generated)
- Very large aggregations may take longer to process
- Complex instructions may yield variable results

## Related Functions

- `AI_COMPLETE` - General LLM completion (context window limited)
- `SUMMARIZE` (deprecated) - Single-text summarization (context window limited)
- `AI_FILTER` - Boolean filtering instead of aggregation
- `AI_CLASSIFY` - Categorization instead of aggregation
# AI_FILTER

Boolean filter using natural language predicates on text or images.

**Docs**: [docs.snowflake.com/en/sql-reference/functions/ai_filter](https://docs.snowflake.com/en/sql-reference/functions/ai_filter)

## Signature

```sql
-- Text: Direct question/statement
AI_FILTER( predicate )

-- Text: With column input
AI_FILTER( CONCAT(instruction, text_column) )
AI_FILTER( PROMPT('instruction: {0}', text_column) )

-- Text: Multiple columns
AI_FILTER( PROMPT('{0} relates to {1}', col1, col2) )

-- Image: Single file
AI_FILTER( predicate, file_column )
AI_FILTER( PROMPT('{0} shows X', file_column) )

-- Multimodal: Text + Image
AI_FILTER( PROMPT('{0} matches {1}', text_col, file_col) )

-- With options
AI_FILTER( predicate [, options] )
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `predicate` | VARCHAR | Yes | Natural language yes/no question or statement |
| `file` | FILE | No | Image file for visual filtering (via `TO_FILE()`) |
| `options` | OBJECT | No | Configuration: `{'model': 'model-name'}` |

## Returns

`BOOLEAN` - `TRUE` if condition is met, `FALSE` otherwise.

## Usage Patterns

### Pattern 1: Direct Question (Factual)
Simple yes/no factual questions.

**Trigger**: "Is X true?", "simple facts", "verify statement"

```sql
-- Constant predicate
SELECT AI_FILTER('Is Canada in North America?');
-- Returns: TRUE

-- Column-based facts
SELECT question, AI_FILTER(question) AS is_true
FROM facts_table;
```

### Pattern 2: Sentiment Analysis
Determine positive/negative sentiment of text.

**Trigger**: "sentiment", "positive review", "negative feedback", "tone"

```sql
SELECT 
    review_text,
    CASE 
        WHEN AI_FILTER(PROMPT('Is the sentiment positive?: {0}', review_text))
        THEN 'positive' 
        ELSE 'negative' 
    END AS sentiment
FROM reviews;
```

### Pattern 3: Content Matching (Two Columns)
Check if two pieces of content relate or match.

**Trigger**: "match columns", "relate", "corresponds to", "FAQ matching", "entity matching"

```sql
-- FAQ-to-email matching
SELECT * FROM support_emails e
JOIN faqs f ON AI_FILTER(
    PROMPT('Can the FAQ {1} answer this email? {0}', e.email_text, f.faq_text)
);

-- Entity mention detection
SELECT * FROM articles
WHERE AI_FILTER(
    PROMPT('Does the text mention "{0}"? Text: {1}', entity_name, article_text)
);

-- Title-summary correspondence
SELECT * FROM documents
WHERE AI_FILTER(
    PROMPT('Does the summary {0} correspond to the title {1}?', summary, title)
);
```

### Pattern 4: Classification as Filter
Binary classification via true/false filtering.

**Trigger**: "is this category", "belongs to", "classify as yes/no"

```sql
-- Category matching
SELECT * FROM support_tickets
WHERE AI_FILTER(
    PROMPT('Does category {1} match this question? {0}', ticket_text, category)
);

-- Product matching across marketplaces
SELECT * FROM product_pairs
WHERE AI_FILTER(
    PROMPT('Are these the same product? {0} vs {1}', product_name_a, product_name_b)
);
```

### Pattern 5: Question Answering Verification
Verify if an answer is correct for a question.

**Trigger**: "correct answer", "verify answer", "is this right"

```sql
-- MMLU-style verification
SELECT question, choice,
    AI_FILTER(PROMPT(
        'Does choice {1} correctly answer: {0}?', 
        question, choice
    )) AS is_correct
FROM qa_pairs;

-- With supporting passage
SELECT * FROM qa_table
WHERE AI_FILTER(PROMPT(
    'Is the answer to "{0}" yes? Context: {1}',
    question, passage
));
```

### Pattern 6: Content Moderation
Detect policy violations, fake content, inappropriate material.

**Trigger**: "fake news", "policy violation", "inappropriate", "moderation"

```sql
-- Fake news detection
SELECT * FROM news_articles
WHERE AI_FILTER(PROMPT('Is this text fake news? {0}', article_text));

-- Policy violation
SELECT * FROM user_content
WHERE AI_FILTER(PROMPT('Does this violate content policy? {0}', content));
```

### Pattern 7: Domain-Specific Matching
Medical, financial, or specialized domain matching.

**Trigger**: "drug reaction", "medical", "financial", "ticker symbol"

```sql
-- Medical: drug reaction detection
SELECT * FROM medical_articles
WHERE AI_FILTER(PROMPT(
    'Does this article mention drug reaction {1}? Article: {0}',
    article_text, reaction_name
));

-- Financial: ticker-company matching
SELECT * FROM stock_data
WHERE AI_FILTER(PROMPT(
    'Does ticker {0} correspond to company {1}?',
    ticker, company_name
));
```

### Pattern 8: Image Filtering
Filter images by visual content.

**Trigger**: "image shows", "picture of", "visual content", "filter images"

```sql
-- Direct image question
SELECT * FROM images
WHERE AI_FILTER('Is this a picture of a cat?', TO_FILE(image_url));

-- Image with prompt template
SELECT * FROM product_images
WHERE AI_FILTER(PROMPT('{0} shows a defective product', TO_FILE(image_path)));

-- Image + text verification
SELECT * FROM listings
WHERE AI_FILTER(PROMPT(
    'Does image {0} match description {1}?',
    TO_FILE(image_url), description
));
```

### Pattern 9: Semantic JOIN
Join tables using natural language conditions.

**Trigger**: "semantic join", "fuzzy join", "match resumes to jobs"

```sql
-- Resume-job matching
SELECT r.*, j.*
FROM resumes r
JOIN jobs j ON AI_FILTER(PROMPT(
    'Does resume {0} fit job description {1}?',
    r.resume_text, j.job_description
));
```

## Prompt Engineering Tips

1. **Be explicit**: Use "Does X...?" or "Is X...?" phrasing
2. **Provide context**: Include relevant details in the prompt
3. **Use XML tags** for complex inputs: `<article>{0}</article>`
4. **Test both directions**: `{0} relates to {1}` vs `{1} answers {0}`

## Examples by Client Question

| Client Question | Pattern | SQL |
|-----------------|---------|-----|
| "Filter reviews by sentiment" | Sentiment | `WHERE AI_FILTER(PROMPT('Is positive?: {0}', review))` |
| "Find emails that match FAQs" | Content Match | `JOIN ON AI_FILTER(PROMPT('{1} answers {0}', email, faq))` |
| "Check if entity is mentioned" | Content Match | `WHERE AI_FILTER(PROMPT('Mentions "{0}"? {1}', entity, text))` |
| "Verify correct answers" | QA Verify | `WHERE AI_FILTER(PROMPT('{1} answers {0}?', q, choice))` |
| "Detect fake news" | Moderation | `WHERE AI_FILTER(PROMPT('Is fake? {0}', article))` |
| "Match products across sites" | Classification | `WHERE AI_FILTER(PROMPT('Same product? {0} vs {1}', a, b))` |
| "Filter cat pictures" | Image | `WHERE AI_FILTER('Is cat?', TO_FILE(img))` |
| "Match resumes to jobs" | Semantic JOIN | `JOIN ON AI_FILTER(PROMPT('Fits? {0} for {1}', resume, job))` |

## Performance

- **Optimization**: 2-10x speedup with automatic query optimization (Preview)
- **Batch processing**: Recommended for large datasets
- **Cascades**: Enable with `ALTER SESSION SET ENABLE_MODEL_CASCADES = true`

## Access Control

Requires `SNOWFLAKE.CORTEX_USER` database role.

## Limitations

- Does not work with `SNOWFLAKE_FULL` encrypted internal stages
- Does not work with customer-side encrypted external stages
- Image support requires multimodal-capable models (e.g., `pixtral-large`)

## Related Functions

- `AI_CLASSIFY` - Multi-category classification (vs binary)
- `AI_SENTIMENT` - Returns numeric score (-1 to 1) instead of boolean
- `AI_EXTRACT` - Extract structured data instead of filtering
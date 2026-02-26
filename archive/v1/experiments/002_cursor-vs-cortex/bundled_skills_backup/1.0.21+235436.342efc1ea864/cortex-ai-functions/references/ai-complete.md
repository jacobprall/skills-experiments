# AI_COMPLETE

Execute AI completions with LLMs. Supports text prompts and vision (image analysis).

**Docs**: [docs.snowflake.com/en/sql-reference/functions/ai_complete](https://docs.snowflake.com/en/sql-reference/functions/ai_complete)

## ⚠️ CRITICAL: Always Display Pricing Before Execution

**Before executing ANY AI_COMPLETE call, you MUST inform the user of the estimated cost.**

### Model for Visual Analysis: `claude-3-5-sonnet`

For visual analysis (charts, diagrams, blueprints), use **claude-3-5-sonnet**. It provides the best capability for image understanding tasks.

### Pricing (Credits per Million Tokens)

| Token Type | Credits |
|------------|---------|
| Input      | 1.50    |
| Output     | 7.50    |

**Source**: [Snowflake Service Consumption Table](https://www.snowflake.com/legal-files/CreditConsumptionTable.pdf)

### Cost Formula

```
cost = (input_tokens × 1.50 + output_tokens × 7.50) / 1,000,000

Rule of thumb: ~4 characters ≈ 1 token
```

### Example Estimates for claude-3-5-sonnet

| Scenario | Input Tokens | Output Tokens | Credits |
|----------|--------------|---------------|---------|
| Single image analysis | 1,500 | 500 | ~0.006 |
| Chart data extraction | 2,000 | 1,000 | ~0.011 |
| Blueprint analysis | 3,000 | 2,000 | ~0.020 |
| Batch (100 images) | 200,000 | 100,000 | ~1.05 |

**Reference**: [Snowflake Service Consumption Table](https://www.snowflake.com/legal-files/CreditConsumptionTable.pdf)

## Signatures

```sql
-- Text completion (simple)
AI_COMPLETE( model, prompt )

-- Text completion (with options)
AI_COMPLETE( model, prompt, options )

-- Single image analysis
AI_COMPLETE( model, prompt, file [, options] )

-- Multi-turn / multi-image conversation
AI_COMPLETE( model, conversation, options )
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | STRING | Yes | Model name (see supported models) |
| `prompt` | STRING | Yes* | Text prompt for completion |
| `file` | FILE | No | Image file via `TO_FILE()` for vision |
| `conversation` | ARRAY | Yes* | Array of message objects for multi-turn |
| `options` | OBJECT | No | Configuration options |

*One of `prompt` or `conversation` required.

### Options Object

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_tokens` | INT | 4096 | Maximum tokens in response |
| `temperature` | FLOAT | 0.0 | Randomness (0.0 = deterministic) |
| `top_p` | FLOAT | 1.0 | Nucleus sampling threshold |
| `response_format` | OBJECT | - | Structured JSON output schema |
| `guardrails` | BOOLEAN | true | Enable content safety filters |

## Supported Models

### Vision-Capable Models (for image analysis)

| Model | Provider | Best For |
|-------|----------|----------|
| `claude-4-opus` | Anthropic | Complex visual reasoning |
| `claude-4-sonnet` | Anthropic | Balanced quality/speed |
| `claude-3-7-sonnet` | Anthropic | General purpose |
| `claude-3-5-sonnet` | Anthropic | General purpose (recommended) |
| `llama4-maverick` | Meta | Fast, cost-effective |
| `llama4-scout` | Meta | Fast, cost-effective |
| `openai-o4-mini` | OpenAI | Reasoning tasks |
| `openai-gpt-4.1` | OpenAI | General purpose |
| `pixtral-large` | Mistral | Visual analysis |

### Text-Only Models

| Model | Provider | Best For |
|-------|----------|----------|
| `claude-3-5-sonnet` | Anthropic | General purpose |
| `llama3.3-70b` | Meta | Open-source, fast |
| `mistral-large2` | Mistral | European deployment |
| `deepseek-r1` | DeepSeek | Reasoning |

## Constraints

| Constraint | Limit |
|------------|-------|
| Max image size | 10 MB (3.75 MB for Claude models) |
| Max resolution | 8000×8000 pixels (Claude) |
| Max tokens output | Model-dependent (typically 4096-8192) |

**Stage Requirements:**
- Server-side encryption must be enabled
- Does NOT work with `TYPE = 'SNOWFLAKE_FULL'` or client-side encryption

## Usage Patterns

### Pattern 1: Basic Text Completion

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    'Summarize this text: ' || my_text_column
) AS summary
FROM my_table;
```

### Pattern 2: Single Image Analysis

Analyze one image file directly.

**Trigger**: "analyze chart", "extract from image", "what's in this picture", "read diagram"

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    'Analyze this chart and extract all data points.',
    TO_FILE('@db.schema.stage', 'chart.png')
) AS analysis;
```

### Pattern 3: Single Image with Options

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    'Extract all dimensions and measurements from this blueprint.',
    TO_FILE('@stage', 'blueprint.png'),
    {'max_tokens': 4096, 'temperature': 0}
) AS analysis;
```

### Pattern 4: Structured JSON Output

Get consistent JSON responses.

**Trigger**: "extract as JSON", "structured output", "parse into fields"

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    'Extract chart data from this image.',
    TO_FILE('@stage', 'chart.png'),
    {
        'response_format': {
            'type': 'json',
            'schema': {
                'type': 'object',
                'properties': {
                    'chart_type': {'type': 'string'},
                    'title': {'type': 'string'},
                    'data_points': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'label': {'type': 'string'},
                                'value': {'type': 'number'}
                            }
                        }
                    }
                },
                'required': ['chart_type', 'data_points']
            }
        }
    }
) AS structured_result;
```

### Pattern 5: Multi-Turn Conversation

Complex interactions with context.

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    [
        {'role': 'system', 'content': 'You are a document analysis expert.'},
        {'role': 'user', 'content': 'Analyze this technical drawing.'},
        {'role': 'assistant', 'content': 'I see a mechanical assembly with several components.'},
        {'role': 'user', 'content': 'What are the dimensions?'}
    ],
    {'max_tokens': 4096}
) AS response;
```

### Pattern 6: Multi-Image Analysis (Conversation Format)

Analyze multiple images in one call.

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    [
        {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': 'Compare these two charts.'},
                {'type': 'image_url', 'image_url': {'url': TO_FILE('@stage', 'chart1.png')}},
                {'type': 'image_url', 'image_url': {'url': TO_FILE('@stage', 'chart2.png')}}
            ]
        }
    ],
    {'max_tokens': 4096}
) AS comparison;
```

### Pattern 7: Batch Image Analysis

Process all images in a stage.

**Trigger**: "analyze all images", "batch visual analysis"

```sql
-- DDL uses stage name without @
ALTER STAGE db.schema.stage SET DIRECTORY = (ENABLE = TRUE);
ALTER STAGE db.schema.stage REFRESH;

SELECT 
    relative_path,
    AI_COMPLETE(
        'claude-3-5-sonnet',
        'Extract all data from this chart.',
        TO_FILE('@db.schema.stage', relative_path)
    ) AS analysis
FROM DIRECTORY(@db.schema.stage)
WHERE relative_path ILIKE '%.png' OR relative_path ILIKE '%.jpg';
```

### Pattern 8: Chain with AI_PARSE_DOCUMENT

Parse document then analyze with AI_COMPLETE.

**Trigger**: "summarize document", "analyze PDF content"

```sql
WITH parsed AS (
    SELECT AI_PARSE_DOCUMENT(
        TO_FILE('@stage', 'report.pdf'),
        {'mode': 'LAYOUT'}
    ):content::STRING AS text
)
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    'Extract key insights from this document:\n\n' || text
) AS insights
FROM parsed;
```

## Visual Analysis Prompts by Content Type

### Charts & Graphs

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    'Analyze this chart:
1. Chart type (bar, line, pie, etc.)
2. Title and axis labels
3. All data points with exact values
4. Key trends or insights
5. Any annotations or legends

Format data points as a table.',
    TO_FILE('@stage', 'chart.png')
) AS chart_analysis;
```

### Blueprints & Technical Drawings

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    'Analyze this technical drawing:
1. All labeled components and parts
2. Dimensions and measurements with units
3. Materials specifications if shown
4. Scale information
5. Assembly notes or instructions
6. Any warnings or special callouts',
    TO_FILE('@stage', 'blueprint.png')
) AS blueprint_analysis;
```

### Diagrams & Flowcharts

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    'Analyze this diagram:
1. Overall purpose
2. All nodes/boxes and their labels
3. Connections and relationships
4. Flow direction and sequence
5. Decision points and branches
6. Start and end points',
    TO_FILE('@stage', 'diagram.png')
) AS diagram_analysis;
```

### General Visual Analysis

```sql
SELECT AI_COMPLETE(
    'claude-3-5-sonnet',
    'Describe this image in detail. Include all visible text, numbers, symbols, and visual elements.',
    TO_FILE('@stage', 'image.png')
) AS description;
```

## Error Cases & Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `File not found` | Invalid stage path or filename | Verify stage and file exist |
| `Image too large` | Exceeds size limit | Resize image or reduce DPI |
| `Unsupported format` | Non-image file with vision | Use supported image format (PNG, JPG, etc.) |
| `Model not available` | Invalid model name | Check supported models list |

## Access Control

```sql
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE my_role;
```

## Limitations

- Vision requires image files (PNG, JPG, TIFF, etc.) - not PDF/DOCX directly
- PDFs must be converted to images for visual analysis
- Dynamic tables not supported
- Output is non-deterministic (LLM-generated)
- Image size limits vary by model

## When to Use vs Other Functions

| Scenario | Recommended Function |
|----------|---------------------|
| Extract specific fields from document | AI_EXTRACT |
| Get full text from document | AI_PARSE_DOCUMENT |
| Analyze charts, blueprints, diagrams | **AI_COMPLETE** (vision) |
| Extract data from engineering drawings | **AI_COMPLETE** (vision) |
| Summarize parsed document text | **AI_COMPLETE** (text) |
| Custom analysis on parsed text | **AI_COMPLETE** (text) |

## Related Functions

- `AI_EXTRACT` - Structured field extraction from documents
- `AI_PARSE_DOCUMENT` - Full document text extraction
- `AI_CLASSIFY` - Categorize text/documents
- `AI_FILTER` - Binary yes/no filtering
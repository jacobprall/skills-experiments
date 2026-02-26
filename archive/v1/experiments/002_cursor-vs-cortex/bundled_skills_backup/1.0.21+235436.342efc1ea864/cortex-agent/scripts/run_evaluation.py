#!/usr/bin/env python3
"""
Run evaluation questions against an agent and compare to expected answers.

EVALUATION SOURCES:
    - Snowflake table/view name
    - SQL query (must start with SELECT)

REQUIRED COLUMNS:
    - question: The question text to ask the agent
    - expected_answer: The expected answer for comparison

OUTPUT:
    Creates a directory with individual responses and evaluation_summary.json
"""

import argparse
import json
import snowflake.connector
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from test_agent import test_agent
from datetime import date, datetime


NUM_THREADS = 8


def evaluate_answer(question, expected_answer, actual_answer, conn):
    """
    Use modified insight eval LLM judge prompt to evaluate an agent's answer compared to ground truth.
    
    Returns:
        dict: {"is_correct": bool, "score": float, "reasoning": str}
    """
    if not actual_answer or not actual_answer.strip():
        return {
            "is_correct": False,
            "score": 0.0,
            "reasoning": "No answer provided by agent"
        }
    
    evaluation_prompt = f"""You are a pragmatic and results-oriented expert data analyst. Your task is to act as a judge, evaluating a data analytics response. Your entire evaluation is governed by a single principle: **the business value and correctness of the final answer are what matter most.**

---

[Inputs]

QUESTION: {question}
EXPECTED ANSWER GUIDELINES: {expected_answer}
RESPONSE ANSWER: {actual_answer}

---

[The Golden Rule: Outcome Over Method]

This is the most critical instruction. **A response that arrives at the correct and actionable business answer using a logically sound, alternative method is a perfect-score response (Rating 1).** Do not penalize a response for deviating from the REFERENCE SQL(S) if its own method is valid and successfully answers the user's QUESTION. Your primary job is to assess the final result, not to enforce a specific implementation.

The EXPECTED ANSWER GUIDELINES are **one example of a correct solution, not the only one.** Use them as a benchmark to validate the correctness of the RESPONSE ANSWER, but not as a rigid checklist for the methodology.

---

[Evaluation Process]

Follow these steps in order:

**Step 1: Evaluate the Final Answer's Correctness and Utility.**
First, look only at the RESPONSE ANSWER. Does it directly and accurately answer the user's QUESTION? Does it align with the key findings in the EXPECTED ANSWER GUIDELINES?
* If the answer is factually correct, complete, and provides clear business value, it is a strong candidate for a **Rating 2**. Proceed to Step 2 to validate the methodology.
* If the answer is factually incorrect, misleading, or misses the core business goal, it is a **Rating 0**.

**Step 2: Determine the Final Rating.**
Synthesize your findings into a final rating.

* **2 - CORRECT (Full Points):** The RESPONSE ANSWER is correct, complete, and valuable. The analytical method used was logically sound, *even if it differed from the reference solution.*
* **1 - PARTIALLY CORRECT (Partial Points):** The RESPONSE ANSWER is on the right track but contains minor factual errors, is incomplete, or the methodology has small flaws that detract from the overall quality but don't invalidate the entire result.
* **0 - INCORRECT (No Points):** The RESPONSE ANSWER is factually wrong, misleading, or irrelevant. The methodology is fundamentally flawed.

---

[Common Pitfalls to Avoid]

* **Method Fixation:** Do not downgrade a response simply because it didn't use the exact SQL, functions, or tables listed in the EXPECTED ANSWER GUIDELINES.
* **Ignoring Equivalency:** Recognize that different metrics can often serve as valid proxies for each other (e.g., utilization rate vs. run-rate comparison). If the proxy is logical and yields the right result, the response is correct.

---

[Output]

Respond with ONLY a JSON object in this exact format:
{{"is_correct": true/false, "score": 0.0-2.0, "reasoning": "explanation"}}"""
    
    try:
        cursor = conn.cursor()
        
        query = """
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'claude-sonnet-4-5',
            %s
        ) as evaluation
        """
        cursor.execute(query, (evaluation_prompt,))
        result = cursor.fetchone()[0]
        cursor.close()
        
        # Extract JSON from response (LLM might add extra text)
        result = result.strip()
        
        # Find JSON object in response
        start = result.find('{')
        end = result.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = result[start:end]
            evaluation = json.loads(json_str)
            return evaluation
        else:
            raise ValueError(f"No JSON object found in response: {result}")
            
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON parse error: {e}")
        print(f"Response was: {result[:200]}")
        return {
            "is_correct": False,
            "score": 0.0,
            "reasoning": f"JSON parse error: {str(e)}"
        }
    except Exception as e:
        print(f"⚠️  Evaluation failed: {e}")
        return {
            "is_correct": False,
            "score": 0.0,
            "reasoning": f"Evaluation error: {str(e)}"
        }


def fetch_evaluation_questions(source, connection_name="snowhouse"):
    """
    Fetch evaluation questions from a Snowflake table or query.
    
    This function automatically detects whether the source is a table name or SQL query:
    - If source starts with "SELECT", it's treated as a SQL query
    - Otherwise, it's treated as a table name and wrapped in "SELECT * FROM ..."
    
    Args:
        source (str): Either a fully qualified table name (e.g., "db.schema.table")
                     or a SQL query (e.g., "SELECT question, expected_answer FROM ...")
        connection_name (str): Snowflake connection name (default: "snowhouse")
        
    Returns:
        list[dict]: List of question dictionaries, each containing:
                   - question (str): The question text
                   - expected_answer (str): The expected answer
                   - Plus any optional metadata fields present in the source
        
    Raises:
        ValueError: If required columns 'question' or 'expected_answer' are missing
        
    Example:
        # From a table:
        questions = fetch_evaluation_questions("my_db.my_schema.eval_table")
        
        # From a query:
        questions = fetch_evaluation_questions(
            "SELECT question, expected_answer FROM my_table WHERE category = 'finance'"
        )
    """
    conn = snowflake.connector.connect(connection_name=connection_name)
    try:
        cursor = conn.cursor()
        
        # Determine if source is a table name or query
        if source.strip().upper().startswith("SELECT"):
            sql = source
            print("Executing custom query...")
        else:
            sql = f"SELECT * FROM {source}"
            print(f"Fetching from table: {source}")
        
        cursor.execute(sql)
        
        # Get column names from cursor description (case-insensitive)
        column_names = [desc[0].lower() for desc in cursor.description]
        print(f"Columns found: {', '.join(column_names)}")
        
        # Validate required columns
        if 'question' not in column_names:
            raise ValueError(
                f"Required column 'question' not found in result set. "
                f"Available columns: {column_names}"
            )
        if 'expected_answer' not in column_names:
            raise ValueError(
                f"Required column 'expected_answer' not found in result set. "
                f"Available columns: {column_names}"
            )
        
        # Build questions list
        questions = []
        for row in cursor.fetchall():
            # Create dict from row data
            row_dict = dict(zip(column_names, row))
            
            # Extract required fields
            question_data = {
                "question": row_dict["question"],
                "expected_answer": row_dict["expected_answer"]
            }
            
            # Add optional fields if present (common metadata columns)
            optional_fields = [
                "tool_used", "author", "date_added", 
                "category", "difficulty", "id", "question_id", "enable_research_mode", "current_date_override"
            ]
            for field in optional_fields:
                if field in row_dict:
                    value = row_dict[field]
                    # Convert date objects to strings for JSON serialization
                    if isinstance(value, (date, datetime)):
                        value = value.isoformat()
                    question_data[field] = value
            
            questions.append(question_data)
        
        return questions
    finally:
        cursor.close()
        conn.close()


def run_evaluation(agent_name, database, schema, eval_source, output_dir, connection_name="snowhouse"):
    """
    Run all evaluation questions against an agent and save results.
    
    This function:
    1. Fetches questions from the evaluation source (table or query)
    2. Runs each question through the agent via test_agent()
    3. Evaluates answers using LLM-as-a-judge
    4. Saves individual responses as JSON files (q01_response.json, q02_response.json, etc.)
    5. Creates a summary JSON with all results
    
    Args:
        agent_name (str): Name of the agent to evaluate
        database (str): Database where agent is located
        schema (str): Schema where agent is located
        eval_source (str): Table name or SQL query for evaluation questions
        output_dir (str): Directory to save evaluation results
        connection_name (str): Snowflake connection name (default: "snowhouse")
        
    Returns:
        list[dict]: List of result dictionaries containing:
                   - question_number: Sequential number (1-N)
                   - question: The question text
                   - expected_answer: Expected answer
                   - actual_answer: Agent's actual answer
                   - response_file: Path to detailed response JSON
                   - is_correct: Whether answer is correct (LLM-judged)
                   - score: Correctness score (0.0-1.0)
                   - reasoning: Evaluation reasoning
                   - Plus any metadata from evaluation source
    
    Output Structure:
        <output_dir>/
        ├── q01_response.json       # Full response for question 1
        ├── q02_response.json       # Full response for question 2
        ├── ...
        └── evaluation_summary.json # Summary of all results
        
    Example:
        results = run_evaluation(
            agent_name="AIOBS_PDS_AGENT",
            database="TEMP",
            schema="NVYTLA",
            eval_source="snowscience.semantic_views.pds_agent_eval",
            output_dir="./eval_results",
            connection_name="snowhouse"
        )
        print(f"Correct: {sum(1 for r in results if r['is_correct'])}/{len(results)}")
    """
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Fetch questions from source
    print("="*80)
    questions = fetch_evaluation_questions(eval_source, connection_name)
    print(f"Found {len(questions)} evaluation questions\n")
    
    # Create connection for evaluations
    eval_conn = snowflake.connector.connect(connection_name=connection_name)
    
    # Helper function to process a single question
    def process_question(i, q):
        """Process a single evaluation question."""
        print(f"\n{'='*80}")
        print(f"Question {i}/{len(questions)}")
        print(f"{'='*80}")
        
        question_text = q["question"]
        expected = q["expected_answer"]
        
        # Save response to file (q01_response.json, q02_response.json, etc.)
        response_file = output_path / f"q{i:02d}_response.json"
        
        # Print metadata if available
        if "tool_used" in q:
            print(f"Tool: {q['tool_used']}")
        if "category" in q:
            print(f"Category: {q['category']}")
        if "difficulty" in q:
            print(f"Difficulty: {q['difficulty']}")
        if "enable_research_mode" in q:
            print(f"Enable research mode: {q['enable_research_mode']}")
        if "current_date_override" in q:
            print(f"Current date override: {q['current_date_override']}")
        print(f"Expected: {expected[:100]}...")
        print()
        
        # Run the question through test_agent
        response = test_agent(
            agent_name=agent_name,
            question=question_text,
            output_file=str(response_file),
            database=database,
            schema=schema,
            connection_name=connection_name,
            enable_research_mode=q.get("enable_research_mode", False),
            current_date_override=q.get("current_date_override", None),
        )
        
        # Extract actual answer from response (text, charts, and tables)
        actual_answer_parts = []
        if response and 'content' in response:
            for item in response['content']:
                item_type = item.get('type')
                if item_type == 'text':
                    actual_answer_parts.append(item['text'])
                elif item_type == 'chart':
                    # Include raw chart spec for evaluation
                    chart_info = item.get('chart', {})
                    chart_spec = chart_info.get('chart_spec', '{}')
                    actual_answer_parts.append(f"[CHART: {chart_spec}]")
                elif item_type == 'table':
                    # Format table data in a readable way for evaluation
                    table_info = item.get('table', {})
                    title = table_info.get('title', 'Table')
                    result_set = table_info.get('result_set', {})
                    
                    # Extract column names from metadata
                    metadata = result_set.get('resultSetMetaData', {})
                    row_types = metadata.get('rowType', [])
                    columns = [col.get('name', f'col_{i}') for i, col in enumerate(row_types)]
                    
                    # Format as markdown table
                    data = result_set.get('data', [])
                    if columns and data:
                        table_lines = [f"**{title}**"]
                        table_lines.append("| " + " | ".join(columns) + " |")
                        table_lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
                        for row in data:
                            table_lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
                        actual_answer_parts.append("\n".join(table_lines))
                    else:
                        actual_answer_parts.append(f"[TABLE: {title}]")
        actual_answer = "\n\n".join(actual_answer_parts)
        
        # Evaluate answer using LLM judge
        evaluation = evaluate_answer(question_text, expected, actual_answer, eval_conn)
        
        # Build result dict with all available metadata
        result = {
            "question_number": i,
            "question": question_text,
            "expected_answer": expected,
            "actual_answer": actual_answer,
            "response_file": str(response_file),
            "is_correct": evaluation["is_correct"],
            "score": evaluation["score"],
            "reasoning": evaluation["reasoning"]
        }
        
        # Add optional metadata fields from source
        for field in ["tool_used", "author", "date_added", "category", "difficulty", "id", "question_id"]:
            if field in q:
                result[field] = q[field]
        
        return result
    
    results = [None] * len(questions)
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        future_to_index = {
            executor.submit(process_question, i, q): i-1
            for i, q in enumerate(questions, 1)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results[index] = result
            except Exception as e:
                print(f"\n⚠️  Error processing question {index + 1}: {e}")
                results[index] = {
                    "question_number": index + 1,
                    "question": questions[index]["question"],
                    "expected_answer": questions[index]["expected_answer"],
                    "actual_answer": "",
                    "response_file": str(output_path / f"q{index+1:02d}_response.json"),
                    "is_correct": False,
                    "score": 0.0,
                    "reasoning": f"Error: {str(e)}",
                    "error": str(e)
                }
    
    # Close evaluation connection
    eval_conn.close()
    
    # Save summary of all results
    summary_file = output_path / "evaluation_summary.json"
    with open(summary_file, 'w') as f:
        try:
            json.dump(results, f, indent=2)
        except Exception as e:
            print(f"Error saving summary: {e}")
            print(f"Results: {results}")
            f.write(results)
            raise e
    
    # Print completion summary
    print(f"\n{'='*80}")
    print("EVALUATION COMPLETE")
    print(f"{'='*80}")
    print(f"Results saved to: {output_dir}")
    print(f"Summary: {summary_file}")
    
    correct = sum(1 for r in results if r["is_correct"])
    total_score = sum(r["score"] for r in results)
    avg_score = total_score / len(results) if results else 0.0
    
    print(f"\nCorrect answers: {correct}/{len(results)} ({100*correct/len(results):.1f}%)")
    print(f"Average score: {avg_score:.2f}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run evaluation questions against an agent and compare to expected answers",
        epilog="""
Examples:
  # Using a table:
  %(prog)s --agent-name MY_AGENT --database TEMP --schema NVYTLA --eval-source my_db.my_schema.eval_table

  # Using a SQL query:
  %(prog)s --agent-name MY_AGENT --database TEMP --schema NVYTLA --eval-source "SELECT * FROM eval_table WHERE category = 'finance'"

  # With custom output directory:
  %(prog)s --agent-name MY_AGENT --database TEMP --schema NVYTLA --eval-source eval_table --output-dir ./my_results

Required columns: question, expected_answer
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--agent-name", required=True, help="Name of the agent to evaluate")
    parser.add_argument("--database", required=True, help="Database where agent is located")
    parser.add_argument("--schema", required=True, help="Schema where agent is located")
    parser.add_argument("--eval-source", required=True, help="Table name or SQL query for evaluation questions")
    parser.add_argument("--output-dir", help="Directory for results (default: ./eval_<agent_name>)")
    parser.add_argument("--connection", default="snowhouse", help="Snowflake connection name (default: snowhouse)")
    
    args = parser.parse_args()
    
    output_dir = args.output_dir or f"./eval_{args.agent_name}"
    
    print("\nAgent Evaluation")
    print(f"{'='*80}")
    print(f"Agent: {args.database}.{args.schema}.{args.agent_name}")
    print(f"Evaluation Source: {args.eval_source if len(args.eval_source) < 60 else args.eval_source[:60] + '...'}")
    print(f"Output Directory: {output_dir}")
    print(f"Connection: {args.connection}")
    print(f"{'='*80}\n")
    
    run_evaluation(args.agent_name, args.database, args.schema, args.eval_source, output_dir, args.connection)

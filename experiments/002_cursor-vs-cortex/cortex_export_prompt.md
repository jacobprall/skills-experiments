# Cortex Code CLI — Transcript Export Prompt

Paste this at the end of each Cortex Code test session. Replace `T1` with the test number.

---

**Prompt:**

> Before we wrap up, I need you to write the full transcript of our conversation to a file. Write it as JSONL (one JSON object per line) to the file `experiments/002_cursor-vs-cortex/logs/T1_cortex.jsonl`.
>
> Use this exact format — one line per message, in chronological order:
>
> ```
> {"role": "user", "message": {"content": [{"type": "text", "text": "the user message"}]}}
> {"role": "assistant", "message": {"content": [{"type": "text", "text": "the assistant response"}]}}
> ```
>
> Include every message in our conversation — your reasoning, all SQL you ran, all tool calls and their results, and all of your responses. Do not summarize or truncate. Each message should be its own line.

---

**File naming convention:**

| Test | Cursor (Arm B) | Cortex Code (Arm A) |
|------|-----------------|---------------------|
| T1 | `logs/T1_cursor.jsonl` | `logs/T1_cortex.jsonl` |
| T2 | `logs/T2_cursor.jsonl` | `logs/T2_cortex.jsonl` |
| T3 | `logs/T3_cursor.jsonl` | `logs/T3_cortex.jsonl` |
| T4 | `logs/T4_cursor.jsonl` | `logs/T4_cortex.jsonl` |
| T5 | `logs/T5_cursor.jsonl` | `logs/T5_cortex.jsonl` |
| T6 | `logs/T6_cursor.jsonl` | `logs/T6_cortex.jsonl` |

For Cursor transcripts, copy the `.jsonl` from `~/.cursor/projects/.../agent-transcripts/` and rename to match.

**Analyze:**

```bash
# Single transcript
python analyze_transcript.py logs/T1_cortex.jsonl --arm cortex --test T1

# Compare arms
python analyze_transcript.py --compare logs/T1_cursor.jsonl logs/T1_cortex.jsonl --test T1
```

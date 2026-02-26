# Experiment 001: Bundled Skills vs. Standard Skills Library

**Date:** 2025-02-24 / 2025-02-25
**Operator:** JPRALL
**Cortex Code Version:** 1.0.20 / 1.0.21
**Model:** Claude (Anthropic)

---

## TL;DR

We compared two skill architectures for Cortex Code — Snowflake's AI agent CLI — across three progressively complex Snowflake tasks. The **Standard Skills Library** (17 structured markdown files in a 4-layer DAG) matched or outperformed **137 pre-bundled skill files** on every metric that matters to a business user: outcome correctness (+8%), human interventions (-75%), and average time (-18%).

The most surprising finding: skill descriptions embedded in the system prompt influenced agent behavior even when the full skills were never loaded.

---

## Background

### What is Cortex Code?

Cortex Code is Snowflake's CLI-based AI agent. It connects to a Snowflake account, takes natural-language instructions, and executes multi-step workflows — writing SQL, creating objects, deploying apps. It ships with **bundled skills**: markdown files that get loaded into the agent's context when triggered by keywords in the user's prompt.

### The Problem

Bundled skills are authored independently by product teams. This produces:
- **Overlapping scope** — 3 separate skills cover data security (`data-policy`, `data-governance`, `sensitive-data-classification`)
- **Bloated context** — some skills exceed 6,000 lines; the dynamic-tables skill spans 15 files totaling 4,722 lines
- **No cross-domain orchestration** — a task spanning security + transformation + app deployment loads 3 independent skills with no coordination

### The Hypothesis

A **structured library** — organized as a DAG with explicit routing, playbooks, and primitives — would produce more reliable agent behavior than a collection of independent reference documents, even with significantly less material.

### Standard Skills Library Architecture

```
meta-router → domain routers → playbooks → primitives
```

- **Meta-router:** Decomposes multi-domain requests, topologically sorts execution order
- **Domain routers** (3): data-security, data-transformation, app-deployment
- **Playbooks** (3): Step-by-step workflows (secure-sensitive-data, build-streaming-pipeline, build-react-app)
- **Primitives** (10): Atomic Snowflake operations (dynamic-tables, masking-policies, SYSTEM$CLASSIFY, etc.)

Total: **17 files, ~2,400 lines** (vs. 137 files, ~50,000+ lines for bundled skills)

---

## Methodology

### Test Design

Two arms, three tests each. Same prompts, same Snowflake account, same data, same operator.

| Test | Domains | Complexity | Prompt Style |
|------|---------|-----------|--------------|
| **T1: Basic** | Security only | Single domain | Conversational, mentions PII |
| **T2: Moderate** | Transformation + Security | Two domains | Mentions pipeline + PII |
| **T3: End-to-End** | Transform + Security + App | Three domains | Deliberately ambiguous |

**Arm A (Control):** Original bundled skills (137 SKILL.md files across 23 directories)
**Arm B (Treatment):** Standard Skills Library content injected into the bundled skill directories (content replacement — same trigger names, different loaded content)

### Metrics

| Metric | What It Measures |
|--------|-----------------|
| **Time to done** | Wall-clock from first prompt to verified completion |
| **Human interventions** | Corrections, re-prompts, clarifications by operator |
| **Outcome correctness** | % of ground-truth checklist items passed |
| **Skills loaded** | Number of skills invoked by the agent |

### Ground-Truth Checklists

- **T1 (6 items):** SYSTEM$CLASSIFY run, PII identified, masking policies with IS_ROLE_IN_SESSION(), policies applied, masking verified both directions
- **T2 (10 items):** Dynamic table with correct lag, aggregation correct, change tracking, SYSTEM$CLASSIFY, masking applied, pipeline verified, masking verified
- **T3 (14 items):** All of T2 + Streamlit/React dashboard created, connects to data, renders charts, runs without errors

### Constraints

- **N=1 per cell** — each test ran once per arm (proof-of-concept, not powered study)
- **Same operator** for both arms (not blinded)
- **Skill description leakage** — modified `<available_skills>` descriptions in the system prompt contained standard library patterns, influencing B-arm behavior even without skill loading

---

## Results

### Scorecard

| Test | Arm A Time | A Interventions | A Score | Arm B Time | B Interventions | B Score |
|------|-----------|----------------|---------|-----------|----------------|---------|
| T1: Basic Security | 14.5 min | 2 | 4/6 (67%) | 5 min | 1 | 6/6 (100%) |
| T2: Moderate | 8 min | 0 | 8/10 (80%) | 9 min | 0 | 8/10 (80%) |
| T3: End-to-End | 13 min | 2 | 11/14 (79%) | 15 min | 0 | 11/14 (79%) |
| **Totals** | **35.5 min** | **4** | **23/30 (77%)** | **29 min** | **1** | **25/30 (83%)** |

### Aggregate Comparison

| Metric | Arm A (Bundled) | Arm B (Standard Library) | Delta |
|--------|----------------|--------------------------|-------|
| Total score | 23/30 (77%) | 25/30 (83%) | **+8%** |
| Total interventions | 4 | 1 | **-75%** |
| Average time | 11.8 min | 9.7 min | **-18%** |
| Skills loaded (total) | 6 | 2 | **-67%** |
| Skill content loaded (est.) | ~16,500 lines | ~867 lines | **-95%** |

---

## Findings

### 1. Structured playbooks beat comprehensive references — when loaded

The clearest signal: **T1 (Basic Security)**.

| | A1 | B1 |
|---|---|---|
| Score | 67% | **100%** |
| Time | 14.5 min | **5 min** |
| Interventions | 2 | **1** |
| Skill loaded | sensitive-data-classification (712 lines) | data-security (561 lines) |

B1 followed the playbook's prescribed flow: discover → classify → review → create policies → apply → verify. A1 loaded the classification skill but had to improvise masking without `data-policy` guidance — the bundled architecture splits classify and mask across two independent skills, and A1 only loaded one.

The structural advantage: a playbook prescribes the **complete workflow**, not just domain knowledge.

### 2. Skill descriptions function as behavioral primers

The most surprising result: **B2 loaded zero skills** yet produced results nearly identical to A2 (which loaded 2 skills totaling ~6,783 lines).

Despite not loading any skills, the B2 agent still used:
- Split-pattern masking (one policy per data type)
- `IS_ROLE_IN_SESSION()` (correct function)
- Plan-mode with clear step sequencing

These patterns appear in the modified `<available_skills>` descriptions — short text strings the agent reads on every turn. Skill descriptions are not just routing metadata; they are **lightweight behavioral primers** that deliver a meaningful fraction of a skill's value without the full content ever being loaded.

**Implication:** The description field in a skill registry deserves as much design attention as the skill content itself.

### 3. Fewer interventions across the board

| Test | A Interventions | B Interventions | What B avoided |
|------|----------------|-----------------|----------------|
| T1 | 2 | 1 | Agent proactively investigated roles instead of assuming |
| T2 | 0 | 0 | — |
| T3 | 2 | 0 | Found correct tables immediately; no CLI rejection needed |
| **Total** | **4** | **1** | |

The playbook structure appears to encourage more **methodical behavior** (investigate before acting), reducing the need for human course-correction.

### 4. Less material loaded, comparable or better outcomes

| Test | A: Skills Loaded | A: Material (est.) | B: Skills Loaded | B: Material (est.) |
|------|-----------------|-------------------|-----------------|-------------------|
| T1 | 1 | ~712 lines | 1 | ~561 lines |
| T2 | 2 | ~6,783 lines | 0 | 0 lines |
| T3 | 3 | ~9,000+ lines | 1 | ~306 lines |
| **Total** | **6** | **~16,500 lines** | **2** | **~867 lines** |

B-arm loaded **95% less skill content** while scoring 8% higher overall. More reference material does not necessarily improve agent performance. The playbook approach provides the *right instructions at the right moment* rather than comprehensive coverage.

### 5. Both arms failed on the same environmental issue

The Snowflake account's role hierarchy (`SNOWFLAKE_LEARNING_ADMIN_ROLE` granted TO `SNOWFLAKE_LEARNING_ROLE`) caused masking verification to fail when agents gated policies on `SNOWFLAKE_LEARNING_ADMIN_ROLE`. Neither arm's agent discovered this without being told.

B1 and B3 independently chose roles (ACCOUNTADMIN, SYSADMIN) that avoided this issue — producing working masking. A1, A2, A3, and B2 all hit it.

---

## Threats to Validity

1. **N=1 per cell.** Results could vary significantly with repeated runs.
2. **Operator bias.** Same operator, not blinded, knew which arm was active.
3. **Skill description leakage.** Modified descriptions influenced all B-arm tests, including B2 where no skills were loaded. B-arm never ran against a truly vanilla baseline.
4. **Narrow surface area.** The standard library covers 3 domains. Tests were designed to exercise exactly these 3 domains. Out-of-scope tasks (monitoring, troubleshooting, optimization) are untested.
5. **Model variability.** Claude's responses are non-deterministic. Same prompt can produce different outcomes.
6. **Role hierarchy confound.** Environmental issue affected scoring asymmetrically between arms.

---

## Conclusions

The standard skills library — 17 files in a 4-layer DAG — matched or outperformed 137 bundled skill files on outcome correctness and human interventions across all three test tiers. The key mechanism is **workflow prescription**: playbooks that specify *what to do in what order* produce more reliable behavior than reference material that explains *everything the agent could do*.

The most actionable finding is that skill descriptions in the system prompt act as behavioral primers. Patterns embedded in descriptions influence agent behavior without full skill loading. This suggests the skill registry's description field is an underexploited lever for agent reliability.

These results are directional, not definitive. A proper evaluation would require multiple runs per cell, blind operation, controlled description baselines, and a broader task corpus. But the signal is consistent: structured playbooks with less material outperformed comprehensive references with more.

---

## Files in This Experiment

| File | Purpose |
|------|---------|
| `report.md` | This document — polished findings |
| `experiment_plan.md` | Pre-registered methodology, test design, scoring rubrics |
| `experiment_log.md` | Raw operator notes, per-test results, skill path comparisons |
| `agents.md` | Step-by-step runbook for executing the benchmark |
| `proposal.md` | Original proposal for the Standard Skills Library |

## Related Files (Repo Root)

| Path | Purpose |
|------|---------|
| `standard-skills-library/` | The standard library source (17 files, 4-layer DAG) |
| `bundled-skills-snapshot/` | Snapshot of Cortex Code's bundled skills at v1.0.20 |
| `run_benchmark.sh` | Orchestration script (setup, swap, clean-slate, audit) |

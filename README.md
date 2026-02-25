# Cortex Code Skills Benchmark

Benchmarking skill architectures for [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code), Snowflake's AI agent CLI.

## What This Repo Contains

**The question:** Does the structure of agent skills matter? Or is comprehensive reference material always better?

**The approach:** We run the same natural-language Snowflake tasks against two skill configurations and measure what a business user cares about: time, correctness, and how much hand-holding the agent needs.

| Arm | Description | Material |
|-----|-------------|----------|
| **A: Bundled Skills** | Pre-shipped skills in Cortex Code (v1.0.20) | 137 files, ~50K+ lines across 23 skill directories |
| **B: Standard Skills Library** | Structured DAG: routers -> playbooks -> primitives | 17 files, ~2,400 lines across 4 layers |

## Repo Structure

```
skills_benchmark/
├── README.md                              # You are here
├── run_benchmark.sh                       # Orchestration (setup, swap, clean-slate, audit)
│
├── standard-skills-library/               # The standard library (Arm B treatment)
│   ├── router.md                          # Meta-router (entry point)
│   ├── routers/                           # Domain routers (3)
│   ├── playbooks/                         # Step-by-step workflows (3)
│   ├── primitives/                        # Atomic Snowflake operations (10)
│   ├── bundled/                           # Pre-compiled skills for Cortex Code injection
│   └── spec/                              # Authoring guide, schema, vocabulary
│
├── bundled-skills-snapshot/               # Bundled skills at Cortex Code v1.0.20
│   └── (23 skill directories)
│
└── experiments/
    └── 001_bundled-vs-standard/           # First experiment
        ├── report.md                      # Start here — polished findings
        ├── experiment_plan.md             # Methodology and test design
        ├── experiment_log.md              # Raw operator notes per test
        ├── agents.md                      # Step-by-step runbook
        └── proposal.md                    # Original standard library proposal
```

## Quick Start

**If you want the results:** Read [`experiments/001_bundled-vs-standard/report.md`](experiments/001_bundled-vs-standard/report.md).

**If you want to understand the standard library:** Read [`standard-skills-library/README.md`](standard-skills-library/README.md).

**If you want to reproduce the experiment:** Read [`experiments/001_bundled-vs-standard/agents.md`](experiments/001_bundled-vs-standard/agents.md) for the full runbook.

## Experiment 001: Headline Results

Three tests (basic, moderate, end-to-end) across both arms:

| Metric | Bundled Skills | Standard Library | Delta |
|--------|---------------|-----------------|-------|
| Outcome correctness | 77% | 83% | **+8%** |
| Human interventions | 4 | 1 | **-75%** |
| Avg time per test | 11.8 min | 9.7 min | **-18%** |
| Skill content loaded | ~16,500 lines | ~867 lines | **-95%** |

Key finding: Structured playbooks that prescribe *what to do in what order* outperformed comprehensive reference material that explains *everything the agent could do* — with 95% less context loaded.

See the [full report](experiments/001_bundled-vs-standard/report.md) for methodology, per-test breakdowns, and threats to validity.

## Adding New Experiments

Create a new directory under `experiments/`:

```
experiments/
├── 001_bundled-vs-standard/
└── 002_your-experiment-name/
    ├── report.md              # Polished findings
    ├── experiment_plan.md     # Pre-registered methodology
    └── experiment_log.md      # Raw notes
```

Number experiments sequentially. Each experiment is self-contained with its own report, plan, and log.

## Prerequisites

- Cortex Code CLI (v1.0.20+)
- Snowflake account with admin-level role access
- `snow` CLI v3.x (for orchestration script)
- Connection named `snowhouse` in `~/.snowflake/connections.toml`

## Notes

- The benchmark uses a **content replacement** approach to inject standard library skills into Cortex Code's hardcoded skill registry. See `experiment_plan.md` in each experiment for details.
- Bundled skills snapshot is a point-in-time copy. Cortex Code updates may change the bundled content.
- Results are directional (N=1 per cell). See Threats to Validity in each experiment report.

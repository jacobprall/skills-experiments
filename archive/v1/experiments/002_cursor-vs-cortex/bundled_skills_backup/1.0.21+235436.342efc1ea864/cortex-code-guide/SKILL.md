---
name: cortex-code-guide
description: "Complete reference guide for Cortex Code (CoCo) CLI. Use when: learning cortex features, understanding commands, troubleshooting setup, exploring Snowflake tools, managing sessions, configuring agents, keyboard shortcuts, MCP integration. Triggers: how to use cortex, cortex guide, cortex help, cortex commands, getting started, snowflake tools, #table syntax, subagents, sessions, resume, fork, rewind, compact, /agents, configuration."
---

# Cortex Code Guide

Comprehensive reference for **Cortex Code** (CoCo) -- Snowflake's AI-powered coding assistant CLI.

## Quick Reference

| Topic | File |
|-------|------|
| CLI & Slash Commands | `COMMANDS.md` |
| Keyboard Shortcuts | `SHORTCUTS.md` |
| Configuration | `CONFIGURATION.md` |
| Skills System | `SKILLS.md` |
| MCP Integration | `MCP.md` |
| Hooks System | `HOOKS.md` |
| Agents & Task System | `AGENTS.md` |
| Snowflake-Native Tools | `SNOWFLAKE.md` |
| Session Management | `SESSIONS.md` |


---

## Quick Start

```bash
cortex                              # Start interactive REPL
cortex -p "summarize README.md"     # Non-interactive mode
cortex --resume last                # Resume last session
cortex -r <session_id>              # Resume specific session
cortex --connection <name>          # Use specific Snowflake connection
```

## Essential Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Submit message |
| `Ctrl+J` | Insert newline |
| `Ctrl+C` | Cancel/Exit |
| `Shift+Tab` | Cycle modes |
| `Ctrl+D` | Open fullscreen todo view |
| `Ctrl+B` | Background bash process |
| `Ctrl+O` | Cycle display mode |
| `@` | File completion |
| `$` | Skill tagging |
| `#` | Snowflake table |
| `!` | Run bash command |
| `/` | Slash commands |
| `?` | Quick help |

## Operational Modes

| Mode | Command | Description |
|------|---------|-------------|
| Confirm Actions | (default) | Normal with permission checks |
| Plan Mode | `/plan` or `Ctrl+P` | Review actions before execution |
| Bypass Safeguards | `/bypass` | Auto-approve all tools (use with caution) |

Cycle modes with `Shift+Tab`.

## Common Commands

```bash
# CLI
cortex --help              # Show help
cortex --version           # Show version
cortex mcp list            # List MCP servers
cortex connections list    # List Snowflake connections

# Slash commands (in REPL)
/help                      # Show help
/status                    # Session status
/model <name>              # Switch model
/sql <query>               # Execute SQL
/skill                     # Manage skills
/agents                    # Manage agents
/compact                   # Summarize and compact context
/fork                      # Fork conversation
/rewind                    # Rewind to previous state
/diff                      # Fullscreen git diff viewer
```

## Configuration

Config directory: `~/.snowflake/cortex/`

Key files:
- `settings.json` -- Main settings
- `skills/` -- Global skills
- `agents/` -- Custom agent definitions
- `mcp.json` -- MCP server config

## Tips

1. Use `@path/to/file` to include file context
2. Use `@file$10-50` to include specific lines
3. Use `$skill-name` to activate skills
4. Use `#DB.SCHEMA.TABLE` to reference Snowflake tables (auto-injects schema + sample rows)
5. Use `!git status` to run bash (output goes to agent)
6. Use `/plan` for risky operations
7. Use `/compact` when context gets long
8. Use `/fork` before experimental approaches
9. Use `/rewind` when the agent goes down a wrong path
10. Use `Ctrl+B` to background long-running bash commands
11. Use `/agents` to manage and view available subagents

---

## Official Documentation

- **Cortex Code CLI docs**: https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli

---

**For detailed documentation, load the specific reference file listed above.**

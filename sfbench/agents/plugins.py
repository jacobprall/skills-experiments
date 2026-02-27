"""Plugin-set manager — configure agent workspaces with skills, rules, and tools."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from rich.console import Console

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PLUGIN_SETS_FILE = PROJECT_ROOT / "experiment_sets" / "plugin-sets.yaml"


class PluginSetConfig(BaseModel):
    description: str = ""
    skills_dir: Optional[str] = None
    cursor_rules: Optional[str] = None
    mcp_servers: list[str] = Field(default_factory=list)


def load_plugin_sets(path: Optional[Path] = None) -> dict[str, PluginSetConfig]:
    """Load plugin set definitions from YAML."""
    yaml_path = path or DEFAULT_PLUGIN_SETS_FILE
    if not yaml_path.exists():
        return {"blind": PluginSetConfig(description="No skills, no rules")}

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    sets = {}
    for name, cfg in data.get("plugin_sets", {}).items():
        sets[name] = PluginSetConfig(**cfg)
    return sets


def configure_workspace(
    workspace_dir: Path,
    plugin_set_name: str,
    plugin_sets_file: Optional[Path] = None,
) -> None:
    """Set up a workspace directory according to a plugin set.

    For 'blind': empty workspace, no rules file.
    For others: copy skills, write .cursorrules, configure MCP.
    """
    workspace_dir.mkdir(parents=True, exist_ok=True)
    sets = load_plugin_sets(plugin_sets_file)

    if plugin_set_name == "none" or plugin_set_name not in sets:
        return

    pset = sets[plugin_set_name]

    if plugin_set_name == "blind":
        # Explicitly write empty rules
        (workspace_dir / ".cursorrules").write_text("")
        console.print("  [dim]Plugin set: blind (no skills/rules)[/dim]")
        return

    # Copy skills directory
    if pset.skills_dir:
        skills_src = Path(pset.skills_dir)
        if skills_src.exists():
            skills_dst = workspace_dir / "skills"
            if skills_dst.exists():
                shutil.rmtree(skills_dst)
            shutil.copytree(skills_src, skills_dst, dirs_exist_ok=True)
            console.print(f"  [dim]Copied skills from {skills_src}[/dim]")

    # Copy cursor rules
    if pset.cursor_rules:
        rules_src = Path(pset.cursor_rules)
        if rules_src.exists():
            rules_dst = workspace_dir / ".cursor" / "rules"
            rules_dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rules_src, rules_dst / rules_src.name)
            console.print(f"  [dim]Copied cursor rules[/dim]")

    console.print(f"  [dim]Plugin set: {plugin_set_name} ({pset.description})[/dim]")

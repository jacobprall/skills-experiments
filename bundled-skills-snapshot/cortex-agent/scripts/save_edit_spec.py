#!/usr/bin/env python3
"""
Save edit specification to the agent workspace.

This script creates the edit_spec.json file in the correct location within
the agent workspace. Using this script ensures consistent file naming and
location across all edit operations.

@SKILL.md (edit-cortex-agent, lines 216-252):
    The edit workflow requires saving changes to edit_spec.json before applying.
    This script guarantees the file is created with the exact required name.

@SKILL.md (edit-cortex-agent, lines 563-576):
    Step 5 requires edit_spec.json to exist before applying changes via
    create_or_alter_agent.py. This script is the recommended way to create it.
"""

import argparse
import json
import sys
from pathlib import Path


def find_latest_version(workspace_dir: Path) -> Path | None:
    """Find the most recent version directory in the workspace.
    
    @SKILL.md (edit-cortex-agent, lines 95-99):
        Version directories follow the pattern vYYYYMMDD-HHMM inside
        the versions/ subdirectory of the workspace.
    """
    versions_dir = workspace_dir / "versions"
    if not versions_dir.exists():
        return None
    
    version_dirs = sorted(
        [d for d in versions_dir.iterdir() if d.is_dir() and d.name.startswith('v')],
        reverse=True  # Most recent first
    )
    
    return version_dirs[0] if version_dirs else None


def save_edit_spec(workspace_dir: Path, version: str | None, spec: dict) -> Path:
    """Save the edit specification to edit_spec.json.
    
    @SKILL.md (edit-cortex-agent, lines 218-224):
        The file MUST be named exactly edit_spec.json - no variations allowed.
        This function enforces that requirement.
    
    Args:
        workspace_dir: Path to the agent workspace directory
        version: Version directory name (e.g., v20260213-0515), or None to use latest
        spec: Dictionary containing the edit specification
        
    Returns:
        Path to the created edit_spec.json file
    """
    if version:
        version_dir = workspace_dir / "versions" / version
    else:
        version_dir = find_latest_version(workspace_dir)
        if version_dir is None:
            raise ValueError(f"No version directory found in {workspace_dir}/versions/")
    
    if not version_dir.exists():
        raise ValueError(f"Version directory does not exist: {version_dir}")
    
    # Always use the exact name edit_spec.json
    edit_spec_path = version_dir / "edit_spec.json"
    
    with open(edit_spec_path, 'w') as f:
        json.dump(spec, f, indent=2)
    
    return edit_spec_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Save edit specification to agent workspace",
        epilog="""
Examples:
  # Save orchestration instructions change:
  %(prog)s --workspace ./MY_DB_SCHEMA_AGENT --spec '{"instructions": {"orchestration": "You are helpful."}}'

  # Save to specific version:
  %(prog)s --workspace ./MY_DB_SCHEMA_AGENT --version v20260213-0515 --spec '{"comment": "Updated agent"}'

  # Read spec from stdin (useful for multi-line JSON):
  echo '{"instructions": {"response": "Be concise."}}' | %(prog)s --workspace ./MY_DB_SCHEMA_AGENT --stdin

  # Save comment change:
  %(prog)s --workspace ./MY_DB_SCHEMA_AGENT --spec '{"comment": "Sales analytics agent v2"}'

  # Save tools change:
  %(prog)s --workspace ./MY_DB_SCHEMA_AGENT --spec '{"tools": [{"tool_spec": {"type": "cortex_search", "name": "search"}}]}'
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--workspace", 
        required=True, 
        help="Path to agent workspace directory (e.g., MY_DATABASE_SCHEMA_AGENT_NAME)"
    )
    parser.add_argument(
        "--version", 
        help="Version directory name (e.g., v20260213-0515). If not provided, uses the latest version."
    )
    parser.add_argument(
        "--spec", 
        help="Edit specification as JSON string"
    )
    parser.add_argument(
        "--stdin", 
        action="store_true",
        help="Read edit specification from stdin instead of --spec argument"
    )
    
    args = parser.parse_args()
    
    # Get the spec from either --spec or stdin
    if args.stdin:
        spec_json = sys.stdin.read()
    elif args.spec:
        spec_json = args.spec
    else:
        parser.error("Either --spec or --stdin must be provided")
    
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    workspace_dir = Path(args.workspace)
    if not workspace_dir.exists():
        print(f"Error: Workspace directory does not exist: {workspace_dir}", file=sys.stderr)
        sys.exit(1)
    
    try:
        edit_spec_path = save_edit_spec(workspace_dir, args.version, spec)
        print(f"✓ Created {edit_spec_path}")
        print(f"\nContents:")
        print(json.dumps(spec, indent=2))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""
Create or alter Snowflake Cortex Agents via REST API.

This script consolidates agent creation and modification into a single tool with two commands:
- create: Create a new agent from a full specification
- alter: Modify an existing agent (full spec or instructions only)
"""

import argparse
import json
import os
import sys

import requests
import snowflake.connector
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Valid top-level keys for agent specification
VALID_TOP_LEVEL_KEYS = {
    "models", "instructions", "orchestration", "tools", "tool_resources",
    "experimental", "profile", "comment"
}


def deep_merge(base: dict, changes: dict) -> dict:
    """
    Deep merge changes into base dictionary.
    
    For nested dicts, recursively merges. For other types (including lists),
    the value from changes replaces the base value.
    
    Args:
        base: The base dictionary to merge into
        changes: The changes to apply
        
    Returns:
        dict: New dictionary with changes merged into base
    """
    result = base.copy()
    for key, value in changes.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_current_agent_spec(merge_with_file: str) -> dict:
    """
    Load and parse the current agent specification from a get_agent_config.py output file.
    
    The file format from get_agent_config.py is:
    {
        "agent_spec": "{\"instructions\": {...}, ...}",  // JSON string
        "name": "AGENT_NAME",
        ...
    }
    
    Args:
        merge_with_file: Path to the current_agent_spec.json file
        
    Returns:
        dict: Parsed agent specification
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON parsing fails
    """
    if not os.path.exists(merge_with_file):
        raise FileNotFoundError(f"Merge-with file not found: {merge_with_file}")
    
    with open(merge_with_file, 'r') as f:
        data = json.load(f)
    
    # The agent_spec field is a JSON string that needs to be parsed
    if "agent_spec" not in data:
        raise ValueError(f"File does not contain 'agent_spec' field: {merge_with_file}")
    
    agent_spec_str = data["agent_spec"]
    if isinstance(agent_spec_str, str):
        try:
            return json.loads(agent_spec_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse agent_spec JSON string: {e}")
    elif isinstance(agent_spec_str, dict):
        # Already a dict (shouldn't happen but handle it)
        return agent_spec_str
    else:
        raise ValueError(f"agent_spec must be a string or dict, got {type(agent_spec_str)}")


def validate_agent_spec(agent_spec: dict) -> list:
    """
    Validate agent specification JSON structure.
    
    Args:
        agent_spec: The agent specification dictionary
        
    Returns:
        list: List of validation errors (empty if valid)
    """
    errors = []
    
    # Check that agent_spec is a dictionary
    if not isinstance(agent_spec, dict):
        errors.append("Agent specification must be a JSON object")
        return errors
    
    # Check for invalid top-level keys
    invalid_keys = set(agent_spec.keys()) - VALID_TOP_LEVEL_KEYS
    if invalid_keys:
        errors.append(f"Invalid top-level keys found: {', '.join(sorted(invalid_keys))}")
        errors.append(f"Valid keys are: {', '.join(sorted(VALID_TOP_LEVEL_KEYS))}")
    
    # Validate models structure
    if "models" in agent_spec:
        models = agent_spec["models"]
        if not isinstance(models, dict):
            errors.append("'models' must be an object")
        elif "orchestration" in models:
            if not isinstance(models["orchestration"], str):
                errors.append("'models.orchestration' must be a string")
    
    # Validate instructions structure
    if "instructions" in agent_spec:
        instructions = agent_spec["instructions"]
        if not isinstance(instructions, dict):
            errors.append("'instructions' must be an object")
        else:
            valid_instruction_keys = {"orchestration", "response", "system", "sample_questions"}
            for key, value in instructions.items():
                if key not in valid_instruction_keys:
                    errors.append(f"Invalid instruction key: '{key}'. Valid keys: {', '.join(valid_instruction_keys)}")
                elif key == "sample_questions":
                    if not isinstance(value, list):
                        errors.append("'instructions.sample_questions' must be an array")
                    else:
                        for i, question in enumerate(value):
                            if not isinstance(question, (str, dict)):
                                errors.append(f"'instructions.sample_questions[{i}]' must be a string or object")
                elif not isinstance(value, str):
                    errors.append(f"'instructions.{key}' must be a string")
    
    # Validate orchestration structure
    if "orchestration" in agent_spec:
        orchestration = agent_spec["orchestration"]
        if not isinstance(orchestration, dict):
            errors.append("'orchestration' must be an object")
        elif "budget" in orchestration:
            budget = orchestration["budget"]
            if not isinstance(budget, dict):
                errors.append("'orchestration.budget' must be an object")
            else:
                if "seconds" in budget and not isinstance(budget["seconds"], int):
                    errors.append("'orchestration.budget.seconds' must be an integer")
                if "tokens" in budget and not isinstance(budget["tokens"], int):
                    errors.append("'orchestration.budget.tokens' must be an integer")
    
    # Validate tools structure
    if "tools" in agent_spec:
        tools = agent_spec["tools"]
        if not isinstance(tools, list):
            errors.append("'tools' must be an array")
        else:
            for i, tool in enumerate(tools):
                if not isinstance(tool, dict):
                    errors.append(f"'tools[{i}]' must be an object")
                elif "tool_spec" not in tool:
                    errors.append(f"'tools[{i}].tool_spec' is required")
                else:
                    tool_spec = tool["tool_spec"]
                    if not isinstance(tool_spec, dict):
                        errors.append(f"'tools[{i}].tool_spec' must be an object")
                    else:
                        if "type" in tool_spec and not isinstance(tool_spec["type"], str):
                            errors.append(f"'tools[{i}].tool_spec.type' must be a string")
                        if "name" in tool_spec and not isinstance(tool_spec["name"], str):
                            errors.append(f"'tools[{i}].tool_spec.name' must be a string")
                        if "description" in tool_spec and not isinstance(tool_spec["description"], str):
                            errors.append(f"'tools[{i}].tool_spec.description' must be a string")
    
    # Validate tool_resources structure
    if "tool_resources" in agent_spec:
        tool_resources = agent_spec["tool_resources"]
        if not isinstance(tool_resources, dict):
            errors.append("'tool_resources' must be an object")
    
    # Validate profile structure
    if "profile" in agent_spec:
        profile = agent_spec["profile"]
        if not isinstance(profile, dict):
            errors.append("'profile' must be an object")
    
    # Validate comment
    if "comment" in agent_spec:
        if not isinstance(agent_spec["comment"], str):
            errors.append("'comment' must be a string")
    
    # Validate experimental
    if "experimental" in agent_spec:
        if not isinstance(agent_spec["experimental"], dict):
            errors.append("'experimental' must be an object")
    
    return errors


def load_and_validate_json(config_file: str) -> dict:
    """
    Load and validate JSON configuration file.
    
    Args:
        config_file: Path to JSON configuration file
        
    Returns:
        dict: Validated agent specification
        
    Raises:
        ValueError: If JSON is invalid or validation fails
        FileNotFoundError: If config file doesn't exist
    """
    # Check if file exists
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    # Load JSON
    try:
        with open(config_file, 'r') as f:
            agent_spec = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    # Validate structure
    errors = validate_agent_spec(agent_spec)
    if errors:
        error_msg = "JSON validation failed:\n  " + "\n  ".join(errors)
        raise ValueError(error_msg)
    
    return agent_spec


def read_instructions(instructions_arg: str) -> str:
    """
    Read instructions from file or use as direct text.
    
    Args:
        instructions_arg: File path or instruction text
        
    Returns:
        str: Instructions text
    """
    if os.path.isfile(instructions_arg):
        with open(instructions_arg, 'r') as f:
            return f.read()
    return instructions_arg


def handle_create(args):
    """Handle create subcommand."""
    # Load and validate agent spec
    agent_spec = load_and_validate_json(args.config_file)
    
    # Connect to Snowflake
    conn = snowflake.connector.connect(connection_name=args.connection)
    
    try:
        # Switch to specified role if provided
        if args.role:
            cursor = conn.cursor()
            try:
                cursor.execute(f"USE ROLE {args.role}")
                print(f"Using role: {args.role}")
            finally:
                cursor.close()
        
        # Prepare the request body - merge agent_spec fields into root
        request_body = {
            "name": args.agent_name
        }
        request_body.update(agent_spec)
        
        # Make API request to create agent
        url = f"https://{conn.host}/api/v2/databases/{args.database}/schemas/{args.schema}/agents"
        
        headers = {
            "Authorization": f'Snowflake Token="{conn.rest.token}"',
            "Content-Type": "application/json"
        }
        
        print(f"Creating agent {args.agent_name} in {args.database}.{args.schema}...")
        
        response = requests.post(url, json=request_body, headers=headers, verify=False)
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"✓ Successfully created agent {args.agent_name}")
            result = response.json()
            print(f"  Created on: {result.get('created_on', 'N/A')}")
            print(f"  Location: {args.database}.{args.schema}.{args.agent_name}")
            return result
        else:
            raise Exception(f"Failed to create agent: {response.status_code} - {response.text}")
    finally:
        conn.close()


def handle_alter(args):
    """Handle alter subcommand."""
    # Validate that at least one input is provided
    if not args.config_file and not args.instructions:
        raise ValueError("alter requires at least one of: --config-file or --instructions")
    
    # Validate --merge-with usage
    if args.merge_with and not args.config_file:
        raise ValueError("--merge-with requires --config-file to be specified")
    
    # Determine what to alter
    if args.config_file and args.instructions:
        # Load config and override instructions
        print("Loading full spec and overriding instructions...")
        agent_spec = load_and_validate_json(args.config_file)
        instructions_text = read_instructions(args.instructions)
        
        # Override orchestration instructions
        if "instructions" not in agent_spec:
            agent_spec["instructions"] = {}
        agent_spec["instructions"]["orchestration"] = instructions_text
        
        request_body = agent_spec
        
    elif args.config_file:
        # Full spec update (or partial with merge)
        agent_spec = load_and_validate_json(args.config_file)
        
        if args.merge_with:
            # Merge changes with current config
            print(f"Loading current config from {args.merge_with}...")
            current_spec = load_current_agent_spec(args.merge_with)
            
            print("Merging changes with current configuration...")
            merged_spec = deep_merge(current_spec, agent_spec)
            
            # Validate merged result
            errors = validate_agent_spec(merged_spec)
            if errors:
                error_msg = "Merged spec validation failed:\n  " + "\n  ".join(errors)
                raise ValueError(error_msg)
            
            print(f"  Merged keys: {', '.join(merged_spec.keys())}")
            request_body = merged_spec
        else:
            print("Altering agent with full specification...")
            request_body = agent_spec
        
    else:  # args.instructions only
        # Instructions-only update (lightweight)
        print("Altering agent instructions only...")
        instructions_text = read_instructions(args.instructions)
        request_body = {
            "instructions": {
                "orchestration": instructions_text
            }
        }
        print(f"\nNew instructions:\n{'-'*60}")
        print(instructions_text)
        print(f"{'-'*60}\n")
    
    # Connect to Snowflake
    conn = snowflake.connector.connect(connection_name=args.connection)
    
    try:
        # Switch to specified role if provided
        if args.role:
            cursor = conn.cursor()
            try:
                cursor.execute(f"USE ROLE {args.role}")
                print(f"Using role: {args.role}")
            finally:
                cursor.close()
        
        # Make API request to alter agent
        url = f"https://{conn.host}/api/v2/databases/{args.database}/schemas/{args.schema}/agents/{args.agent_name}"
        
        headers = {
            "Authorization": f'Snowflake Token="{conn.rest.token}"',
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        print(f"Altering agent {args.agent_name} in {args.database}.{args.schema}...")
        
        response = requests.put(url, json=request_body, headers=headers, verify=False)
        
        if response.status_code == 200:
            print(f"✓ Successfully altered agent {args.agent_name}")
            if response.text:
                result = response.json()
                print(f"  Modified on: {result.get('modified_on', 'N/A')}")
            print(f"  Location: {args.database}.{args.schema}.{args.agent_name}")
            return True
        else:
            raise Exception(f"Failed to alter agent: {response.status_code} - {response.text}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create or alter Snowflake Cortex Agents via REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', required=True, help='Command to execute')
    
    # CREATE subcommand
    create_parser = subparsers.add_parser(
        'create',
        help='Create a new agent from full specification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --agent-name MY_AGENT --config-file full_spec.json
  %(prog)s --agent-name MY_AGENT --config-file spec.json --database MY_DB --schema MY_SCHEMA --role MY_ROLE
        """
    )
    create_parser.add_argument('--agent-name', required=True, help='Name for the new agent')
    create_parser.add_argument('--config-file', required=True, help='Path to full agent specification JSON')
    create_parser.add_argument('--database', required=True, 
                              help='Database name')
    create_parser.add_argument('--schema', required=True, 
                              help='Schema name')
    create_parser.add_argument('--role', required=True,
                              help='Snowflake role to use')
    create_parser.add_argument('--connection', default=os.getenv('SNOWFLAKE_CONNECTION_NAME', 'snowhouse'),
                              help='Snowflake connection name')
    
    # ALTER subcommand
    alter_parser = subparsers.add_parser(
        'alter',
        help='Alter an existing agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Alter instructions only (quick/common):
  %(prog)s --agent-name MY_AGENT --instructions instructions.txt
  %(prog)s --agent-name MY_AGENT --instructions "Always be polite and concise"

  # Alter full specification (replaces entire config):
  %(prog)s --agent-name MY_AGENT --config-file full_spec.json

  # Partial edit with merge (recommended for partial changes):
  %(prog)s --agent-name MY_AGENT --config-file edit_spec.json --merge-with current_agent_spec.json

  # Alter full spec but override instructions:
  %(prog)s --agent-name MY_AGENT --config-file full_spec.json --instructions custom_instructions.txt

Note: At least one of --config-file or --instructions is required.
      Use --merge-with when making partial changes to preserve existing config.
        """
    )
    alter_parser.add_argument('--agent-name', required=True, help='Name of the agent to alter')
    alter_parser.add_argument('--config-file', help='Path to agent specification JSON (full or partial)')
    alter_parser.add_argument('--merge-with', 
                             help='Path to current_agent_spec.json to merge changes with (for partial edits)')
    alter_parser.add_argument('--instructions', help='Path to instructions file or instructions text')
    alter_parser.add_argument('--database', default='SNOWFLAKE_INTELLIGENCE',
                             help='Database name (default: SNOWFLAKE_INTELLIGENCE)')
    alter_parser.add_argument('--schema', default='AGENTS',
                             help='Schema name (default: AGENTS)')
    alter_parser.add_argument('--role',
                             help='Snowflake role to use (optional)')
    alter_parser.add_argument('--connection', default=os.getenv('SNOWFLAKE_CONNECTION_NAME', 'snowhouse'),
                             help='Snowflake connection name')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'create':
            handle_create(args)
        elif args.command == 'alter':
            handle_alter(args)
    except ValueError as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"File Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate semantic model using FastGen API endpoint (REST).

This script calls the /api/v2/cortex/analyst/fast-generation endpoint to automatically
generate a semantic model from SQL queries and table metadata.

Follows the pattern from snowpilot/orchestrator/e2e_tests/fixtures/semantic_model_automation_client.py

Usage:
    python generate_semantic_model_fastgen.py <config_file> <output_directory> --connection <connection_name>

Example:
    python generate_semantic_model_fastgen.py "./fastgen_config.json" "./output" --connection my_connection
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def parse_sse_response(response: requests.Response) -> Dict[str, Any]:
    """
    Parse SSE response from FastGen endpoint and extract semantic YAML.

    Extracts semantic YAML from the last successful response before stream ends.
    Also collects warnings, errors, request_id, and suggestions from the response.

    Args:
        response: SSE response object from FastGen endpoint

    Returns:
        Dictionary with "semantic_yaml", "warnings", "errors", "request_id", "suggestions" keys
    """
    last_semantic_yaml = None
    all_warnings: list[str] = []
    all_errors: list[str] = []
    request_id: Optional[str] = None
    all_suggestions: list[Dict[str, Any]] = []

    for line in response.iter_lines(decode_unicode=True):
        if not line or (isinstance(line, str) and not line.strip()):
            continue

        line_str = line

        if line_str == "event: done":
            pass

        if line_str.startswith("data: "):
            data_str = line_str[6:]

            if data_str == "done":
                if last_semantic_yaml:
                    return {
                        "semantic_yaml": last_semantic_yaml,
                        "warnings": all_warnings,
                        "errors": all_errors,
                        "request_id": request_id,
                        "suggestions": all_suggestions,
                        "status": "success",
                    }
                else:
                    return {
                        "errors": all_errors
                        if all_errors
                        else ["No semantic YAML generated"],
                        "warnings": all_warnings,
                        "request_id": request_id,
                        "suggestions": all_suggestions,
                    }

            try:
                parsed_response = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if "json_proto" in parsed_response:
                proto_data = parsed_response["json_proto"]

                if proto_data.get("errors"):
                    for error in proto_data["errors"]:
                        if isinstance(error, dict):
                            error_msg = error.get("message", str(error))
                        else:
                            error_msg = str(error)
                        if error_msg not in all_errors:
                            all_errors.append(error_msg)

                if proto_data.get("warnings"):
                    for warning in proto_data["warnings"]:
                        if isinstance(warning, dict):
                            warning_msg = warning.get("message", str(warning))
                        else:
                            warning_msg = str(warning)
                        if warning_msg not in all_warnings:
                            all_warnings.append(warning_msg)

                yaml_field = proto_data.get("semanticYaml")
                if yaml_field:
                    last_semantic_yaml = yaml_field

                extensions = proto_data.get("extensions", {})
                if extensions.get("request_id"):
                    req_id_val = extensions["request_id"]
                    if isinstance(req_id_val, dict):
                        request_id = req_id_val.get(
                            "stringValue", req_id_val.get("string_value")
                        )
                    else:
                        request_id = str(req_id_val)

                structured_suggestions = proto_data.get("structuredSuggestions", [])
                for suggestion in structured_suggestions:
                    if suggestion not in all_suggestions:
                        all_suggestions.append(suggestion)

    if last_semantic_yaml:
        return {
            "semantic_yaml": last_semantic_yaml,
            "warnings": all_warnings,
            "errors": all_errors,
            "request_id": request_id,
            "suggestions": all_suggestions,
            "status": "success",
        }

    return {
        "errors": all_errors if all_errors else ["FastGen stream ended without YAML"],
        "warnings": all_warnings,
        "request_id": request_id,
        "suggestions": all_suggestions,
    }


def normalize_identifier(identifier: str) -> str:
    """
    Normalize identifiers to UPPERCASE if not already quoted.

    If identifier is quoted with escaped quotes (e.g., "\"MixedCase\""),
    return as-is. Otherwise, convert to UPPERCASE.

    Args:
        identifier: The identifier string (table name, column name, etc.)

    Returns:
        UPPERCASE identifier if unquoted, or original if quoted
    """
    if isinstance(identifier, str):
        if identifier.startswith('\\"') and identifier.endswith('\\"'):
            return identifier
        return identifier.upper()
    return identifier


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize all identifiers in configuration to UPPERCASE.

    Converts unquoted table names, column names, database, and schema names to UPPERCASE.
    Preserves quoted identifiers with escaped quotes.

    Args:
        config: Configuration dictionary from JSON file

    Returns:
        Configuration with normalized identifiers
    """
    if "tables" in config and isinstance(config["tables"], list):
        for table in config["tables"]:
            if "database" in table:
                table["database"] = normalize_identifier(table["database"])
            if "schema" in table:
                table["schema"] = normalize_identifier(table["schema"])
            if "table" in table:
                table["table"] = normalize_identifier(table["table"])
            if "column_names" in table and isinstance(table["column_names"], list):
                table["column_names"] = [
                    normalize_identifier(col) for col in table["column_names"]
                ]

    if "metadata" in config and isinstance(config["metadata"], dict):
        if "warehouse" in config["metadata"]:
            config["metadata"]["warehouse"] = normalize_identifier(
                config["metadata"]["warehouse"]
            )

    if "extensions" in config and isinstance(config["extensions"], dict):
        if "semantic_view_db" in config["extensions"]:
            config["extensions"]["semantic_view_db"] = normalize_identifier(
                config["extensions"]["semantic_view_db"]
            )
        if "semantic_view_schema" in config["extensions"]:
            config["extensions"]["semantic_view_schema"] = normalize_identifier(
                config["extensions"]["semantic_view_schema"]
            )

    return config


def load_config(config_file: Path) -> Dict[str, Any]:
    """
    Load FastGen configuration from JSON file.

    Config file should contain:
    - name: model name
    - sql_source: queries
    - tables: table definitions
    - metadata: warehouse, etc.
    - extensions: additional settings

    Args:
        config_file: Path to configuration JSON file

    Returns:
        Configuration dictionary

    Raises:
        SystemExit: If config file not found or invalid JSON
    """
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        sys.exit(1)

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config: Dict[str, Any] = json.load(f)

        config = normalize_config(config)

        return config
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to read config file: {e}")
        sys.exit(1)


def load_snowflake_config(connection_name: str) -> tuple[str, Dict[str, Any]]:
    """
    Load Snowflake connection configuration from ~/.snowflake/config.toml.

    Args:
        connection_name: Name of the connection to load (case-insensitive)

    Returns:
        Tuple of (actual_connection_name_from_config, configuration_dictionary)
    """
    import tomllib

    config_path = Path.home() / ".snowflake" / "config.toml"
    if not config_path.exists():
        print(f"❌ Snowflake config not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
            connections = config.get("connections", {})

            if not connections:
                print(f"❌ No connections found in {config_path}")
                sys.exit(1)

            for conn_key, conn_value in connections.items():
                if conn_key.lower() == connection_name.lower():
                    print(f"✅ Found connection: {conn_key}")
                    return conn_key, dict(conn_value)

            print(f"❌ Connection '{connection_name}' not found in {config_path}")
            print(f"   Available connections: {list(connections.keys())}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading Snowflake config: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def get_auth_headers(
    token: Optional[str] = None,
    connection_name: Optional[str] = None,
    role_override: Optional[str] = None,
) -> tuple[Dict[str, str], Dict[str, Any], Any]:
    """
    Build authentication headers and connection info for FastGen API.

    Follows the pattern from test_semantic_model_automation_client:
    - Loads Snowflake connection from config.toml
    - Gets session token for FastGen API authentication
    - Returns connection (which must stay open while making requests!)

    Args:
        token: Optional explicit authentication token (overrides connection)
        connection_name: Snowflake connection name from ~/.snowflake/config.toml
        role_override: Optional role to use instead of the one in config file

    Returns:
        Tuple of (headers dict, connection_info dict, snowflake_connection object)
        IMPORTANT: Keep the returned connection object alive during API calls!
    """
    import snowflake.connector

    headers = {"Content-Type": "application/json"}
    connection_info: Dict[str, Any] = {}

    auth_token = token
    conn = None

    if not auth_token:
        if not connection_name:
            print(
                "❌ No connection name specified. Please provide --connection argument."
            )
            print("   Available connections can be found in ~/.snowflake/config.toml")
            sys.exit(1)

        conn_name = connection_name
        print(f"📋 Using Snowflake connection: {conn_name}")

        try:
            actual_conn_name, sf_config = load_snowflake_config(conn_name)
            connection_info["role"] = sf_config.get("role")
            connection_info["warehouse"] = sf_config.get("warehouse")
            connection_info["account"] = sf_config.get("account")
            connection_info["user"] = sf_config.get("user")

            if role_override:
                print(
                    f"⚠️  Overriding role from config: {connection_info['role']} → {role_override}"
                )
                connection_info["role"] = role_override

            print("✅ Loaded connection config:")
            if connection_info["user"]:
                print(f"   User: {connection_info['user']}")
            if connection_info["role"]:
                print(f"   Role: {connection_info['role']}")
            if connection_info["warehouse"]:
                print(f"   Warehouse: {connection_info['warehouse']}")

            print("   Connecting to Snowflake...")
            if role_override:
                conn = snowflake.connector.connect(
                    connection_name=actual_conn_name, role=role_override
                )
            else:
                conn = snowflake.connector.connect(connection_name=actual_conn_name)

            connection_info["host"] = conn.host
            print(f"✅ Connected to: {connection_info['host']}")

            cursor = conn.cursor()
            cursor.execute("SELECT CURRENT_USER()")
            current_user = cursor.fetchone()
            if current_user:
                connection_info["current_user"] = current_user[0]
                print(f"✅ Connected as: {connection_info['current_user']}")

            cursor.execute("SELECT CURRENT_ACCOUNT()")
            current_account = cursor.fetchone()
            if current_account:
                connection_info["current_account"] = current_account[0]

            cursor.execute("SELECT CURRENT_WAREHOUSE()")
            current_warehouse = cursor.fetchone()
            if current_warehouse and current_warehouse[0]:
                connection_info["current_warehouse"] = current_warehouse[0]

            cursor.execute("SELECT CURRENT_ROLE()")
            current_role = cursor.fetchone()
            if current_role and current_role[0]:
                connection_info["current_role"] = current_role[0]

            cursor.close()

            print("✅ Snowflake connection established")
            print(f"   Account: {conn.account}")
            print(f"   Current role: {connection_info.get('current_role', 'N/A')}")
            print(
                f"   Current warehouse: {connection_info.get('current_warehouse', 'N/A')}"
            )

            print("🔐 Getting FastGen authentication token...")
            if conn.rest.token:
                auth_token = f'Snowflake Token="{conn.rest.token}"'
                print("✅ Got FastGen token (Snowflake session format)")
            else:
                print("⚠️  No session token available")
                auth_token = None

        except Exception as e:
            print(f"❌ Error with Snowflake connection: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    if not auth_token:
        print("❌ No authentication token available")
        sys.exit(1)

    headers["Authorization"] = auth_token

    return headers, connection_info, conn


def call_fastgen_api(
    host: str,
    config: Dict[str, Any],
    headers: Dict[str, str],
    connection_info: Optional[Dict[str, Any]] = None,
    verify_ssl: bool = True,
    streaming: bool = True,
) -> Dict[str, Any]:
    """
    Call FastGen API endpoint with the provided configuration.

    Follows the pattern from SemanticModelAutomationGSClient.fast_gen_streaming():
    - Wraps request in "json_proto" key
    - Posts to connection.host/api/v2/cortex/analyst/fast-generation

    Args:
        host: API host (e.g., snowhouse.snowflakecomputing.com)
        config: FastGen configuration dictionary
        headers: Authentication headers
        connection_info: Connection info from Snowflake
        verify_ssl: Whether to verify SSL certificates (default: True)
        streaming: Whether to use streaming mode (default: True)

    Returns:
        Parsed response from FastGen endpoint

    Raises:
        SystemExit: If API call fails
    """
    if connection_info is None:
        connection_info = {}

    extensions = config.get("extensions", {}).copy()
    extensions["streaming"] = "true" if streaming else "false"

    if connection_info.get("role") and "sf_role" not in extensions:
        extensions["sf_role"] = connection_info["role"]

    request_body: Dict[str, Any] = {
        "json_proto": {
            "name": config.get("name"),
            "metadata": config.get("metadata", {}),
            "extensions": extensions,
        },
    }

    if config.get("sql_source"):
        request_body["json_proto"]["sql_source"] = config["sql_source"]

    if config.get("tables"):
        request_body["json_proto"]["tables"] = config["tables"]

    endpoint = f"https://{host}/api/v2/cortex/analyst/fast-generation"

    try:
        print(f"Calling FastGen API: {endpoint}")
        print("📋 Request metadata:")
        print(f"   Model name: {config.get('name')}")
        print(f"   Account: {connection_info.get('current_account', 'N/A')}")
        print(f"   User: {connection_info.get('current_user', 'N/A')}")
        print(f"   Warehouse: {connection_info.get('warehouse', 'N/A')}")
        print(f"   Role: {connection_info.get('role', 'N/A')}")
        print(f"   Semantic DB: {extensions.get('semantic_view_db', 'N/A')}")
        print(f"   Semantic Schema: {extensions.get('semantic_view_schema', 'N/A')}")
        print(f"   Auth header: {headers.get('Authorization', 'MISSING')[:20]}...")
        print()

        api_request_start = time.time()
        response = requests.post(
            endpoint,
            json=request_body,
            headers=headers,
            stream=True,
            timeout=300,
            verify=verify_ssl,
        )
        api_request_time = time.time() - api_request_start
        print(f"⏱️  HTTP request completed in {api_request_time:.2f}s")

        if response.status_code != 200:
            print(f"❌ FastGen API returned status code: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            sys.exit(1)

        parse_start = time.time()
        parsed = parse_sse_response(response)
        parse_time = time.time() - parse_start
        print(f"⏱️  Response parsing completed in {parse_time:.2f}s")

        if parsed.get("warnings"):
            print("\n⚠️  FastGen returned warnings:")
            for warning in parsed["warnings"]:
                print(f"   ⚠️  {warning}")

        if parsed.get("errors"):
            print("\n❌ FastGen returned errors:")
            for error in parsed["errors"]:
                print(f"   ❌ {error}")

        return parsed

    except requests.exceptions.Timeout:
        print("❌ FastGen API request timed out (300 seconds)")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Failed to connect to FastGen API: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error calling FastGen API: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def print_semantic_model_summary(yaml_content: str) -> None:
    """
    Parse and print a summary of the generated semantic model.

    Displays:
    - Number of tables and columns
    - Number of verified queries
    - Number of relationships

    Args:
        yaml_content: YAML content string
    """
    try:
        yaml_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError:
        return

    if not isinstance(yaml_data, dict):
        return

    print("\n📊 Semantic Model Summary:")
    print("=" * 50)

    tables = yaml_data.get("tables", [])
    num_tables = len(tables)
    total_columns = 0
    for table in tables:
        if isinstance(table, dict):
            dimensions = table.get("dimensions", [])
            measures = table.get("measures", [])
            total_columns += len(dimensions) + len(measures)

    print(f"  📋 Tables: {num_tables}")
    print(f"  📊 Columns: {total_columns}")

    vqrs = yaml_data.get("verified_queries", [])
    print(f"  ✅ Verified Queries: {len(vqrs)}")

    relationships = yaml_data.get("relationships", [])
    print(f"  🔗 Relationships: {len(relationships)}")

    print("=" * 50)


def save_semantic_yaml(
    yaml_content: str,
    output_dir: Path,
    model_name: str,
    warnings: Optional[list[str]] = None,
    errors: Optional[list[str]] = None,
    request_id: Optional[str] = None,
    suggestions: Optional[list[Dict[str, Any]]] = None,
) -> None:
    """
    Save semantic YAML content and metadata to files.

    Saves:
    - YAML file with the semantic model
    - JSON file with semantic_yaml, warnings, errors, request_id, and suggestions

    Args:
        yaml_content: YAML content string
        output_dir: Output directory path
        model_name: Model name to use in filename
        warnings: Optional list of warning messages
        errors: Optional list of error messages
        request_id: Optional request ID from FastGen response
        suggestions: Optional list of structured suggestions from FastGen

    Raises:
        SystemExit: If YAML is invalid or save fails
    """
    if warnings is None:
        warnings = []
    if errors is None:
        errors = []
    if suggestions is None:
        suggestions = []

    try:
        yaml_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        print(f"❌ Invalid YAML in FastGen response: {e}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = model_name.replace(".", "_").replace('"', "").replace("'", "")

    yaml_file = output_dir / f"{safe_name}_semantic_model.yaml"
    json_file = output_dir / f"{safe_name}_metadata.json"

    try:
        save_start = time.time()
        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, sort_keys=False)

        print("✅ Successfully generated semantic model")
        print(f"📁 Saved to: {yaml_file}")
        print(f"📊 File size: {len(yaml_content)} characters")

        metadata: Dict[str, Any] = {
            "semantic_yaml": yaml_content,
            "warnings": warnings,
            "errors": errors,
            "request_id": request_id,
            "suggestions": suggestions,
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        save_time = time.time() - save_start
        print(f"📋 Metadata saved to: {json_file}")
        if request_id:
            print(f"🆔 Request ID: {request_id}")
        if suggestions:
            print(f"💡 Suggestions: {len(suggestions)} structured suggestions captured")
        print(f"⏱️  Files saved in {save_time:.2f}s")

        print_semantic_model_summary(yaml_content)

    except Exception as e:
        print(f"❌ Failed to save files: {e}")
        sys.exit(1)


def main() -> None:
    script_start_time = time.time()
    print(f"⏱️  Script started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    parser = argparse.ArgumentParser(
        description="Generate semantic model using FastGen API (REST endpoint)"
    )
    parser.add_argument(
        "config_file",
        help="Path to FastGen configuration JSON file",
    )
    parser.add_argument(
        "output_directory",
        help="Directory to save the generated semantic model YAML",
    )
    parser.add_argument(
        "--connection",
        required=True,
        help="Snowflake connection name from ~/.snowflake/config.toml",
    )
    parser.add_argument(
        "--role",
        help="Override the role from config file (optional)",
    )
    parser.add_argument(
        "--no-ssl-verify",
        action="store_true",
        help="Disable SSL certificate verification (for internal/test environments)",
    )

    args = parser.parse_args()

    config_file = Path(args.config_file)
    output_dir = Path(args.output_directory)

    config_load_start = time.time()
    print(f"Loading configuration from: {config_file}")
    config = load_config(config_file)
    config_load_time = time.time() - config_load_start
    print(f"   ⏱️  Config loaded in {config_load_time:.2f}s")

    model_name = config.get("name", "fastgen_model")

    auth_start = time.time()
    print("Authenticating with FastGen API...")
    headers, connection_info, sf_conn = get_auth_headers(
        None, args.connection, args.role
    )
    auth_time = time.time() - auth_start
    print(f"   ⏱️  Authentication completed in {auth_time:.2f}s")

    host = connection_info.get("host")
    if not host:
        print("❌ Could not determine API host from Snowflake connection")
        if sf_conn:
            sf_conn.close()
        sys.exit(1)

    try:
        api_start = time.time()
        print(f"Generating semantic model: {model_name}")
        result = call_fastgen_api(
            host,
            config,
            headers,
            connection_info,
            verify_ssl=not args.no_ssl_verify,
            streaming=False,
        )
        api_time = time.time() - api_start
        print(f"   ⏱️  FastGen API completed in {api_time:.2f}s")

        warnings = result.get("warnings", [])
        errors = result.get("errors", [])
        request_id = result.get("request_id")
        suggestions = result.get("suggestions", [])

        if "semantic_yaml" in result and result["semantic_yaml"]:
            save_semantic_yaml(
                result["semantic_yaml"],
                output_dir,
                model_name,
                warnings,
                errors,
                request_id,
                suggestions,
            )
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            safe_name = model_name.replace(".", "_").replace('"', "").replace("'", "")
            json_file = output_dir / f"{safe_name}_metadata.json"

            metadata: Dict[str, Any] = {
                "semantic_yaml": None,
                "warnings": warnings,
                "errors": errors,
                "request_id": request_id,
                "suggestions": suggestions,
            }

            try:
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                print(f"📋 Metadata saved to: {json_file}")
                if request_id:
                    print(f"🆔 Request ID: {request_id}")
                if suggestions:
                    print(
                        f"💡 Suggestions: {len(suggestions)} structured suggestions captured"
                    )
            except Exception as e:
                print(f"⚠️  Could not save metadata: {e}")
                import traceback

                traceback.print_exc()

            sys.exit(1)
    finally:
        if sf_conn:
            sf_conn.close()

        total_time = time.time() - script_start_time
        print(f"\n⏱️  Total script execution time: {total_time:.2f}s")
        print(f"✅ Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

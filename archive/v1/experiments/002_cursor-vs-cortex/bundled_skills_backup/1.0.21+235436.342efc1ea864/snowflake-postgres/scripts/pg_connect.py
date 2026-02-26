#!/usr/bin/env python3
"""
Connection management for Snowflake Postgres using standard PostgreSQL files.

Uses:
- ~/.pg_service.conf - connection profiles (host, port, dbname, user, sslmode)
- ~/.pgpass - passwords (enforced 0600 permissions by PostgreSQL clients)

Also handles CREATE INSTANCE and RESET ACCESS operations via Snowflake,
saving credentials securely without exposing them in chat.

Credentials are never logged to console.
"""

import argparse
import configparser
import json
import os
import sys
import tomllib
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import psycopg2
import snowflake.connector
from cryptography.hazmat.primitives import serialization

# Standard PostgreSQL config files
PG_SERVICE_FILE = Path.home() / ".pg_service.conf"
PGPASS_FILE = Path.home() / ".pgpass"

# Snowflake CLI config paths (for --create and --reset to connect to Snowflake)
# These are standard Snowflake CLI locations - the script reads them directly
# when executed standalone (not through the agent's SQL tool)
_SF_CONFIG_DIR = Path.home() / ".snowflake"
_SF_CONNECTIONS_TOML = _SF_CONFIG_DIR / "connections.toml"
_SF_CONFIG_TOML = _SF_CONFIG_DIR / "config.toml"
_SF_AGENT_SETTINGS = _SF_CONFIG_DIR / "cortex" / "settings.json"

_SF_ALLOWED_CONFIG_KEYS = {
    "account", "user", "password", "authenticator",
    "private_key_path", "private_key_passphrase",
    "host", "database", "schema", "warehouse", "role",
}


def _row_to_dict(columns: list, row: list | tuple) -> dict:
    """Convert a SQL result row to a dict using column names."""
    return {col.lower(): val for col, val in zip(columns, row)}


def parse_create_response(response_file: str) -> dict:
    """
    Extract connection params from CREATE POSTGRES INSTANCE JSON response.
    
    Handles two formats:
    1. Direct dict: {"host": "...", "access_roles": [...]}
    2. SQL result: {"columns": [...], "rows": [[...]]}
    
    Returns dict with:
    - host, port, database, sslmode (connection info)
    - user, password (primary user - snowflake_admin)
    - access_roles: list of {"name": str, "password": str} for all roles
    """
    if not Path(response_file).exists():
        raise FileNotFoundError(
            f"Response file not found: {response_file}\n"
            "The temp file may have been cleaned up. To add this connection:\n"
            "  • Ask your assistant to reset credentials for this instance, or\n"
            "  • Manually add your connection to ~/.pg_service.conf and password to ~/.pgpass"
        )
    
    with open(response_file) as f:
        data = json.load(f)
    
    # Handle list wrapper
    if isinstance(data, list) and len(data) > 0:
        data = data[0]
    
    # Handle SQL result format: {"columns": [...], "rows": [[...]]}
    if "columns" in data and "rows" in data:
        columns = data["columns"]
        rows = data["rows"]
        if not rows:
            raise ValueError("No rows in response")
        data = _row_to_dict(columns, rows[0])
    
    host = data.get("host")
    if not host:
        raise ValueError("No 'host' field found in response")
    
    # Extract access_roles (may be JSON string or already parsed)
    access_roles = data.get("access_roles", [])
    if isinstance(access_roles, str):
        try:
            access_roles = json.loads(access_roles)
        except json.JSONDecodeError:
            access_roles = []
    
    # Extract all roles with passwords
    # Handles two formats:
    # 1. Dict format: {"role_name": "password", ...} (real Snowflake response)
    # 2. List format: [{"name": "...", "password": "..."}, ...] (legacy/test format)
    roles_with_passwords = []
    admin_password = None
    
    if isinstance(access_roles, dict):
        # Dict format: keys are role names, values are passwords
        for role_name, password in access_roles.items():
            if role_name and password:
                roles_with_passwords.append({
                    "name": role_name,
                    "password": password,
                })
                if role_name == "snowflake_admin":
                    admin_password = password
    elif isinstance(access_roles, list):
        # List format: each item has "name" and "password" keys
        for role in access_roles:
            if isinstance(role, dict) and role.get("name") and role.get("password"):
                roles_with_passwords.append({
                    "name": role["name"],
                    "password": role["password"],
                })
                if role["name"] == "snowflake_admin":
                    admin_password = role["password"]
    
    if not admin_password:
        raise ValueError("No snowflake_admin password found in access_roles")
    
    return {
        "host": host,
        "port": 5432,
        "database": "postgres",
        "user": "snowflake_admin",
        "password": admin_password,
        "sslmode": "require",
        "access_roles": roles_with_passwords,
    }


def _extract_password(payload: object) -> str | None:
    """Extract a password from common response shapes."""
    if isinstance(payload, list) and payload:
        return _extract_password(payload[0])

    if isinstance(payload, dict):
        if payload.get("password"):
            return payload["password"]

        access_roles = payload.get("access_roles")
        if isinstance(access_roles, list):
            for role in access_roles:
                if isinstance(role, dict) and role.get("password"):
                    return role["password"]

        if "data" in payload:
            return _extract_password(payload["data"])

        # Handle SQL result format: {"columns": ["col1", ...], "rows": [[val1, ...], ...]}
        if "columns" in payload and "rows" in payload:
            columns = payload["columns"]
            rows = payload["rows"]
            if isinstance(columns, list) and isinstance(rows, list) and rows:
                # Find password column index (case-insensitive)
                col_lower = [c.lower() if isinstance(c, str) else c for c in columns]
                if "password" in col_lower:
                    pwd_idx = col_lower.index("password")
                    first_row = rows[0]
                    if isinstance(first_row, (list, tuple)) and len(first_row) > pwd_idx:
                        return first_row[pwd_idx]

        if "rows" in payload:
            return _extract_password(payload["rows"])

    return None


def parse_reset_response(response_file: str) -> str:
    """
    Extract password from RESET ACCESS response JSON.
    """
    if not Path(response_file).exists():
        raise FileNotFoundError(
            f"Reset response file not found: {response_file}\n"
            "The temp file may have been cleaned up. To update this connection:\n"
            "  • Ask your assistant to reset credentials again, or\n"
            "  • Manually update your password in ~/.pgpass"
        )
    
    with open(response_file) as f:
        data = json.load(f)

    password = _extract_password(data)
    if not password:
        raise ValueError("No password field found in reset response")

    return password


def parse_connection_string(conn_str: str) -> dict:
    """
    Parse a postgres:// connection string into components.
    
    Returns dict with: host, port, database, user, password, sslmode
    """
    parsed = urlparse(conn_str)
    
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ValueError(f"Invalid scheme: {parsed.scheme}. Expected postgres:// or postgresql://")
    
    # Extract query params (like sslmode)
    query_params = parse_qs(parsed.query)
    
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": (parsed.path.lstrip("/") or None) if parsed.path else None,
        "user": parsed.username,
        "password": unquote(parsed.password) if parsed.password else None,
        "sslmode": query_params.get("sslmode", ["require"])[0],
    }


def build_connection_string(params: dict) -> str:
    """
    Build a connection string from parameters.
    Password is masked in the output.
    """
    password_display = "****" if params.get("password") else ""
    return (
        f"postgres://{params.get('user', '')}:{password_display}@"
        f"{params.get('host', '')}:{params.get('port', 5432)}/"
        f"{params.get('database', '')}?sslmode={params.get('sslmode', 'require')}"
    )


def sanitize_error(error_msg: str, params: dict) -> str:
    """Remove any credentials from error messages."""
    msg = str(error_msg)
    if params.get("password"):
        msg = msg.replace(params["password"], "[REDACTED]")
    if params.get("user"):
        msg = msg.replace(f"user={params['user']}", "user=[REDACTED]")
    return msg


def categorize_connection_error(error: Exception, params: dict) -> str:
    """Provide helpful error messages for common connection issues."""
    error_str = str(error).lower()
    
    if "connection refused" in error_str or "could not connect" in error_str:
        return (
            "Connection refused. Possible causes:\n"
            "  • Your IP may not be in the network policy allow list\n"
            "  • The Postgres instance may be suspended\n"
            "  • Firewall blocking port 5432\n"
            "  Run: network_policy_check.py to verify your IP is allowed"
        )
    elif "timeout" in error_str or "timed out" in error_str:
        return (
            "Connection timed out. Possible causes:\n"
            "  • Network connectivity issues\n"
            "  • Firewall blocking the connection\n"
            "  • Instance may be starting up"
        )
    elif "authentication failed" in error_str or "password" in error_str:
        return (
            "Authentication failed. Possible causes:\n"
            "  • Incorrect username or password\n"
            "  • Password may need URL encoding for special characters\n"
            "  • User may not exist on this instance"
        )
    elif "ssl" in error_str:
        return (
            "SSL error. Ensure your connection string includes:\n"
            "  ?sslmode=require"
        )
    elif "does not exist" in error_str:
        return (
            f"Database '{params.get('database')}' not found.\n"
            "  • Check the database name\n"
            "  • Default database is usually 'postgres'"
        )
    else:
        return f"Connection failed: {sanitize_error(error, params)}"


def validate_connection(params: dict) -> tuple[bool, str]:
    """
    Test a connection to verify it works.
    
    Returns (success, message). Never exposes credentials in error messages.
    """
    try:
        conn = psycopg2.connect(
            host=params["host"],
            port=params["port"],
            database=params["database"],
            user=params["user"],
            password=params["password"],
            sslmode=params.get("sslmode", "require"),
            connect_timeout=10,
        )
        conn.close()
        return True, "Connection successful"
    except psycopg2.Error as e:
        return False, categorize_connection_error(e, params)
    except Exception as e:
        return False, f"Unexpected error: {sanitize_error(e, params)}"


# --- Snowflake Connection (for CREATE/RESET operations) ---

def _read_agent_connection_name() -> str | None:
    """Read default connection name from agent settings if available."""
    if not _SF_AGENT_SETTINGS.exists():
        return None
    try:
        data = json.loads(_SF_AGENT_SETTINGS.read_text())
    except json.JSONDecodeError:
        return None
    return data.get("cortexAgentConnectionName")


def _load_snowflake_connection_config(connection_name: str | None) -> tuple[str, dict]:
    """Load Snowflake connection config from ~/.snowflake/connections.toml or config.toml."""
    connections: dict[str, dict] = {}
    default_name = None

    if _SF_CONNECTIONS_TOML.exists():
        data = tomllib.loads(_SF_CONNECTIONS_TOML.read_text())
        default_name = data.get("default_connection_name")
        for key, value in data.items():
            if key != "default_connection_name" and isinstance(value, dict):
                connections[key] = value
    elif _SF_CONFIG_TOML.exists():
        data = tomllib.loads(_SF_CONFIG_TOML.read_text())
        default_name = data.get("default_connection_name")
        connections = data.get("connections", {})

    if not connections:
        raise RuntimeError(
            "No Snowflake connection config found in ~/.snowflake/connections.toml or ~/.snowflake/config.toml"
        )

    target = (
        connection_name
        or os.environ.get("SNOWFLAKE_CONNECTION_NAME")
        or os.environ.get("SNOWFLAKE_DEFAULT_CONNECTION_NAME")
        or default_name
        or _read_agent_connection_name()
    )
    if not target:
        target = next(iter(connections.keys()))

    if target not in connections:
        raise RuntimeError(
            f"Connection '{target}' not found. Available: {', '.join(connections.keys())}"
        )

    return target, connections[target]


def _load_private_key(path: str, passphrase: str | None) -> object:
    """Load a private key from file for Snowflake key-pair auth."""
    key_bytes = Path(path).read_bytes()
    password = passphrase.encode() if passphrase else None
    return serialization.load_pem_private_key(key_bytes, password=password)


def get_snowflake_connection(
    connection_name: str | None = None,
    authenticator: str | None = None,
) -> snowflake.connector.SnowflakeConnection:
    """
    Get a Snowflake connection using available configuration.

    Priority:
    1. Environment variables (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, etc.)
    2. Connection name from ~/.snowflake/connections.toml
    """
    env_account = os.environ.get("SNOWFLAKE_ACCOUNT")
    env_user = os.environ.get("SNOWFLAKE_USER")
    if env_account and env_user:
        connect_args = {"account": env_account, "user": env_user}
        if authenticator:
            connect_args["authenticator"] = authenticator
        elif os.environ.get("SNOWFLAKE_AUTHENTICATOR"):
            connect_args["authenticator"] = os.environ["SNOWFLAKE_AUTHENTICATOR"]
        elif os.environ.get("SNOWFLAKE_PASSWORD"):
            connect_args["password"] = os.environ["SNOWFLAKE_PASSWORD"]
        return snowflake.connector.connect(**connect_args)

    target_name, config = _load_snowflake_connection_config(connection_name)
    connect_args = {k: v for k, v in config.items() if k in _SF_ALLOWED_CONFIG_KEYS}

    if authenticator:
        connect_args["authenticator"] = authenticator

    if connect_args.get("private_key_path"):
        connect_args["private_key"] = _load_private_key(
            connect_args["private_key_path"],
            connect_args.get("private_key_passphrase"),
        )
        connect_args.pop("private_key_path", None)
        connect_args.pop("private_key_passphrase", None)

    return snowflake.connector.connect(**connect_args)


def execute_snowflake_sql(query: str, connection_name: str | None = None, authenticator: str | None = None) -> dict:
    """Execute a SQL query on Snowflake and return the result."""
    conn = get_snowflake_connection(connection_name, authenticator)
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            columns = [c[0] for c in cur.description] if cur.description else []
    finally:
        conn.close()
    return {"query": query, "columns": columns, "rows": rows}


def write_secure_json(path: str, payload: dict) -> None:
    """Write JSON to a file with 0600 permissions."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2))
    os.chmod(output_path, 0o600)


def create_postgres_instance(
    instance_name: str,
    compute_pool: str,
    storage: int,
    auto_suspend_secs: int | None = None,
    enable_ha: bool = False,
    postgres_version: str | None = None,
    network_policy: str | None = None,
    snowflake_connection: str | None = None,
    authenticator: str | None = None,
) -> dict:
    """
    Create a Snowflake Postgres instance and save connection securely.
    
    Returns dict with instance info (host) without exposing passwords.
    """
    # Build optional clauses
    optional_clauses = []
    if auto_suspend_secs is not None:
        optional_clauses.append(f"AUTO_SUSPEND_SECS = {auto_suspend_secs}")
    if enable_ha:
        optional_clauses.append("HIGH_AVAILABILITY = TRUE")
    if postgres_version:
        optional_clauses.append(f"POSTGRES_VERSION = '{postgres_version}'")
    if network_policy:
        optional_clauses.append(f"NETWORK_POLICY = '{network_policy}'")
    
    optional_sql = "\n  ".join(optional_clauses)
    if optional_sql:
        optional_sql = "\n  " + optional_sql
    
    query = f"""CREATE POSTGRES INSTANCE {instance_name}
  COMPUTE_FAMILY = '{compute_pool}'
  STORAGE_SIZE_GB = {storage}
  AUTHENTICATION_AUTHORITY = POSTGRES{optional_sql};"""

    response = execute_snowflake_sql(query, snowflake_connection, authenticator)
    
    # Write to temp file for debugging/recovery
    tmp_path = f"/tmp/pg_create_{instance_name}.json"
    write_secure_json(tmp_path, response)
    
    # Parse and save connection
    conn_info = parse_create_response(tmp_path)
    connection_name = instance_name.lower()
    
    save_service_entry(connection_name, conn_info)
    upsert_pgpass_entry(
        host=conn_info["host"],
        port=int(conn_info.get("port", 5432)),
        database=conn_info.get("database", "postgres"),
        user=conn_info.get("user", "snowflake_admin"),
        password=conn_info["password"],
    )
    
    return {
        "instance_name": instance_name,
        "connection_name": connection_name,
        "host": conn_info["host"],
    }


def reset_postgres_access(
    instance_name: str,
    role: str = "snowflake_admin",
    host: str | None = None,
    snowflake_connection: str | None = None,
    authenticator: str | None = None,
) -> dict:
    """
    Reset credentials for a Snowflake Postgres role and update saved password.
    
    If --host is provided, creates the service entry if missing.
    Otherwise requires an existing connection in ~/.pg_service.conf.
    """
    query = f"ALTER POSTGRES SERVICE {instance_name} RESET ACCESS FOR '{role}';"
    
    response = execute_snowflake_sql(query, snowflake_connection, authenticator)
    
    # Write to temp file for debugging/recovery
    tmp_path = f"/tmp/pg_reset_{instance_name}.json"
    write_secure_json(tmp_path, response)
    
    # Parse password and update pgpass
    new_password = parse_reset_response(tmp_path)
    connection_name = instance_name.lower()
    
    # Get existing service entry or create from --host
    service_entry = get_service_entry(connection_name)
    if not service_entry:
        if host:
            # Create new service entry with provided host
            service_entry = {
                "host": host,
                "port": 5432,
                "database": "postgres",
                "user": "snowflake_admin",
                "sslmode": "require",
            }
            save_service_entry(connection_name, service_entry)
        else:
            return {
                "success": False,
                "instance_name": instance_name,
                "message": f"No existing connection '{connection_name}' in ~/.pg_service.conf. Use --host to create one.",
                "tmp_path": tmp_path,
            }
    
    # Update password in pgpass for the specific role being reset
    upsert_pgpass_entry(
        host=service_entry["host"],
        port=int(service_entry.get("port", 5432)),
        database=service_entry.get("database", "postgres"),
        user=role,
        password=new_password,
    )
    
    return {
        "success": True,
        "instance_name": instance_name,
        "connection_name": connection_name,
        "role": role,
    }


# --- PostgreSQL Service File Management ---

def load_service_file() -> configparser.ConfigParser:
    """Load ~/.pg_service.conf as a ConfigParser object."""
    config = configparser.ConfigParser()
    if PG_SERVICE_FILE.exists():
        config.read(PG_SERVICE_FILE)
    return config


def save_service_file(config: configparser.ConfigParser) -> None:
    """Save the service file in pg_service.conf format (no spaces around =)."""
    with open(PG_SERVICE_FILE, "w") as f:
        for section in config.sections():
            f.write(f"[{section}]\n")
            for key, value in config.items(section):
                f.write(f"{key}={value}\n")
            f.write("\n")


def get_service_entry(name: str) -> dict | None:
    """Get a service entry by name (without password).
    
    Returns None if the entry doesn't exist or is missing required 'host' field.
    """
    config = load_service_file()
    if name not in config.sections():
        return None
    
    host = config.get(name, "host", fallback=None)
    if not host:
        # Host is required - return None for invalid entries
        return None
    
    return {
        "host": host,
        "port": config.getint(name, "port", fallback=5432),
        "database": config.get(name, "dbname", fallback="postgres"),
        "user": config.get(name, "user", fallback="snowflake_admin"),
        "sslmode": config.get(name, "sslmode", fallback="require"),
    }


def save_service_entry(name: str, params: dict) -> None:
    """Save a service entry (without password)."""
    config = load_service_file()
    
    if name not in config.sections():
        config.add_section(name)
    
    config.set(name, "host", params["host"])
    config.set(name, "port", str(params.get("port", 5432)))
    config.set(name, "dbname", params.get("database", "postgres"))
    config.set(name, "user", params.get("user", "snowflake_admin"))
    config.set(name, "sslmode", params.get("sslmode", "require"))
    
    save_service_file(config)


def delete_service_entry(name: str) -> bool:
    """Delete a service entry."""
    config = load_service_file()
    if name not in config.sections():
        return False
    
    config.remove_section(name)
    save_service_file(config)
    return True


def list_service_entries() -> list[str]:
    """List all service entry names."""
    config = load_service_file()
    return config.sections()


# --- PostgreSQL Password File Management ---

def load_pgpass() -> list[dict]:
    """
    Load ~/.pgpass entries.
    
    Format: hostname:port:database:username:password
    Lines starting with # are comments.
    """
    entries = []
    if not PGPASS_FILE.exists():
        return entries
    
    with open(PGPASS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Handle escaped colons (\:)
            parts = []
            current = ""
            i = 0
            while i < len(line):
                if line[i] == "\\" and i + 1 < len(line) and line[i + 1] == ":":
                    current += ":"
                    i += 2
                elif line[i] == ":":
                    parts.append(current)
                    current = ""
                    i += 1
                else:
                    current += line[i]
                    i += 1
            parts.append(current)
            
            if len(parts) == 5:
                entries.append({
                    "host": parts[0],
                    "port": parts[1],
                    "database": parts[2],
                    "user": parts[3],
                    "password": parts[4],
                })
    
    return entries


def save_pgpass(entries: list[dict]) -> None:
    """Save entries to ~/.pgpass with secure permissions."""
    lines = []
    for entry in entries:
        # Escape backslashes and colons in all fields
        # Also strip newlines from password to prevent file corruption
        def escape(s):
            return str(s).replace("\\", "\\\\").replace(":", "\\:")
        
        def escape_password(s):
            # Escape backslashes and colons (colons are field delimiters in pgpass format).
            # Strip newlines to prevent file corruption (one entry per line).
            return str(s).replace("\\", "\\\\").replace(":", "\\:").replace("\n", "").replace("\r", "")
        
        line = ":".join([
            escape(entry["host"]),
            str(entry.get("port", "*")),
            escape(entry.get("database", "*")),
            escape(entry.get("user", "*")),
            escape_password(entry["password"]),
        ])
        lines.append(line)
    
    with open(PGPASS_FILE, "w") as f:
        f.write("# PostgreSQL password file - managed by pg_connect.py\n")
        f.write("# Format: hostname:port:database:username:password\n")
        f.write("\n".join(lines))
        if lines:
            f.write("\n")
    
    # Enforce secure permissions (required by PostgreSQL)
    os.chmod(PGPASS_FILE, 0o600)


def find_pgpass_entry(host: str, port: int, database: str, user: str) -> dict | None:
    """Find a matching pgpass entry."""
    entries = load_pgpass()
    for entry in entries:
        if (
            (entry["host"] == "*" or entry["host"] == host) and
            (entry["port"] == "*" or str(entry["port"]) == str(port)) and
            (entry["database"] == "*" or entry["database"] == database) and
            (entry["user"] == "*" or entry["user"] == user)
        ):
            return entry
    return None


def upsert_pgpass_entry(host: str, port: int, database: str, user: str, password: str) -> None:
    """Add or update a pgpass entry."""
    entries = load_pgpass()
    
    # Find and update existing entry
    for entry in entries:
        if (
            entry["host"] == host and
            str(entry["port"]) == str(port) and
            entry["database"] == database and
            entry["user"] == user
        ):
            entry["password"] = password
            save_pgpass(entries)
            return
    
    # Add new entry
    entries.append({
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": password,
    })
    save_pgpass(entries)


def delete_pgpass_entry(host: str, port: int, database: str, user: str) -> bool:
    """Delete a pgpass entry."""
    entries = load_pgpass()
    original_len = len(entries)
    
    entries = [
        e for e in entries
        if not (
            e["host"] == host and
            str(e["port"]) == str(port) and
            e["database"] == database and
            e["user"] == user
        )
    ]
    
    if len(entries) < original_len:
        save_pgpass(entries)
        return True
    return False


# --- Combined Operations ---

def save_connection(name: str, params: dict) -> dict:
    """
    Save a connection to both service file and pgpass.
    
    If params contains 'access_roles' (from CREATE response), saves all roles
    to pgpass. Otherwise saves just the primary user/password.
    
    Returns dict with:
      - service_existed: bool - True if service file already existed
      - connection_existed: bool - True if this connection name already existed
      - pgpass_existed: bool - True if pgpass file already existed
      - password_updated: bool - True if password entry was updated (vs created)
      - roles_saved: list[str] - names of roles saved to pgpass
    """
    result = {
        "service_existed": PG_SERVICE_FILE.exists(),
        "connection_existed": get_service_entry(name) is not None,
        "pgpass_existed": PGPASS_FILE.exists(),
        "password_updated": False,
        "roles_saved": [],
    }
    
    host = params["host"]
    port = params.get("port", 5432)
    database = params.get("database", "postgres")
    
    # Check if primary pgpass entry already exists
    if params.get("password"):
        existing_pgpass = find_pgpass_entry(
            host, port, database,
            params.get("user", "snowflake_admin"),
        )
        result["password_updated"] = existing_pgpass is not None
    
    # Save service entry (no password, uses primary user)
    save_service_entry(name, params)
    
    # Save passwords to pgpass - either all access_roles or just primary user
    access_roles = params.get("access_roles", [])
    if access_roles:
        # CREATE response with multiple roles - save all to pgpass
        for role in access_roles:
            if role.get("name") and role.get("password"):
                upsert_pgpass_entry(host, port, database, role["name"], role["password"])
                result["roles_saved"].append(role["name"])
    elif params.get("password"):
        # Single user/password (e.g., from connection string)
        user = params.get("user", "snowflake_admin")
        upsert_pgpass_entry(host, port, database, user, params["password"])
        result["roles_saved"].append(user)
    
    return result


def get_connection(name: str) -> dict | None:
    """
    Get a connection by service name.
    Combines service entry with password from pgpass.
    """
    service = get_service_entry(name)
    if not service:
        return None
    
    # Look up password from pgpass
    pgpass_entry = find_pgpass_entry(
        service["host"],
        service["port"],
        service["database"],
        service["user"],
    )
    
    if pgpass_entry:
        service["password"] = pgpass_entry["password"]
    
    return service


def delete_connection(name: str) -> bool:
    """Delete a connection from both service file and pgpass."""
    service = get_service_entry(name)
    
    service_deleted = delete_service_entry(name)
    pgpass_deleted = False
    
    if service:
        pgpass_deleted = delete_pgpass_entry(
            service["host"],
            service.get("port", 5432),
            service.get("database", "postgres"),
            service.get("user", "snowflake_admin"),
        )
    
    return service_deleted or pgpass_deleted


def list_connections() -> list[str]:
    """List all saved connection names (from service file)."""
    return list_service_entries()


def update_password(name: str, new_password: str) -> bool:
    """
    Update password for an existing saved connection.
    """
    service = get_service_entry(name)
    if not service:
        return False
    
    upsert_pgpass_entry(
        service["host"],
        service.get("port", 5432),
        service.get("database", "postgres"),
        service.get("user", "snowflake_admin"),
        new_password,
    )
    return True


def get_connect_params(connection: str = None, connection_name: str = None) -> dict:
    """
    Get connection parameters from either a connection string or saved name.
    
    Priority: connection string > connection name > 'default'
    """
    if connection:
        return parse_connection_string(connection)
    
    name = connection_name or "default"
    params = get_connection(name)
    
    if not params:
        raise ValueError(
            f"No connection found with name '{name}'. "
            f"Provide --connection or save one with --save"
        )
    
    return params


def main():
    parser = argparse.ArgumentParser(
        description="Manage Postgres connections using standard PostgreSQL files",
        epilog="Connections stored in ~/.pg_service.conf and ~/.pgpass",
    )
    parser.add_argument("--connection", "-c", help="Connection string (postgres://...)")
    parser.add_argument("--connection-name", "-n", default="default", help="Name for saved connection")
    parser.add_argument("--save", "-s", action="store_true", help="Save the connection")
    parser.add_argument("--test", "-t", action="store_true", help="Test the connection")
    parser.add_argument("--list", "-l", action="store_true", help="List saved connections")
    parser.add_argument("--delete", "-d", help="Delete a saved connection")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    # Extract credentials from CREATE/DESCRIBE response file (agent-safe)
    parser.add_argument("--from-response", help="Extract credentials from CREATE INSTANCE JSON response file")
    # Extract password from RESET ACCESS response file (agent-safe)
    parser.add_argument("--from-reset-response", help="Extract password from RESET ACCESS JSON response file")
    
    # Snowflake operations: CREATE and RESET (execute SQL + save connection)
    parser.add_argument("--create", action="store_true", help="Create a new Postgres instance")
    parser.add_argument("--reset", action="store_true", help="Reset credentials for an existing instance")
    parser.add_argument("--instance-name", "-i", help="Instance name (for --create or --reset)")
    parser.add_argument("--compute-pool", help="Compute pool for --create (STANDARD_M, STANDARD_L, etc.)")
    parser.add_argument("--storage", type=int, help="Storage in GB for --create")
    parser.add_argument("--auto-suspend-secs", type=int, help="Auto-suspend timeout for --create (optional)")
    parser.add_argument("--enable-ha", action="store_true", help="Enable high availability for --create")
    parser.add_argument("--postgres-version", help="Postgres version for --create (e.g., 16)")
    parser.add_argument("--network-policy", help="Network policy name for --create")
    parser.add_argument("--role", default="snowflake_admin", choices=["snowflake_admin", "application"], 
                        help="Role for --reset")
    parser.add_argument("--host", help="Host for --reset (creates service entry if missing)")
    parser.add_argument("--snowflake-connection", help="Snowflake connection name from ~/.snowflake/connections.toml")
    parser.add_argument("--authenticator", help="Snowflake authenticator (e.g., externalbrowser)")
    
    args = parser.parse_args()
    
    # Handle --from-response: extract credentials from CREATE response file
    if args.from_response:
        try:
            args._params_from_args = parse_create_response(args.from_response)
        except FileNotFoundError as e:
            print(f"❌ {e}", file=sys.stderr)
            sys.exit(1)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ Failed to parse response file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.from_reset_response:
        try:
            args._update_password_from_file = parse_reset_response(args.from_reset_response)
        except FileNotFoundError as e:
            print(f"❌ {e}", file=sys.stderr)
            sys.exit(1)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ Failed to parse reset response file: {e}", file=sys.stderr)
            sys.exit(1)
    
    output = {"success": True, "message": "", "data": None}
    
    try:
        # Handle --create: Create Postgres instance via Snowflake
        if args.create:
            if not args.instance_name:
                print("❌ --instance-name is required for --create", file=sys.stderr)
                sys.exit(1)
            if not args.compute_pool:
                print("❌ --compute-pool is required for --create", file=sys.stderr)
                sys.exit(1)
            if not args.storage:
                print("❌ --storage is required for --create", file=sys.stderr)
                sys.exit(1)
            if args.role != "snowflake_admin":
                print("❌ --role is for --reset, not --create (CREATE creates all roles automatically)", file=sys.stderr)
                sys.exit(1)
            
            result = create_postgres_instance(
                instance_name=args.instance_name,
                compute_pool=args.compute_pool,
                storage=args.storage,
                auto_suspend_secs=args.auto_suspend_secs,
                enable_ha=args.enable_ha,
                postgres_version=args.postgres_version,
                network_policy=args.network_policy,
                snowflake_connection=args.snowflake_connection,
                authenticator=args.authenticator,
            )
            output["data"] = {"host": result["host"]}
            output["message"] = (
                f"Created instance {result['instance_name']}\n"
                f"   Host: {result['host']}\n"
                f"⏳ Instance is provisioning (1-2 minutes)\n"
                f"✅ Connection saved to ~/.pg_service.conf\n"
                f"✅ Password saved to ~/.pgpass\n"
                f"   Connect with: psql \"service={result['connection_name']}\""
            )
        
        # Handle --reset: Reset credentials via Snowflake
        elif args.reset:
            if not args.instance_name:
                print("❌ --instance-name is required for --reset", file=sys.stderr)
                sys.exit(1)
            
            result = reset_postgres_access(
                instance_name=args.instance_name,
                role=args.role,
                host=args.host,
                snowflake_connection=args.snowflake_connection,
                authenticator=args.authenticator,
            )
            if result["success"]:
                output["message"] = (
                    f"Reset credentials for {result['instance_name']} ({result['role']})\n"
                    f"✅ Password updated in ~/.pgpass\n"
                    f"   Connect with: psql \"service={result['connection_name']}\""
                )
            else:
                output["success"] = False
                output["message"] = (
                    f"{result['message']}\n"
                    f"Response saved to: {result['tmp_path']}\n"
                    f"Run: pg_connect.py --from-reset-response {result['tmp_path']} --connection-name {args.instance_name.lower()}"
                )
        
        # Handle password update from reset response file
        elif hasattr(args, '_update_password_from_file'):
            if update_password(args.connection_name, args._update_password_from_file):
                output["message"] = (
                    f"Password for '{args.connection_name}' updated in ~/.pgpass\n"
                    f"Connect with: psql \"service={args.connection_name}\""
                )
            else:
                output["success"] = False
                output["message"] = f"Connection '{args.connection_name}' not found in ~/.pg_service.conf"
                
        elif args.list:
            names = list_connections()
            output["data"] = names
            output["message"] = f"Found {len(names)} saved connections in ~/.pg_service.conf"
            
        elif args.delete:
            if delete_connection(args.delete):
                output["message"] = f"Deleted connection '{args.delete}' from service file and pgpass"
            else:
                output["success"] = False
                output["message"] = f"Connection '{args.delete}' not found"
                
        elif args.connection or hasattr(args, '_params_from_args'):
            if hasattr(args, '_params_from_args'):
                params = args._params_from_args
            else:
                params = parse_connection_string(args.connection)
            
            if args.test:
                success, msg = validate_connection(params)
                output["success"] = success
                output["message"] = msg
                
            if args.save and output["success"]:
                save_result = save_connection(args.connection_name, params)
                if output["success"]:
                    if save_result["connection_existed"]:
                        output["message"] = (
                            f"Connection '{args.connection_name}' updated\n"
                            f"  Service file: ~/.pg_service.conf\n"
                            f"  Password: ~/.pgpass\n"
                            f"Connect with: psql \"service={args.connection_name}\""
                        )
                    else:
                        output["message"] = (
                            f"Connection '{args.connection_name}' saved\n"
                            f"  Service file: ~/.pg_service.conf\n"
                            f"  Password: ~/.pgpass\n"
                            f"Connect with: psql \"service={args.connection_name}\""
                        )
                
            if output["success"]:
                # Filter out secrets from display output
                secret_keys = {"password", "access_roles"}
                display_params = {k: v for k, v in params.items() if k not in secret_keys}
                display_params["has_password"] = bool(params.get("password"))
                output["data"] = display_params
            
        else:
            names = list_connections()
            if names:
                output["data"] = {"saved_connections": names}
                output["message"] = (
                    "Connections stored in:\n"
                    "  ~/.pg_service.conf (connection profiles)\n"
                    "  ~/.pgpass (passwords)\n"
                    "Use --connection to add or --list to see saved"
                )
            else:
                output["message"] = (
                    "No saved connections.\n"
                    "Use --connection to add one, or manually edit:\n"
                    "  ~/.pg_service.conf (connection profiles)\n"
                    "  ~/.pgpass (passwords, chmod 600)"
                )
                
    except ValueError as e:
        output["success"] = False
        output["message"] = str(e)
    except Exception as e:
        output["success"] = False
        # Show actual error for debugging (Snowflake errors contain useful info)
        error_msg = str(e)
        # Truncate very long error messages but keep the important parts
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        output["message"] = f"Error: {type(e).__name__}: {error_msg}"
    
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        if output["message"]:
            prefix = "✅" if output["success"] else "❌"
            print(f"{prefix} {output['message']}")
        if output["data"]:
            if isinstance(output["data"], list):
                for item in output["data"]:
                    print(f"  - {item}")
            elif isinstance(output["data"], dict):
                # Never print secret fields even if they somehow got into output
                secret_fields = {"password", "access_roles"}
                for k, v in output["data"].items():
                    if k not in secret_fields:
                        print(f"  {k}: {v}")
    
    sys.exit(0 if output["success"] else 1)


if __name__ == "__main__":
    main()

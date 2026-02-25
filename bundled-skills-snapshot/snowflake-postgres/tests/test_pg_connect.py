"""Tests for pg_connect.py parsing and file management functions."""

import json
import os
import tempfile
from pathlib import Path

import pytest

# Import from scripts directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from pg_connect import (
    _extract_password,
    _row_to_dict,
    parse_create_response,
    parse_reset_response,
    load_pgpass,
    save_pgpass,
    find_pgpass_entry,
    upsert_pgpass_entry,
    load_service_file,
    save_service_entry,
    get_service_entry,
    save_connection,
)


class TestExtractPassword:
    """Tests for _extract_password function."""
    
    def test_direct_password_field(self):
        """Password at top level of dict."""
        assert _extract_password({"password": "secret123"}) == "secret123"
    
    def test_password_in_access_roles(self):
        """Password nested in access_roles array."""
        data = {
            "access_roles": [
                {"name": "snowflake_admin", "password": "admin_pass"}
            ]
        }
        assert _extract_password(data) == "admin_pass"
    
    def test_password_in_data_wrapper(self):
        """Password nested under 'data' key."""
        data = {"data": {"password": "wrapped_pass"}}
        assert _extract_password(data) == "wrapped_pass"
    
    def test_password_in_rows_wrapper(self):
        """Password nested under 'rows' key (list of dicts)."""
        data = {"rows": [{"password": "row_pass"}]}
        assert _extract_password(data) == "row_pass"
    
    def test_sql_result_format_columns_rows(self):
        """SQL result format: {"columns": [...], "rows": [[...]]}."""
        data = {
            "columns": ["PASSWORD"],
            "rows": [["sql_password_value"]]
        }
        assert _extract_password(data) == "sql_password_value"
    
    def test_sql_result_format_case_insensitive(self):
        """SQL columns are matched case-insensitively."""
        data = {
            "columns": ["other", "Password", "more"],
            "rows": [["a", "the_password", "b"]]
        }
        assert _extract_password(data) == "the_password"
    
    def test_sql_result_format_no_password_column(self):
        """SQL result without password column returns None."""
        data = {
            "columns": ["name", "value"],
            "rows": [["test", "data"]]
        }
        assert _extract_password(data) is None
    
    def test_list_wrapper(self):
        """Password in first element of list."""
        data = [{"password": "list_pass"}]
        assert _extract_password(data) == "list_pass"
    
    def test_empty_dict(self):
        """Empty dict returns None."""
        assert _extract_password({}) is None
    
    def test_empty_list(self):
        """Empty list returns None."""
        assert _extract_password([]) is None
    
    def test_none_input(self):
        """None input returns None."""
        assert _extract_password(None) is None


class TestRowToDict:
    """Tests for _row_to_dict helper."""
    
    def test_basic_conversion(self):
        """Converts columns and row to dict."""
        columns = ["NAME", "VALUE"]
        row = ["test", 123]
        result = _row_to_dict(columns, row)
        assert result == {"name": "test", "value": 123}
    
    def test_lowercase_keys(self):
        """Column names are lowercased."""
        columns = ["HOST", "Port", "DbName"]
        row = ["host.com", 5432, "mydb"]
        result = _row_to_dict(columns, row)
        assert "host" in result
        assert "port" in result
        assert "dbname" in result


class TestParseCreateResponse:
    """Tests for parse_create_response function."""
    
    def test_direct_dict_format(self):
        """Parse direct dict response format."""
        data = {
            "host": "abc123.snowflakecomputing.com",
            "access_roles": [
                {"name": "snowflake_admin", "password": "admin_secret"}
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            result = parse_create_response(f.name)
            assert result["host"] == "abc123.snowflakecomputing.com"
            assert result["password"] == "admin_secret"
            assert result["port"] == 5432
            assert result["user"] == "snowflake_admin"
            
            os.unlink(f.name)
    
    def test_multiple_access_roles(self):
        """Parse response with both admin and application roles."""
        data = {
            "host": "multi.snowflakecomputing.com",
            "access_roles": [
                {"name": "snowflake_admin", "password": "admin_pass"},
                {"name": "application", "password": "app_pass"}
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            result = parse_create_response(f.name)
            assert result["host"] == "multi.snowflakecomputing.com"
            assert result["user"] == "snowflake_admin"
            assert result["password"] == "admin_pass"
            # access_roles should contain both
            assert len(result["access_roles"]) == 2
            role_names = [r["name"] for r in result["access_roles"]]
            assert "snowflake_admin" in role_names
            assert "application" in role_names
            
            os.unlink(f.name)
    
    def test_sql_result_format(self):
        """Parse SQL result format with columns/rows."""
        data = {
            "columns": ["host", "access_roles"],
            "rows": [[
                "xyz789.snowflakecomputing.com",
                json.dumps([{"name": "snowflake_admin", "password": "sql_secret"}])
            ]]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            result = parse_create_response(f.name)
            assert result["host"] == "xyz789.snowflakecomputing.com"
            assert result["password"] == "sql_secret"
            
            os.unlink(f.name)
    
    def test_sql_result_dict_access_roles(self):
        """Parse real Snowflake response with dict access_roles (role_name: password)."""
        data = {
            "columns": ["status", "host", "access_roles", "default_database"],
            "rows": [[
                "Postgres instance creation initiated.",
                "real.snowflakecomputing.com",
                json.dumps({"application": "app_secret", "snowflake_admin": "admin_secret"}),
                "postgres"
            ]]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            result = parse_create_response(f.name)
            assert result["host"] == "real.snowflakecomputing.com"
            assert result["user"] == "snowflake_admin"
            assert result["password"] == "admin_secret"
            assert len(result["access_roles"]) == 2
            role_names = [r["name"] for r in result["access_roles"]]
            assert "snowflake_admin" in role_names
            assert "application" in role_names
            # Verify passwords are correctly mapped
            for role in result["access_roles"]:
                if role["name"] == "snowflake_admin":
                    assert role["password"] == "admin_secret"
                elif role["name"] == "application":
                    assert role["password"] == "app_secret"
            
            os.unlink(f.name)
    
    def test_list_wrapped_response(self):
        """Parse response wrapped in a list."""
        data = [{
            "host": "wrapped.snowflakecomputing.com",
            "access_roles": [
                {"name": "snowflake_admin", "password": "wrapped_pass"}
            ]
        }]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            result = parse_create_response(f.name)
            assert result["host"] == "wrapped.snowflakecomputing.com"
            
            os.unlink(f.name)
    
    def test_missing_host_raises(self):
        """Missing host field raises ValueError."""
        data = {"access_roles": [{"name": "snowflake_admin", "password": "x"}]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="No 'host' field"):
                parse_create_response(f.name)
            
            os.unlink(f.name)
    
    def test_missing_password_raises(self):
        """Missing snowflake_admin password raises ValueError."""
        data = {"host": "test.com", "access_roles": []}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="No snowflake_admin password"):
                parse_create_response(f.name)
            
            os.unlink(f.name)


class TestParseResetResponse:
    """Tests for parse_reset_response function."""
    
    def test_sql_result_format(self):
        """Parse RESET ACCESS SQL result format."""
        data = {
            "query": "ALTER POSTGRES SERVICE test RESET ACCESS FOR 'snowflake_admin';",
            "columns": ["password"],
            "rows": [["new_reset_password"]]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            result = parse_reset_response(f.name)
            assert result == "new_reset_password"
            
            os.unlink(f.name)
    
    def test_direct_password_format(self):
        """Parse direct password field format."""
        data = {"password": "direct_pass"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            result = parse_reset_response(f.name)
            assert result == "direct_pass"
            
            os.unlink(f.name)
    
    def test_missing_password_raises(self):
        """Missing password field raises ValueError."""
        data = {"columns": ["other"], "rows": [["value"]]}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            
            with pytest.raises(ValueError, match="No password field"):
                parse_reset_response(f.name)
            
            os.unlink(f.name)


class TestPgpassManagement:
    """Tests for pgpass file management."""
    
    @pytest.fixture
    def temp_pgpass(self, tmp_path, monkeypatch):
        """Create a temporary pgpass file location."""
        pgpass_file = tmp_path / ".pgpass"
        monkeypatch.setattr("pg_connect.PGPASS_FILE", pgpass_file)
        return pgpass_file
    
    def test_load_empty_pgpass(self, temp_pgpass):
        """Load returns empty list when file doesn't exist."""
        entries = load_pgpass()
        assert entries == []
    
    def test_save_and_load_pgpass(self, temp_pgpass):
        """Save and reload entries."""
        entries = [{
            "host": "test.com",
            "port": 5432,
            "database": "postgres",
            "user": "admin",
            "password": "secret",
        }]
        save_pgpass(entries)
        
        loaded = load_pgpass()
        assert len(loaded) == 1
        assert loaded[0]["host"] == "test.com"
        assert loaded[0]["password"] == "secret"
    
    def test_pgpass_permissions(self, temp_pgpass):
        """Pgpass file has 0600 permissions."""
        entries = [{"host": "*", "port": "*", "database": "*", "user": "*", "password": "x"}]
        save_pgpass(entries)
        
        mode = temp_pgpass.stat().st_mode & 0o777
        assert mode == 0o600
    
    def test_pgpass_escapes_colons_in_host(self, temp_pgpass):
        """Colons in host field are escaped."""
        entries = [{
            "host": "host:with:colons",
            "port": 5432,
            "database": "db",
            "user": "user",
            "password": "pass",
        }]
        save_pgpass(entries)
        
        loaded = load_pgpass()
        assert loaded[0]["host"] == "host:with:colons"
    
    def test_pgpass_escapes_colons_in_password(self, temp_pgpass):
        """Colons in password field are escaped and round-trip correctly."""
        entries = [{
            "host": "test.com",
            "port": 5432,
            "database": "db",
            "user": "user",
            "password": "pass:with:colons",
        }]
        save_pgpass(entries)
        
        loaded = load_pgpass()
        assert len(loaded) == 1
        assert loaded[0]["password"] == "pass:with:colons"
    
    def test_pgpass_strips_newlines_from_password(self, temp_pgpass):
        """Newlines in password are stripped to prevent file corruption."""
        entries = [{
            "host": "test.com",
            "port": 5432,
            "database": "db",
            "user": "user",
            "password": "pass\nwith\nnewlines",
        }]
        save_pgpass(entries)
        
        loaded = load_pgpass()
        assert "\n" not in loaded[0]["password"]
        assert loaded[0]["password"] == "passwithnewlines"
    
    def test_find_pgpass_entry_exact(self, temp_pgpass):
        """Find exact matching pgpass entry."""
        entries = [{
            "host": "specific.com",
            "port": "5432",
            "database": "mydb",
            "user": "myuser",
            "password": "mypass",
        }]
        save_pgpass(entries)
        
        found = find_pgpass_entry("specific.com", 5432, "mydb", "myuser")
        assert found is not None
        assert found["password"] == "mypass"
    
    def test_find_pgpass_entry_wildcard(self, temp_pgpass):
        """Wildcard entries match any value."""
        entries = [{
            "host": "*",
            "port": "*",
            "database": "*",
            "user": "*",
            "password": "wildcard_pass",
        }]
        save_pgpass(entries)
        
        found = find_pgpass_entry("any.host.com", 9999, "anydb", "anyuser")
        assert found is not None
        assert found["password"] == "wildcard_pass"
    
    def test_upsert_creates_new_entry(self, temp_pgpass):
        """Upsert creates entry when none exists."""
        upsert_pgpass_entry("new.com", 5432, "db", "user", "newpass")
        
        loaded = load_pgpass()
        assert len(loaded) == 1
        assert loaded[0]["password"] == "newpass"
    
    def test_upsert_updates_existing_entry(self, temp_pgpass):
        """Upsert updates password when entry exists."""
        entries = [{
            "host": "update.com",
            "port": 5432,
            "database": "db",
            "user": "user",
            "password": "oldpass",
        }]
        save_pgpass(entries)
        
        upsert_pgpass_entry("update.com", 5432, "db", "user", "newpass")
        
        loaded = load_pgpass()
        assert len(loaded) == 1
        assert loaded[0]["password"] == "newpass"


class TestServiceFileManagement:
    """Tests for pg_service.conf file management."""
    
    @pytest.fixture
    def temp_service_file(self, tmp_path, monkeypatch):
        """Create a temporary service file location."""
        service_file = tmp_path / ".pg_service.conf"
        monkeypatch.setattr("pg_connect.PG_SERVICE_FILE", service_file)
        return service_file
    
    def test_save_and_get_service_entry(self, temp_service_file):
        """Save and retrieve a service entry."""
        params = {
            "host": "test.snowflakecomputing.com",
            "port": 5432,
            "database": "postgres",
            "user": "snowflake_admin",
            "sslmode": "require",
        }
        save_service_entry("myinstance", params)
        
        entry = get_service_entry("myinstance")
        assert entry is not None
        assert entry["host"] == "test.snowflakecomputing.com"
        assert entry["port"] == 5432
    
    def test_get_nonexistent_entry(self, temp_service_file):
        """Get returns None for missing entry."""
        entry = get_service_entry("nonexistent")
        assert entry is None
    
    def test_get_entry_missing_host(self, temp_service_file):
        """Entry without host field returns None."""
        # Manually create an invalid entry
        config = load_service_file()
        config.add_section("invalid")
        config.set("invalid", "port", "5432")
        with open(temp_service_file, "w") as f:
            config.write(f)
        
        entry = get_service_entry("invalid")
        assert entry is None
    
    def test_update_existing_entry(self, temp_service_file):
        """Saving same name updates existing entry."""
        params1 = {"host": "old.com", "port": 5432}
        params2 = {"host": "new.com", "port": 5433}
        
        save_service_entry("test", params1)
        save_service_entry("test", params2)
        
        entry = get_service_entry("test")
        assert entry["host"] == "new.com"
        assert entry["port"] == 5433


class TestSaveConnection:
    """Tests for save_connection combined operation."""
    
    @pytest.fixture
    def temp_pg_files(self, tmp_path, monkeypatch):
        """Create temporary service and pgpass file locations."""
        service_file = tmp_path / ".pg_service.conf"
        pgpass_file = tmp_path / ".pgpass"
        monkeypatch.setattr("pg_connect.PG_SERVICE_FILE", service_file)
        monkeypatch.setattr("pg_connect.PGPASS_FILE", pgpass_file)
        return {"service": service_file, "pgpass": pgpass_file}
    
    def test_save_single_user(self, temp_pg_files):
        """Save connection with single user/password."""
        params = {
            "host": "single.com",
            "port": 5432,
            "database": "postgres",
            "user": "myuser",
            "password": "mypass",
            "sslmode": "require",
        }
        result = save_connection("myconn", params)
        
        assert result["roles_saved"] == ["myuser"]
        
        # Check service file
        entry = get_service_entry("myconn")
        assert entry["host"] == "single.com"
        assert entry["user"] == "myuser"
        
        # Check pgpass
        pgpass_entry = find_pgpass_entry("single.com", 5432, "postgres", "myuser")
        assert pgpass_entry is not None
        assert pgpass_entry["password"] == "mypass"
    
    def test_save_multiple_access_roles(self, temp_pg_files):
        """Save connection with multiple access_roles from CREATE response."""
        params = {
            "host": "multi.snowflakecomputing.com",
            "port": 5432,
            "database": "postgres",
            "user": "snowflake_admin",
            "password": "admin_pass",
            "sslmode": "require",
            "access_roles": [
                {"name": "snowflake_admin", "password": "admin_pass"},
                {"name": "application", "password": "app_pass"},
            ]
        }
        result = save_connection("multiuser", params)
        
        # Both roles should be saved
        assert "snowflake_admin" in result["roles_saved"]
        assert "application" in result["roles_saved"]
        
        # Service file uses primary user
        entry = get_service_entry("multiuser")
        assert entry["user"] == "snowflake_admin"
        
        # Both users in pgpass
        admin_entry = find_pgpass_entry("multi.snowflakecomputing.com", 5432, "postgres", "snowflake_admin")
        assert admin_entry is not None
        assert admin_entry["password"] == "admin_pass"
        
        app_entry = find_pgpass_entry("multi.snowflakecomputing.com", 5432, "postgres", "application")
        assert app_entry is not None
        assert app_entry["password"] == "app_pass"
    
    def test_save_updates_existing_roles(self, temp_pg_files):
        """Saving again updates passwords for existing roles."""
        params1 = {
            "host": "update.com",
            "port": 5432,
            "database": "postgres",
            "user": "snowflake_admin",
            "password": "old_pass",
            "sslmode": "require",
            "access_roles": [
                {"name": "snowflake_admin", "password": "old_admin"},
                {"name": "application", "password": "old_app"},
            ]
        }
        save_connection("updatetest", params1)
        
        # Save again with new passwords
        params2 = {
            "host": "update.com",
            "port": 5432,
            "database": "postgres",
            "user": "snowflake_admin",
            "password": "new_pass",
            "sslmode": "require",
            "access_roles": [
                {"name": "snowflake_admin", "password": "new_admin"},
                {"name": "application", "password": "new_app"},
            ]
        }
        result = save_connection("updatetest", params2)
        
        assert result["password_updated"] is True
        
        # Check updated passwords
        admin_entry = find_pgpass_entry("update.com", 5432, "postgres", "snowflake_admin")
        assert admin_entry["password"] == "new_admin"
        
        app_entry = find_pgpass_entry("update.com", 5432, "postgres", "application")
        assert app_entry["password"] == "new_app"


class TestCLIOutputSecurity:
    """Tests that CLI output never exposes secrets."""
    
    @pytest.fixture
    def temp_pg_files(self, tmp_path, monkeypatch):
        """Create temporary service and pgpass file locations."""
        service_file = tmp_path / ".pg_service.conf"
        pgpass_file = tmp_path / ".pgpass"
        monkeypatch.setattr("pg_connect.PG_SERVICE_FILE", service_file)
        monkeypatch.setattr("pg_connect.PGPASS_FILE", pgpass_file)
        return {"service": service_file, "pgpass": pgpass_file}
    
    def test_from_response_output_hides_password(self, temp_pg_files, tmp_path):
        """CLI output from --from-response should not contain passwords."""
        import subprocess
        
        # Create a response file with passwords
        response_file = tmp_path / "create_response.json"
        response_data = {
            "columns": ["status", "host", "access_roles", "default_database"],
            "rows": [[
                "Instance created.",
                "test.snowflakecomputing.com",
                json.dumps({
                    "application": "SECRET_APP_PASSWORD_12345",
                    "snowflake_admin": "SECRET_ADMIN_PASSWORD_67890"
                }),
                "postgres"
            ]]
        }
        response_file.write_text(json.dumps(response_data))
        
        # Run CLI command
        script_path = Path(__file__).parent.parent / "scripts" / "pg_connect.py"
        env = os.environ.copy()
        env["PGSERVICEFILE"] = str(temp_pg_files["service"])
        env["PGPASSFILE"] = str(temp_pg_files["pgpass"])
        
        result = subprocess.run(
            [
                "python", str(script_path),
                "--from-response", str(response_file),
                "--connection-name", "test_conn",
                "--save"
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        
        output = result.stdout + result.stderr
        
        # Verify passwords are NOT in output
        assert "SECRET_APP_PASSWORD_12345" not in output
        assert "SECRET_ADMIN_PASSWORD_67890" not in output
        assert "access_roles" not in output.lower() or "access_roles" not in output
        
        # Verify safe fields ARE in output
        assert "test.snowflakecomputing.com" in output
        assert "has_password" in output or "True" in output
    
    def test_from_reset_response_output_hides_password(self, temp_pg_files, tmp_path):
        """CLI output from --from-reset-response should not contain passwords."""
        import subprocess
        
        # First create a service entry (required for reset)
        from pg_connect import save_service_entry
        save_service_entry("reset_test", {
            "host": "reset.snowflakecomputing.com",
            "port": 5432,
            "database": "postgres",
            "user": "snowflake_admin",
            "sslmode": "require",
        })
        
        # Create a reset response file with password
        reset_file = tmp_path / "reset_response.json"
        reset_data = {
            "query": "ALTER POSTGRES SERVICE reset_test RESET ACCESS FOR 'snowflake_admin';",
            "columns": ["password"],
            "rows": [["SECRET_RESET_PASSWORD_ABCDEF"]]
        }
        reset_file.write_text(json.dumps(reset_data))
        
        # Run CLI command
        script_path = Path(__file__).parent.parent / "scripts" / "pg_connect.py"
        env = os.environ.copy()
        env["PGSERVICEFILE"] = str(temp_pg_files["service"])
        env["PGPASSFILE"] = str(temp_pg_files["pgpass"])
        
        result = subprocess.run(
            [
                "python", str(script_path),
                "--from-reset-response", str(reset_file),
                "--connection-name", "reset_test"
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        
        output = result.stdout + result.stderr
        
        # Verify password is NOT in output
        assert "SECRET_RESET_PASSWORD_ABCDEF" not in output
    
    def test_json_output_hides_secrets(self, temp_pg_files, tmp_path):
        """JSON output mode should also hide secrets."""
        import subprocess
        
        # Create a response file with passwords
        response_file = tmp_path / "create_response.json"
        response_data = {
            "columns": ["host", "access_roles"],
            "rows": [[
                "json.snowflakecomputing.com",
                json.dumps({
                    "snowflake_admin": "JSON_SECRET_PASSWORD_XYZ"
                })
            ]]
        }
        response_file.write_text(json.dumps(response_data))
        
        # Run CLI command with --json
        script_path = Path(__file__).parent.parent / "scripts" / "pg_connect.py"
        env = os.environ.copy()
        env["PGSERVICEFILE"] = str(temp_pg_files["service"])
        env["PGPASSFILE"] = str(temp_pg_files["pgpass"])
        
        result = subprocess.run(
            [
                "python", str(script_path),
                "--from-response", str(response_file),
                "--connection-name", "json_test",
                "--save",
                "--json"
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        
        output = result.stdout + result.stderr
        
        # Verify password is NOT in JSON output
        assert "JSON_SECRET_PASSWORD_XYZ" not in output
        
        # Parse JSON output and verify structure
        if result.stdout.strip():
            output_json = json.loads(result.stdout)
            assert "password" not in output_json.get("data", {})
            assert "access_roles" not in output_json.get("data", {})

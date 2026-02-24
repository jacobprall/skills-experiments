#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Skills Benchmark Orchestration Script
#
# Usage:
#   ./run_benchmark.sh setup-data       # Load test data into Snowflake
#   ./run_benchmark.sh setup-bundled    # Configure Arm A (bundled skills)
#   ./run_benchmark.sh setup-standard   # Configure Arm B (standard library)
#   ./run_benchmark.sh clean-slate      # Reset Snowflake objects between tests
#   ./run_benchmark.sh restore          # Restore original bundled skills
#   ./run_benchmark.sh audit <transcript_file>  # Count steps/tokens from transcript
#   ./run_benchmark.sh query-audit <start> <end> # Pull Snowflake query history
# =============================================================================

# --- Configuration -----------------------------------------------------------

CORTEX_VERSION="1.0.20+045458.1785e665caa4"
CORTEX_BASE="$HOME/.local/share/cortex/${CORTEX_VERSION}"
BUNDLED_DIR="${CORTEX_BASE}/bundled_skills"
BUNDLED_BACKUP="${CORTEX_BASE}/bundled_skills.bak"
STANDARD_LIB="$HOME/Desktop/snowflake-standard-skills-library"
SNOWFLAKE_CONN="snowhouse"
ROLE="SNOWFLAKE_LEARNING_ADMIN"
WAREHOUSE="BENCHMARK_WH"
DATABASE="SNOWFLAKE_LEARNING_DB"

# --- Helpers -----------------------------------------------------------------

log()  { echo "[benchmark] $*"; }
err()  { echo "[benchmark] ERROR: $*" >&2; exit 1; }
confirm() {
    read -rp "[benchmark] $1 [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || { log "Aborted."; exit 0; }
}

run_sql() {
    local description="$1"
    local sql="$2"
    log "Running: ${description}"
    cortex sql --connection "${SNOWFLAKE_CONN}" -q "${sql}" 2>&1 || true
}

# --- Commands ----------------------------------------------------------------

cmd_setup_data() {
    log "Setting up test data in ${DATABASE}..."
    confirm "This will CREATE OR REPLACE tables in ${DATABASE}.RAW. Continue?"

    run_sql "Create warehouse" \
        "CREATE WAREHOUSE IF NOT EXISTS ${WAREHOUSE} WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE;"

    run_sql "Create database and schemas" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         CREATE DATABASE IF NOT EXISTS ${DATABASE};
         CREATE SCHEMA IF NOT EXISTS ${DATABASE}.RAW;
         CREATE SCHEMA IF NOT EXISTS ${DATABASE}.STAGING;
         CREATE SCHEMA IF NOT EXISTS ${DATABASE}.ANALYTICS;
         CREATE SCHEMA IF NOT EXISTS ${DATABASE}.GOVERNANCE;"

    run_sql "Create CUSTOMERS table" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         CREATE OR REPLACE TABLE ${DATABASE}.RAW.CUSTOMERS (
             customer_id STRING, customer_name STRING, email STRING,
             phone STRING, ssn STRING, segment STRING,
             department STRING, date_of_birth DATE
         );"

    run_sql "Create ORDERS table" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         CREATE OR REPLACE TABLE ${DATABASE}.RAW.ORDERS (
             order_id STRING, customer_id STRING,
             order_date TIMESTAMP, total_amount NUMBER(10,2), status STRING
         );"

    run_sql "Insert customer data" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         INSERT INTO ${DATABASE}.RAW.CUSTOMERS
         SELECT
             'CUST-' || SEQ4(),
             RANDSTR(8, RANDOM()) || ' ' || RANDSTR(10, RANDOM()),
             LOWER(RANDSTR(8, RANDOM())) || '@example.com',
             '+1-555-' || LPAD(UNIFORM(1000000, 9999999, RANDOM())::STRING, 7, '0'),
             LPAD(UNIFORM(100000000, 999999999, RANDOM())::STRING, 9, '0'),
             CASE UNIFORM(1,4,RANDOM()) WHEN 1 THEN 'Enterprise' WHEN 2 THEN 'SMB' WHEN 3 THEN 'Startup' ELSE 'Consumer' END,
             CASE UNIFORM(1,4,RANDOM()) WHEN 1 THEN 'Sales' WHEN 2 THEN 'Engineering' WHEN 3 THEN 'Marketing' ELSE 'Support' END,
             DATEADD('day', -UNIFORM(7000, 25000, RANDOM()), CURRENT_DATE())
         FROM TABLE(GENERATOR(ROWCOUNT => 500));"

    run_sql "Insert order data" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         INSERT INTO ${DATABASE}.RAW.ORDERS
         SELECT
             'ORD-' || SEQ4(),
             'CUST-' || UNIFORM(0, 499, RANDOM()),
             DATEADD('hour', -UNIFORM(1, 8760, RANDOM()), CURRENT_TIMESTAMP()),
             ROUND(UNIFORM(10, 5000, RANDOM()) + UNIFORM(0, 99, RANDOM()) / 100, 2),
             CASE UNIFORM(1,5,RANDOM()) WHEN 1 THEN 'PENDING' WHEN 2 THEN 'SHIPPED' WHEN 3 THEN 'DELIVERED' WHEN 4 THEN 'RETURNED' ELSE 'CANCELLED' END
         FROM TABLE(GENERATOR(ROWCOUNT => 5000));"

    run_sql "Create test roles" \
        "USE ROLE ${ROLE};
         CREATE ROLE IF NOT EXISTS ANALYST_RESTRICTED;
         CREATE ROLE IF NOT EXISTS DATA_STEWARD;
         GRANT USAGE ON DATABASE ${DATABASE} TO ROLE ANALYST_RESTRICTED;
         GRANT USAGE ON ALL SCHEMAS IN DATABASE ${DATABASE} TO ROLE ANALYST_RESTRICTED;
         GRANT SELECT ON ALL TABLES IN SCHEMA ${DATABASE}.RAW TO ROLE ANALYST_RESTRICTED;
         GRANT USAGE ON WAREHOUSE ${WAREHOUSE} TO ROLE ANALYST_RESTRICTED;
         GRANT USAGE ON DATABASE ${DATABASE} TO ROLE DATA_STEWARD;
         GRANT USAGE ON ALL SCHEMAS IN DATABASE ${DATABASE} TO ROLE DATA_STEWARD;
         GRANT SELECT ON ALL TABLES IN SCHEMA ${DATABASE}.RAW TO ROLE DATA_STEWARD;
         GRANT USAGE ON WAREHOUSE ${WAREHOUSE} TO ROLE DATA_STEWARD;
         GRANT ROLE ANALYST_RESTRICTED TO ROLE ${ROLE};
         GRANT ROLE DATA_STEWARD TO ROLE ${ROLE};"

    run_sql "Verify data" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         SELECT 'CUSTOMERS' AS tbl, COUNT(*) AS cnt FROM ${DATABASE}.RAW.CUSTOMERS
         UNION ALL
         SELECT 'ORDERS', COUNT(*) FROM ${DATABASE}.RAW.ORDERS;"

    log "Data setup complete."
}

cmd_setup_bundled() {
    log "Configuring Arm A: Bundled Skills"

    # If backup exists, restore it first
    if [[ -d "${BUNDLED_BACKUP}" ]]; then
        log "Restoring bundled skills from backup..."
        if [[ -d "${BUNDLED_DIR}" ]] || [[ -L "${BUNDLED_DIR}" ]]; then
            rm -rf "${BUNDLED_DIR}"
        fi
        mv "${BUNDLED_BACKUP}" "${BUNDLED_DIR}"
        log "Bundled skills restored."
    fi

    # Verify
    if [[ -d "${BUNDLED_DIR}" ]] && [[ ! -L "${BUNDLED_DIR}" ]]; then
        local count
        count=$(find "${BUNDLED_DIR}" -name "SKILL.md" | wc -l | tr -d ' ')
        log "Bundled skills active: ${count} SKILL.md files found"
    else
        err "Bundled skills directory not found or is a symlink. Something is wrong."
    fi

    log ""
    log "Arm A ready. Start Cortex Code CLI normally:"
    log "  cortex"
    log ""
    log "Use connection: ${SNOWFLAKE_CONN}"
    log "Set role:       USE ROLE ${ROLE};"
    log "Set warehouse:  USE WAREHOUSE ${WAREHOUSE};"
}

cmd_setup_standard() {
    log "Configuring Arm B: Standard Skills Library"

    # Verify standard library exists
    if [[ ! -d "${STANDARD_LIB}" ]]; then
        err "Standard library not found at ${STANDARD_LIB}"
    fi

    if [[ ! -f "${STANDARD_LIB}/router.md" ]]; then
        err "Standard library missing router.md entry point at ${STANDARD_LIB}/router.md"
    fi

    # Back up bundled skills if not already backed up
    if [[ -d "${BUNDLED_DIR}" ]] && [[ ! -L "${BUNDLED_DIR}" ]] && [[ ! -d "${BUNDLED_BACKUP}" ]]; then
        log "Backing up bundled skills to ${BUNDLED_BACKUP}..."
        mv "${BUNDLED_DIR}" "${BUNDLED_BACKUP}"
    elif [[ -L "${BUNDLED_DIR}" ]]; then
        log "Bundled dir is already a symlink, removing it..."
        rm "${BUNDLED_DIR}"
    elif [[ -d "${BUNDLED_BACKUP}" ]]; then
        log "Backup already exists. Removing current bundled_skills..."
        rm -rf "${BUNDLED_DIR}"
    fi

    # Create a bundled_skills directory that contains the standard library content
    # We structure it so the agent discovers the standard library files
    log "Linking standard library into bundled_skills path..."
    mkdir -p "${BUNDLED_DIR}"

    # Copy the standard library into the bundled skills directory
    # The agent reads from bundled_skills/, so we place the library there
    cp -R "${STANDARD_LIB}/router.md" "${BUNDLED_DIR}/"
    cp -R "${STANDARD_LIB}/routers" "${BUNDLED_DIR}/" 2>/dev/null || true
    cp -R "${STANDARD_LIB}/playbooks" "${BUNDLED_DIR}/" 2>/dev/null || true
    cp -R "${STANDARD_LIB}/primitives" "${BUNDLED_DIR}/" 2>/dev/null || true

    # Create a minimal __init__.py so the directory is recognized
    echo "# Standard Skills Library" > "${BUNDLED_DIR}/__init__.py"

    # Verify
    local count
    count=$(find "${BUNDLED_DIR}" -name "*.md" | wc -l | tr -d ' ')
    log "Standard library installed: ${count} .md files in bundled_skills path"
    log ""
    log "NOTE: Bundled SKILL.md files removed. Only standard library content is present."
    log "      The agent will discover router.md, routers/, playbooks/, and primitives/."
    log ""
    log "Arm B ready. Start Cortex Code CLI normally:"
    log "  cortex"
    log ""
    log "Use connection: ${SNOWFLAKE_CONN}"
    log "Set role:       USE ROLE ${ROLE};"
    log "Set warehouse:  USE WAREHOUSE ${WAREHOUSE};"
}

cmd_clean_slate() {
    log "Resetting Snowflake objects between tests..."
    confirm "This will drop STAGING, ANALYTICS, GOVERNANCE schemas and masking policies. Continue?"

    run_sql "Drop dynamic tables" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         DROP DYNAMIC TABLE IF EXISTS ${DATABASE}.ANALYTICS.ORDER_SUMMARY;
         DROP DYNAMIC TABLE IF EXISTS ${DATABASE}.ANALYTICS.DAILY_METRICS;
         DROP DYNAMIC TABLE IF EXISTS ${DATABASE}.STAGING.ENRICHED_ORDERS;
         DROP DYNAMIC TABLE IF EXISTS ${DATABASE}.STAGING.CLEANED_ORDERS;"

    run_sql "Recreate schemas" \
        "USE ROLE ${ROLE};
         DROP SCHEMA IF EXISTS ${DATABASE}.STAGING CASCADE;
         DROP SCHEMA IF EXISTS ${DATABASE}.ANALYTICS CASCADE;
         DROP SCHEMA IF EXISTS ${DATABASE}.GOVERNANCE CASCADE;
         CREATE SCHEMA ${DATABASE}.STAGING;
         CREATE SCHEMA ${DATABASE}.ANALYTICS;
         CREATE SCHEMA ${DATABASE}.GOVERNANCE;"

    # Drop masking policies - need to unset from columns first, then drop
    log "Checking for masking policies to clean up..."
    run_sql "Show masking policies" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         SHOW MASKING POLICIES IN SCHEMA ${DATABASE}.RAW;"

    run_sql "Show masking policies in governance" \
        "USE ROLE ${ROLE};
         SHOW MASKING POLICIES IN DATABASE ${DATABASE};"

    log ""
    log "NOTE: If masking policies were found above, you may need to manually"
    log "      UNSET them from columns and DROP them before the next test."
    log "      The agent names policies differently each run, so this can't be"
    log "      fully automated. Run these if needed:"
    log ""
    log "  ALTER TABLE ${DATABASE}.RAW.CUSTOMERS MODIFY COLUMN email UNSET MASKING POLICY;"
    log "  ALTER TABLE ${DATABASE}.RAW.CUSTOMERS MODIFY COLUMN phone UNSET MASKING POLICY;"
    log "  ALTER TABLE ${DATABASE}.RAW.CUSTOMERS MODIFY COLUMN ssn UNSET MASKING POLICY;"
    log "  -- etc. for any other columns, then DROP MASKING POLICY for each"
    log ""

    run_sql "Disable change tracking" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         ALTER TABLE ${DATABASE}.RAW.ORDERS SET CHANGE_TRACKING = FALSE;
         ALTER TABLE ${DATABASE}.RAW.CUSTOMERS SET CHANGE_TRACKING = FALSE;"

    run_sql "Verify source data intact" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         SELECT 'CUSTOMERS' AS tbl, COUNT(*) AS cnt FROM ${DATABASE}.RAW.CUSTOMERS
         UNION ALL
         SELECT 'ORDERS', COUNT(*) FROM ${DATABASE}.RAW.ORDERS;"

    log "Clean slate complete."
}

cmd_restore() {
    log "Restoring original bundled skills..."

    if [[ ! -d "${BUNDLED_BACKUP}" ]]; then
        if [[ -d "${BUNDLED_DIR}" ]] && [[ ! -L "${BUNDLED_DIR}" ]]; then
            local count
            count=$(find "${BUNDLED_DIR}" -name "SKILL.md" | wc -l | tr -d ' ')
            if [[ "${count}" -gt "0" ]]; then
                log "Bundled skills appear to already be in place (${count} SKILL.md files). Nothing to restore."
                exit 0
            fi
        fi
        err "No backup found at ${BUNDLED_BACKUP}. Cannot restore."
    fi

    # Remove current (standard library or broken state)
    if [[ -d "${BUNDLED_DIR}" ]] || [[ -L "${BUNDLED_DIR}" ]]; then
        rm -rf "${BUNDLED_DIR}"
    fi

    mv "${BUNDLED_BACKUP}" "${BUNDLED_DIR}"

    local count
    count=$(find "${BUNDLED_DIR}" -name "SKILL.md" | wc -l | tr -d ' ')
    log "Restored. ${count} SKILL.md files now in bundled_skills."
    log ""
    log "Cortex Code is back to its default configuration."
}

cmd_audit() {
    local transcript_file="${1:-}"
    if [[ -z "${transcript_file}" ]]; then
        err "Usage: $0 audit <transcript_file>"
    fi
    if [[ ! -f "${transcript_file}" ]]; then
        err "File not found: ${transcript_file}"
    fi

    log "Auditing transcript: ${transcript_file}"
    log "---"

    # Line count
    local lines
    lines=$(wc -l < "${transcript_file}" | tr -d ' ')
    log "Total lines: ${lines}"

    # Tool calls (various patterns Cortex Code uses)
    local tool_calls
    tool_calls=$(grep -cEi 'tool:|invoke|function_call|<tool|snowflake_sql_execute|bash.*command|skill.*load' "${transcript_file}" 2>/dev/null || echo "0")
    log "Tool invocations (approx): ${tool_calls}"

    # SQL executions
    local sql_count
    sql_count=$(grep -ci 'snowflake_sql_execute\|execute.*sql\|```sql' "${transcript_file}" 2>/dev/null || echo "0")
    log "SQL executions (approx): ${sql_count}"

    # Skill loads
    local skill_loads
    skill_loads=$(grep -ci 'skill.*load\|SKILL\.md\|loading.*skill' "${transcript_file}" 2>/dev/null || echo "0")
    log "Skill loads (approx): ${skill_loads}"

    # User messages (interventions proxy)
    local user_msgs
    user_msgs=$(grep -ci '^human:\|^user:\|^H:' "${transcript_file}" 2>/dev/null || echo "0")
    log "User messages: ${user_msgs}"

    # Token approximation (if tiktoken available)
    if command -v python3 &>/dev/null; then
        local tokens
        tokens=$(python3 -c "
try:
    import tiktoken
    enc = tiktoken.encoding_for_model('gpt-4')
    with open('${transcript_file}') as f:
        print(len(enc.encode(f.read())))
except ImportError:
    print('tiktoken not installed')
except Exception as e:
    print(f'error: {e}')
" 2>/dev/null)
        log "Approximate tokens: ${tokens}"
    else
        log "Approximate tokens: (python3 not available)"
    fi

    log "---"
    log "For precise step counts, manually walk the transcript."
}

cmd_query_audit() {
    local start="${1:-}"
    local end="${2:-}"
    if [[ -z "${start}" ]] || [[ -z "${end}" ]]; then
        err "Usage: $0 query-audit <start_timestamp> <end_timestamp>"
        err "  Example: $0 query-audit '2026-02-24 10:00:00' '2026-02-24 11:00:00'"
    fi

    log "Pulling query history from ${start} to ${end}..."

    run_sql "Query history for benchmark" \
        "USE ROLE ${ROLE};
         USE WAREHOUSE ${WAREHOUSE};
         SELECT
             query_id,
             SUBSTR(query_text, 1, 80) AS query_preview,
             start_time,
             DATEDIFF('second', start_time, end_time) AS duration_sec,
             rows_produced,
             error_code,
             SUBSTR(error_message, 1, 60) AS error_preview
         FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
             DATE_RANGE_START => '${start}'::TIMESTAMP_LTZ,
             DATE_RANGE_END => '${end}'::TIMESTAMP_LTZ,
             RESULT_LIMIT => 500
         ))
         WHERE warehouse_name = '${WAREHOUSE}'
         ORDER BY start_time;"
}

# --- Main --------------------------------------------------------------------

case "${1:-}" in
    setup-data)     cmd_setup_data ;;
    setup-bundled)  cmd_setup_bundled ;;
    setup-standard) cmd_setup_standard ;;
    clean-slate)    cmd_clean_slate ;;
    restore)        cmd_restore ;;
    audit)          cmd_audit "${2:-}" ;;
    query-audit)    cmd_query_audit "${2:-}" "${3:-}" ;;
    *)
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  setup-data       Load test data into Snowflake (run once)"
        echo "  setup-bundled    Configure Arm A: bundled skills (default)"
        echo "  setup-standard   Configure Arm B: standard library only"
        echo "  clean-slate      Reset Snowflake objects between tests"
        echo "  restore          Restore original bundled skills after experiment"
        echo "  audit <file>     Count steps/tokens from exported transcript"
        echo "  query-audit <start> <end>  Pull Snowflake query history for time range"
        echo ""
        echo "Typical workflow:"
        echo "  $0 setup-data                    # once"
        echo "  $0 setup-bundled                 # Arm A"
        echo "  # run 3 tests, clean-slate between each"
        echo "  $0 setup-standard                # Arm B"
        echo "  # run 3 tests, clean-slate between each"
        echo "  $0 restore                       # put bundled skills back"
        ;;
esac

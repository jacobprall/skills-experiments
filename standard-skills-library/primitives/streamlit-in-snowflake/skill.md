---
type: primitive
name: streamlit-in-snowflake
domain: app-development
snowflake_docs: "https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit"
---

# Streamlit in Snowflake

Build and deploy Streamlit apps that run natively in Snowflake. Covers Snowflake-specific connection patterns, deployment, and session management.

## Syntax

### Deploy via snow CLI

```bash
snow streamlit deploy <app_name> \
  --database <db> \
  --schema <schema> \
  --replace
```

Requires a `snowflake.yml` configuration file in the project root.

### snowflake.yml

```yaml
definition_version: "2"
entities:
  my_app:
    type: streamlit
    identifier:
      name: <app_name>
    title: "<App Title>"
    main_file: app.py
    pages_dir: pages/
    stage: <stage_name>
```

### Snowflake connection in app code

```python
import streamlit as st
from snowflake.snowpark.context import get_active_session

# In Snowflake (deployed)
session = get_active_session()

# For local development
conn = st.connection("snowflake")
df = conn.query("SELECT * FROM my_table LIMIT 10")
```

## Parameters

### Session patterns

| Context | How to Get Session | Notes |
|---------|-------------------|-------|
| Deployed in Snowflake | `get_active_session()` | Session is pre-configured, no credentials needed |
| Local development | `st.connection("snowflake")` | Uses `~/.snowflake/connections.toml` or secrets |
| Dual-mode | Check environment, fallback | See example below |

### Dual-mode pattern

```python
import streamlit as st

try:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
except Exception:
    conn = st.connection("snowflake")
    session = conn.session()
```

## Constraints

- Deployed apps use the owning role's privileges — users don't authenticate separately.
- External network access requires an External Access Integration (EAI).
- Package availability is limited to the Snowflake Anaconda channel for deployed apps.
- `st.secrets` is not available when deployed in Snowflake — use `get_active_session()` instead.
- File uploads and downloads are supported but files are stored in a temporary stage.

## Examples

### Minimal deployed app

```python
import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()

st.title("Sales Dashboard")
df = session.table("ANALYTICS.PUBLIC.DAILY_SALES").to_pandas()
st.dataframe(df)
st.bar_chart(df.set_index("DATE")["REVENUE"])
```

### Deploy

```bash
snow streamlit deploy sales_dashboard --database analytics --schema apps --replace
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using `st.secrets` for Snowflake credentials in deployed apps | `st.secrets` not available in Snowflake runtime | Use `get_active_session()` |
| Installing pip packages at runtime | Not supported in deployed Snowflake apps | Declare all dependencies in `snowflake.yml` or use Anaconda channel packages |
| Loading entire large tables into pandas | Memory limits in Snowflake-hosted apps | Use Snowpark pushdown: filter and aggregate before `.to_pandas()` |

## References

- `primitives/spcs-deployment`
- [Snowflake Docs: Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)

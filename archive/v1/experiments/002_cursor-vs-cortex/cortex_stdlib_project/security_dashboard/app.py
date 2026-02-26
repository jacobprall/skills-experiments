import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()

st.set_page_config(page_title="Security Ticket Monitor", layout="wide")
st.title("Security Incident Monitor")
st.caption("Live dashboard for the security team -- enriched with AI classification, PII detection, and severity scoring.")

# --- Sidebar filters ---
st.sidebar.header("Filters")

severity_options = ["All", "critical", "high", "medium", "low"]
selected_severity = st.sidebar.selectbox("Security Severity", severity_options)

category_options = ["All", "security_incident", "access_management"]
selected_category = st.sidebar.selectbox("Ticket Category", category_options)

pii_filter = st.sidebar.selectbox("PII Detected", ["All", "Yes", "No"])

show_open_only = st.sidebar.checkbox("Open tickets only", value=False)

# --- Load data ---
query = """
SELECT TICKET_ID, CUSTOMER_ID, SUBJECT, BODY, PRIORITY,
       CREATED_AT, RESOLVED_AT, TICKET_CATEGORY, CONTAINS_PII,
       PII_TYPES_FOUND, SECURITY_SEVERITY, IS_SECURITY_RELATED
FROM SNOWFLAKE_LEARNING_DB.ANALYTICS_CURSOR.SECURITY_TICKETS_ENRICHED
WHERE IS_SECURITY_RELATED = TRUE
"""

conditions = []
if selected_severity != "All":
    conditions.append(f"SECURITY_SEVERITY = '{selected_severity}'")
if selected_category != "All":
    conditions.append(f"TICKET_CATEGORY = '{selected_category}'")
if pii_filter == "Yes":
    conditions.append("CONTAINS_PII = TRUE")
elif pii_filter == "No":
    conditions.append("CONTAINS_PII = FALSE")
if show_open_only:
    conditions.append("RESOLVED_AT IS NULL")

if conditions:
    query += " AND " + " AND ".join(conditions)

query += " ORDER BY CREATED_AT DESC"

df = session.sql(query).to_pandas()

# --- KPI Row ---
col1, col2, col3, col4, col5 = st.columns(5)

total = len(df)
open_count = int(df["RESOLVED_AT"].isna().sum())
critical_count = int((df["SECURITY_SEVERITY"] == "critical").sum())
high_count = int((df["SECURITY_SEVERITY"] == "high").sum())
pii_count = int((df["CONTAINS_PII"] == True).sum())

col1.metric("Total Security Tickets", total)
col2.metric("Open (Unresolved)", open_count)
col3.metric("Critical Severity", critical_count)
col4.metric("High Severity", high_count)
col5.metric("PII Flagged", pii_count)

st.divider()

# --- Charts ---
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Tickets by Severity")
    if not df.empty:
        severity_counts = df["SECURITY_SEVERITY"].value_counts().reset_index()
        severity_counts.columns = ["Severity", "Count"]
        st.bar_chart(severity_counts, x="Severity", y="Count")
    else:
        st.info("No tickets match the current filters.")

with chart_col2:
    st.subheader("Tickets by Category")
    if not df.empty:
        cat_counts = df["TICKET_CATEGORY"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Count"]
        st.bar_chart(cat_counts, x="Category", y="Count")
    else:
        st.info("No tickets match the current filters.")

st.divider()

# --- Ticket table ---
st.subheader("Security Tickets Detail")

if not df.empty:
    display_cols = [
        "TICKET_ID", "SUBJECT", "TICKET_CATEGORY", "SECURITY_SEVERITY",
        "PRIORITY", "CONTAINS_PII", "PII_TYPES_FOUND", "CUSTOMER_ID",
        "CREATED_AT", "RESOLVED_AT"
    ]
    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "TICKET_ID": "Ticket",
            "SUBJECT": "Subject",
            "TICKET_CATEGORY": "Category",
            "SECURITY_SEVERITY": "Severity",
            "PRIORITY": "Priority",
            "CONTAINS_PII": "PII?",
            "PII_TYPES_FOUND": "PII Types",
            "CUSTOMER_ID": "Customer",
            "CREATED_AT": st.column_config.DatetimeColumn("Created", format="YYYY-MM-DD HH:mm"),
            "RESOLVED_AT": st.column_config.DatetimeColumn("Resolved", format="YYYY-MM-DD HH:mm"),
        },
    )
else:
    st.info("No security tickets match the current filters.")

# --- Drill-down ---
st.divider()
st.subheader("Ticket Detail View")

if not df.empty:
    ticket_ids = df["TICKET_ID"].tolist()
    selected_ticket = st.selectbox("Select a ticket to view details", ticket_ids)

    if selected_ticket:
        row = df[df["TICKET_ID"] == selected_ticket].iloc[0]
        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            st.markdown(f"**Ticket:** {row['TICKET_ID']}")
            st.markdown(f"**Subject:** {row['SUBJECT']}")
            st.markdown(f"**Category:** {row['TICKET_CATEGORY']}")
            st.markdown(f"**Severity:** {row['SECURITY_SEVERITY']}")
            st.markdown(f"**Priority:** {row['PRIORITY']}")
        with detail_col2:
            st.markdown(f"**Customer:** {row['CUSTOMER_ID']}")
            st.markdown(f"**PII Detected:** {row['CONTAINS_PII']}")
            st.markdown(f"**PII Types:** {row['PII_TYPES_FOUND']}")
            st.markdown(f"**Created:** {row['CREATED_AT']}")
            st.markdown(f"**Resolved:** {row['RESOLVED_AT']}")
        st.markdown("**Full Description:**")
        st.text_area("", value=str(row["BODY"]), height=200, disabled=True, label_visibility="collapsed")

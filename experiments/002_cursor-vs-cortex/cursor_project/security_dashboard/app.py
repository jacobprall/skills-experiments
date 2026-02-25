import streamlit as st
from snowflake.snowpark.context import get_active_session
import datetime

session = get_active_session()

st.set_page_config(page_title="Security Incident Monitor", layout="wide")

st.title("Security Incident Monitor")
st.caption("Live view of security-related support tickets enriched with AI classification and severity scoring")

# ── Fetch data ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    return session.sql("""
        SELECT *
        FROM SNOWFLAKE_LEARNING_DB.ANALYTICS_CURSOR.SECURITY_DASHBOARD_VW
        ORDER BY CREATED_AT DESC
    """).to_pandas()

df = load_data()

if df.empty:
    st.warning("No security tickets visible. You may not have the required role to view this data.")
    st.stop()

# ── KPI row ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

open_tickets = df[df["STATUS"] == "OPEN"]
pii_tickets = df[df["CONTAINS_PII"] == True]
high_sev = df[df["SEVERITY_SCORE"] >= 4]

col1.metric("Total Security Tickets", len(df))
col2.metric("Open", len(open_tickets))
col3.metric("Contain PII", len(pii_tickets))
col4.metric("High/Critical (4-5)", len(high_sev))
col5.metric("Avg Severity", f"{df['SEVERITY_SCORE'].mean():.1f}")

st.divider()

# ── Filters ─────────────────────────────────────────────────────────────────
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

with filter_col1:
    status_filter = st.multiselect(
        "Status", options=["OPEN", "RESOLVED"], default=["OPEN", "RESOLVED"]
    )
with filter_col2:
    classification_filter = st.multiselect(
        "Classification",
        options=sorted(df["SECURITY_CLASSIFICATION"].unique()),
        default=sorted(df["SECURITY_CLASSIFICATION"].unique()),
    )
with filter_col3:
    severity_range = st.slider("Severity Score", 1, 5, (1, 5))
with filter_col4:
    pii_filter = st.selectbox("PII Flag", ["All", "Contains PII", "No PII"])

filtered = df[
    (df["STATUS"].isin(status_filter))
    & (df["SECURITY_CLASSIFICATION"].isin(classification_filter))
    & (df["SEVERITY_SCORE"] >= severity_range[0])
    & (df["SEVERITY_SCORE"] <= severity_range[1])
]
if pii_filter == "Contains PII":
    filtered = filtered[filtered["CONTAINS_PII"] == True]
elif pii_filter == "No PII":
    filtered = filtered[filtered["CONTAINS_PII"] == False]

st.divider()

# ── Charts ──────────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Severity Distribution")
    sev_counts = filtered.groupby("SEVERITY_LABEL").size().reset_index(name="count")
    st.bar_chart(sev_counts, x="SEVERITY_LABEL", y="count", color="#FF4B4B")

with chart_col2:
    st.subheader("Tickets by Priority")
    pri_counts = filtered.groupby("PRIORITY").size().reset_index(name="count")
    st.bar_chart(pri_counts, x="PRIORITY", y="count", color="#1F77B4")

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    st.subheader("Open vs Resolved")
    status_counts = filtered.groupby("STATUS").size().reset_index(name="count")
    st.bar_chart(status_counts, x="STATUS", y="count", color="#2CA02C")

with chart_col4:
    st.subheader("Classification Breakdown")
    class_counts = (
        filtered.groupby("SECURITY_CLASSIFICATION").size().reset_index(name="count")
    )
    st.bar_chart(
        class_counts, x="SECURITY_CLASSIFICATION", y="count", color="#FF7F0E"
    )

st.divider()

# ── Ticket table ────────────────────────────────────────────────────────────
st.subheader(f"Security Tickets ({len(filtered)} shown)")

display_cols = [
    "TICKET_ID",
    "SEVERITY_SCORE",
    "SEVERITY_LABEL",
    "SECURITY_CLASSIFICATION",
    "CONTAINS_PII",
    "PRIORITY",
    "STATUS",
    "SUBJECT",
    "HOURS_OPEN",
    "CREATED_AT",
]
st.dataframe(
    filtered[display_cols].sort_values("SEVERITY_SCORE", ascending=False),
    use_container_width=True,
    hide_index=True,
)

# ── Ticket detail expander ──────────────────────────────────────────────────
st.subheader("Ticket Detail")
selected_ticket = st.selectbox(
    "Select a ticket to view details",
    options=filtered["TICKET_ID"].tolist(),
    index=0 if len(filtered) > 0 else None,
)

if selected_ticket:
    ticket = filtered[filtered["TICKET_ID"] == selected_ticket].iloc[0]
    detail_col1, detail_col2 = st.columns([2, 1])

    with detail_col1:
        st.markdown(f"**Subject:** {ticket['SUBJECT']}")
        st.markdown(f"**Body:**")
        st.text(ticket["BODY"])

    with detail_col2:
        st.markdown(f"**Severity:** {ticket['SEVERITY_SCORE']}/5 — {ticket['SEVERITY_LABEL']}")
        st.markdown(f"**Classification:** {ticket['SECURITY_CLASSIFICATION']}")
        st.markdown(f"**Contains PII:** {'Yes' if ticket['CONTAINS_PII'] else 'No'}")
        st.markdown(f"**Priority:** {ticket['PRIORITY']}")
        st.markdown(f"**Status:** {ticket['STATUS']}")
        st.markdown(f"**Hours Open:** {ticket['HOURS_OPEN']}")
        st.markdown(f"**AI Reasoning:**")
        st.info(ticket["SEVERITY_REASONING"])

# ── Footer ──────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"Data refreshes every 5 minutes via dynamic table. "
    f"Last enrichment run visible in data. "
    f"Dashboard protected by row access policy — only SNOWFLAKE_LEARNING_ADMIN_ROLE can view."
)

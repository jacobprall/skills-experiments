---
type: primitive
name: openflow
domain: data-transformation
snowflake_docs: "https://docs.snowflake.com/en/user-guide/data-load-snowpipe-streaming-overview"
tested_on:
  snowflake_version: "8.23"
  test_date: "2026-02-15"
  test_account_type: "enterprise"
last_reviewed: "2026-02-15"
---

# OpenFlow

Data integration platform built on Apache NiFi for building and managing data connectors within Snowflake. Handles connector-based ingestion and data movement.

## Syntax

### Session prerequisites

OpenFlow operations require the `nipyapi` Python package:

```bash
pip install nipyapi>=0.21.0
```

### Core operations

OpenFlow uses a REST API via NiFi. Primary operations:

| Operation | Category | Description |
|-----------|----------|-------------|
| Check connector status | Primary | Verify running connectors and their health |
| Create connector | Primary | Set up a new data connector (source or destination) |
| Start/stop connector | Primary | Control connector execution state |
| Monitor throughput | Primary | Check data flow rates and backpressure |
| Troubleshoot errors | Secondary | Diagnose failed connectors or data quality issues |
| Update connector config | Secondary | Modify connection parameters, schedules |
| View connector logs | Secondary | Access NiFi provenance and bulletin board |
| Manage processor groups | Advanced | Organize connectors into logical groups |

### Connector types

| Category | Examples |
|----------|---------|
| Database sources | PostgreSQL, MySQL, Oracle, SQL Server |
| Cloud storage | S3, GCS, Azure Blob |
| Streaming | Kafka, Kinesis |
| SaaS | Salesforce, ServiceNow |
| File-based | CSV, JSON, Parquet, Avro |

## Parameters

### Routing by operation complexity

| Tier | Operations | When to Use |
|------|-----------|-------------|
| Primary | Status check, create, start/stop, monitor | Day-to-day connector management |
| Secondary | Troubleshoot, update config, view logs | When connectors are failing or need tuning |
| Advanced | Processor groups, templates, custom processors | Infrastructure-level changes |

## Constraints

- OpenFlow runs within Snowflake's managed NiFi environment — not a self-hosted NiFi instance.
- Connector creation requires appropriate roles and network access to source systems.
- Throughput depends on warehouse size and source system capacity.
- All connector configurations are stored within the Snowflake account.

## Examples

### Check connector status

```python
import nipyapi

nipyapi.config.nifi_config.host = '<openflow_endpoint>'
root_pg = nipyapi.canvas.get_root_pg_id()
process_groups = nipyapi.canvas.list_all_process_groups(root_pg)

for pg in process_groups:
    print(f"{pg.component.name}: {pg.status.aggregate_snapshot.active_thread_count} active threads")
```

### Monitor data throughput

```python
status = nipyapi.canvas.get_process_group_status(pg_id)
snapshot = status.aggregate_snapshot
print(f"Input: {snapshot.input} | Output: {snapshot.output}")
print(f"Queued: {snapshot.queued_count} | Bytes: {snapshot.queued_size}")
```

## Anti-patterns

| Pattern | Why It Fails | Instead |
|---------|-------------|---------|
| Using OpenFlow for simple S3-to-Snowflake loads | Overhead of connector management when Snowpipe or `COPY INTO` suffices | Use stages + `COPY INTO` or Snowpipe for simple cloud storage ingestion |
| Ignoring backpressure warnings | Data loss or out-of-memory errors in connectors | Monitor queue sizes and adjust flow rate or add backpressure thresholds |

## References

- [Snowflake Docs: Data Loading](https://docs.snowflake.com/en/user-guide/data-load-overview)

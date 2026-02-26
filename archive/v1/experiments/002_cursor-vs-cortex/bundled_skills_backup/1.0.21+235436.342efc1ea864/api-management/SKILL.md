---
name: trust-center-api-management
description: Use for **ALL** Trust Center scanner management requests including: enabling/disabling scanners or packages, changing notification settings, modifying run schedules, or triggering scanner executions. **Always query current state before making changes.**
---

## Instructions

When the user requests to manage Trust Center scanners or scanner packages, use the following SQL API.

## SQL API Reference

### Useful Views and Columns

- `snowflake.trust_center.scanner_packages` view contains metadata about each installed scanner package in an account
- `snowflake.trust_center.scanners` view contains metadata about each installed individual scanner in an account
- `snowflake.trust_center.configuration_view` contains metadata about the configuration of each scanner including notification, enablement status, and schedule

- Package ID: Retrieved from `snowflake.trust_center.scanner_packages` view using the `id` column
- Scanner ID: Retrieved from `snowflake.trust_center.scanners` view using the `id` column

### Useful static mapping of all first party scanners

| Scanner Id | Scanner Name | Severity | Type |
|------------|--------------|----------|------|
| threat_intelligence_non_mfa_person_users | Human User MFA Readiness | Critical | Scheduled |
| threat_intelligence_password_service_users | Service User Passwordless Readiness | Critical | Scheduled |
| threat_intelligence_users_with_high_job_errors | Users with High Job Errors | High | Scheduled |
| threat_intelligence_users_with_high_authn_failures | Users with High Volume of Authentication Failures | High | Scheduled |
| threat_intelligence_users_with_admin_privileges | Users with Admin Privileges | High | Scheduled |
| threat_intelligence_login_protection | Login Protection | High | Event-Driven |
| threat_intelligence_unusual_app_used_in_session | Users with Unusual Application Used in Sessions | Medium | Scheduled |
| threat_intelligence_entities_with_long_running_queries | Users with Long-Running Queries | Medium | Scheduled |
| threat_intelligence_authentication_policy_changes | Authentication Policy Changes | Low | Event-Driven |
| threat_intelligence_sensitive_parameter_protection | Sensitive Parameter Protection | High | Event-Driven |
| threat_intelligence_dormant_user_login | Dormant User Login | Medium | Event-Driven |
| threat_intelligence_sensitive_policy_changes | Sensitive Policy Changes | Low | Event-Driven |
| security_essentials_strong_auth_person_users_readiness | PERSON User Strong Authentication Readiness | High (password auth), Medium (others) | Scheduled |
| security_essentials_strong_auth_legacy_service_users_readiness | LEGACY SERVICE User Strong Authentication Readiness | High (password auth), Medium (others) | Scheduled |
| security_essentials_cis1_4 | 1.4 | Critical | Scheduled |
| security_essentials_cis3_1 | 3.1 | Critical | Scheduled |
| cis_benchmarks_cis1_1 | 1.1 — Ensure SSO is configured | High | Scheduled |
| cis_benchmarks_cis1_2 | 1.2 — Ensure SCIM integration is configured | Medium | Scheduled |
| cis_benchmarks_cis1_3 | 1.3 — Ensure password is unset for SSO users | High | Scheduled |
| cis_benchmarks_cis1_4 | 1.4 — Ensure MFA is on for all human users | Critical | Scheduled |
| cis_benchmarks_cis1_5 | 1.5 — Ensure min password length ≥ 14 | Medium | Scheduled |
| cis_benchmarks_cis1_6 | 1.6 — Ensure legacy service users use key pair auth | High | Scheduled |
| cis_benchmarks_cis1_7 | 1.7 — Ensure key pair rotation every 180 days | Medium | Scheduled |
| cis_benchmarks_cis1_8 | 1.8 — Ensure inactive users (90 days) are disabled | Medium | Scheduled |
| cis_benchmarks_cis1_9 | 1.9 — Ensure idle session timeout ≤ 15 min for admins | Low | Scheduled |
| cis_benchmarks_cis1_10 | 1.10 — Limit ACCOUNTADMIN/SECURITYADMIN users | Medium | Scheduled |
| cis_benchmarks_cis1_11 | 1.11 — Ensure ACCOUNTADMIN users have email | Low | Scheduled |
| cis_benchmarks_cis1_12 | 1.12 — Ensure no users default to admin roles | Low | Scheduled |
| cis_benchmarks_cis1_13 | 1.13 — Ensure admin roles not granted to custom roles | Medium | Scheduled |
| cis_benchmarks_cis1_14 | 1.14 — Ensure tasks not owned by admin roles | High | Scheduled |
| cis_benchmarks_cis1_15 | 1.15 — Ensure tasks don't run with admin privileges | High | Scheduled |
| cis_benchmarks_cis1_16 | 1.16 — Ensure stored procs not owned by admin roles | High | Scheduled |
| cis_benchmarks_cis1_17 | 1.17 — Ensure stored procs don't run with admin privileges | High | Scheduled |
| cis_benchmarks_cis1_18 | 1.18 — Ensure PATs require network policies | Medium | Scheduled |
| cis_benchmarks_cis2_1 | 2.1 — Monitor ACCOUNTADMIN/SECURITYADMIN role grants | Medium | Scheduled |
| cis_benchmarks_cis2_2 | 2.2 — Monitor MANAGE GRANTS privilege grants | Low | Scheduled |
| cis_benchmarks_cis2_4 | 2.4 — Monitor password sign-in without MFA | Medium | Scheduled |
| cis_benchmarks_cis2_5 | 2.5 — Monitor security integration changes | Low | Scheduled |
| cis_benchmarks_cis2_6 | 2.6 — Monitor network policy changes | Low | Scheduled |
| cis_benchmarks_cis2_7 | 2.7 — Monitor SCIM token creation | Low | Scheduled |
| cis_benchmarks_cis2_8 | 2.8 — Monitor new share exposures | Low | Scheduled |
| cis_benchmarks_cis2_9 | 2.9 — Monitor unsupported client sessions | Low | Scheduled |
| cis_benchmarks_cis3_1 | 3.1 — Ensure account-level network policy | Critical | Scheduled |
| cis_benchmarks_cis3_2 | 3.2 — Ensure service account network policies | Medium | Scheduled |
| cis_benchmarks_cis4_1 | 4.1 — Ensure yearly rekeying enabled | Low | Scheduled |
| cis_benchmarks_cis4_2 | 4.2 — Ensure AES 256-bit for internal stages | Low | Scheduled |
| cis_benchmarks_cis4_3 | 4.3 — Ensure retention ≥ 90 days for critical data | Low | Scheduled |
| cis_benchmarks_cis4_4 | 4.4 — Ensure MIN_DATA_RETENTION ≥ 7 days | Low | Scheduled |
| cis_benchmarks_cis4_5 | 4.5 — Ensure REQUIRE_STORAGE_INTEGRATION for stage creation | Medium | Scheduled |
| cis_benchmarks_cis4_6 | 4.6 — Ensure REQUIRE_STORAGE_INTEGRATION for stage operation | Medium | Scheduled |
| cis_benchmarks_cis4_7 | 4.7 — Ensure all external stages have storage integrations | Medium | Scheduled |
| cis_benchmarks_cis4_8 | 4.8 — Ensure PREVENT_UNLOAD_TO_INLINE_URL = true | Medium | Scheduled |
| cis_benchmarks_cis4_9 | 4.9 — Ensure Tri-Secret Secure enabled | Medium | Scheduled |
| cis_benchmarks_cis4_10 | 4.10 — Ensure data masking for sensitive data | Low | Scheduled |
| cis_benchmarks_cis4_11 | 4.11 — Ensure row-access policies for sensitive data | Low | Scheduled |


---

### Scanner Package and Scanner Execution

Runs a scanner package or individual scanner. If a scanner package is executed, all scanners that are enabled in it will be executed. Packages or scanners that do not exist will fail if a user tries to execute them.

To execute an entire scanner package:
```sql
CALL snowflake.trust_center.execute_scanner('<SCANNER_PACKAGE_ID>');
```

To execute a specific scanner:
```sql
CALL snowflake.trust_center.execute_scanner('<SCANNER_PACKAGE_ID>', '<SCANNER_ID>');
```

---

### Scanner Package Enablement

Enables an entire scanner package and all scanners within it. Free scanner packages are enabled by default. Enabling a paid package will incur cost to the account.

```sql
CALL snowflake.trust_center.set_configuration('ENABLED', 'TRUE', '<PACKAGE_ID>');
```

---

### Scanner Package Disablement

Disables an entire scanner package. Disabling a paid package will stop future costs.


```sql
CALL snowflake.trust_center.set_configuration('ENABLED', 'FALSE', '<PACKAGE_ID>');
```

**Note**: The Security Essentials package is free and cannot be disabled. If the user requests this, inform them and check current Snowflake documentation for alternatives.

---

### Scanner Specific Enablement

Enables a specific scanner within a scanner package. Free scanners are typically enabled by default.


```sql
CALL snowflake.trust_center.set_configuration('ENABLED', 'TRUE', '<PACKAGE_ID>', '<SCANNER_ID>');
```

---

### Scanner Specific Disablement

Disables a specific scanner within a scanner package. Disabling a paid scanner will stop future costs for that scanner.


```sql
CALL snowflake.trust_center.set_configuration('ENABLED', 'FALSE', '<PACKAGE_ID>', '<SCANNER_ID>');
```

**Note**: Any Security Essentials scanner cannot be disabled. If the user requests this, inform them and check current Snowflake documentation for alternatives.

---

### Scanner Package or Scanner-level Schedule Modification

Updates the package or scanner CRON schedule. If a package's schedule is updated, all scanners within it will be updated. Convert natural language date descriptions to CRON format.

For package-level schedule:
```sql
CALL snowflake.trust_center.set_configuration('SCHEDULE', 'USING CRON <SCHEDULE> UTC', '<PACKAGE_ID>', false);
```

For scanner-level schedule:
```sql
CALL snowflake.trust_center.set_configuration('SCHEDULE', 'USING CRON <SCHEDULE> UTC', '<PACKAGE_ID>', '<SCANNER_ID>');
```

**Note**: The Security Essentials package and contained scanners have a fixed schedule that cannot be modified. If the user requests this, inform them and check current Snowflake documentation for alternatives.

---

### Scanner Package or Scanner-level Notification Modification

Updates the package or scanner email notification configuration. If a package's notification is updated, all scanners within it will be updated.

#### Configuration Format

The notification configuration must follow this JSON format:
```json
{"NOTIFY_ADMINS":"TRUE","SEVERITY_THRESHOLD":"CRITICAL","USERS":[]}
```

- `SEVERITY_THRESHOLD`: One of `"CRITICAL"`, `"HIGH"`, `"MEDIUM"`, `"LOW"`
- `NOTIFY_ADMINS`: One of `"TRUE"`, `"FALSE"`
- `USERS`: Array of valid users from `snowflake.trust_center.users` view. **Only add users explicitly requested by the user.**

- When `NOTIFY_ADMINS` is true, users array even with value, will be ignored
- When `NOTIFY_ADMINS` is false and users is empty, this is considered invalid configuration
- An empty JSON string `{}` indicates no email notification for this package/scanner

#### Query Current Configuration

For a package:
```sql
SELECT notification 
FROM snowflake.trust_center.scanner_packages
WHERE id = '<SCANNER_PACKAGE_ID>';
```

For a scanner:
```sql
SELECT running_configuration_value
FROM snowflake.trust_center.configuration_view
WHERE configuration_name = 'NOTIFICATION'
  AND scanner_package_id = '<SCANNER_PACKAGE_ID>'
  AND scanner_id = '<SCANNER_ID>';
```

#### Apply Notification Changes

For package-level notification:
```sql
CALL snowflake.trust_center.set_configuration('NOTIFICATION', '<CONFIGURATION_JSON>', '<PACKAGE_ID>', false);
```

For scanner-level notification:
```sql
CALL snowflake.trust_center.set_configuration('NOTIFICATION', '<CONFIGURATION_JSON>', '<PACKAGE_ID>', '<SCANNER_ID>');
```


---

## Error Handling

**If a command fails:**

| Error | Resolution |
|-------|------------|
| `Insufficient privileges` | User needs ACCOUNTADMIN or TRUST_CENTER_ADMIN role. Ask user to verify their role. |
| `Object does not exist` | Verify package/scanner ID exists using the views before retrying. |
| `Invalid CRON expression` | Check CRON syntax: 5 fields (minute, hour, day-of-month, month, day-of-week). |
| `Invalid notification format` | Verify JSON structure and that all users exist in `snowflake.trust_center.users`. |
| Unknown error | Present full error message to user and ask for guidance. |

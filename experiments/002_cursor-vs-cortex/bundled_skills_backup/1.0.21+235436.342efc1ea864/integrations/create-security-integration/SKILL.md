---
name: create-security-integration
description: >
  Create a new security integration (SCIM, SAML2, OAuth, or API authentication) for interfacing with third-party services
---

# CREATE SECURITY INTEGRATION


Creates a new security integration in the account or replaces an existing integration. An integration is a Snowflake object that provides an interface between Snowflake and a third-party service.

## Syntax

```sql
CREATE [ OR REPLACE ] SECURITY INTEGRATION [ IF NOT EXISTS ]
  <name>
  TYPE = { API_AUTHENTICATION | EXTERNAL_OAUTH | OAUTH | SAML2 | SCIM }
  ...
```

The syntax varies considerably among security environments (i.e. types of security integrations). For specific syntax, usage notes, and examples, see:

- CREATE SECURITY INTEGRATION (AWS IAM Authentication)

- CREATE SECURITY INTEGRATION (External API Authentication)

- CREATE SECURITY INTEGRATION (External OAuth)

- CREATE SECURITY INTEGRATION (Snowflake OAuth)

- CREATE SECURITY INTEGRATION (SAML2)

- CREATE SECURITY INTEGRATION (SCIM)

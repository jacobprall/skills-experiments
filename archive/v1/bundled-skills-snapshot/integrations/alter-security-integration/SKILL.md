---
name: alter-security-integration
description: >
  Modify properties of an existing security integration (SCIM, SAML2, OAuth, or API authentication)
---

# ALTER SECURITY INTEGRATION


Modifies the properties for an existing security integration.

## Syntax

```sql
ALTER SECURITY INTEGRATION [ IF EXISTS ] <name> SET <parameters>

ALTER SECURITY INTEGRATION [ IF EXISTS ] <name>  UNSET <parameter>

ALTER SECURITY INTEGRATION <name> SET TAG <tag_name> = '<tag_value>' [ , <tag_name> = '<tag_value>' ... ]

ALTER SECURITY INTEGRATION <name> UNSET TAG <tag_name> [ , <tag_name> ... ]
```

The syntax varies considerably among security environments (i.e. types of security integrations). For specific syntax, usage notes, and examples, see:

- ALTER SECURITY INTEGRATION (AWS IAM Authentication)

- ALTER SECURITY INTEGRATION (External API Authentication)

- ALTER SECURITY INTEGRATION (External OAuth)

- ALTER SECURITY INTEGRATION (Snowflake OAuth)

- ALTER SECURITY INTEGRATION (SAML2)

- ALTER SECURITY INTEGRATION (SCIM)

USE ROLE {admin_role};

CREATE OR REPLACE ROLE {raw_schema}_ANALYST_ROLE;
GRANT USAGE ON DATABASE {database} TO ROLE {raw_schema}_ANALYST_ROLE;
GRANT USAGE ON SCHEMA {database}.{raw_schema} TO ROLE {raw_schema}_ANALYST_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA {database}.{raw_schema} TO ROLE {raw_schema}_ANALYST_ROLE;
GRANT ROLE {raw_schema}_ANALYST_ROLE TO ROLE {restricted_role};

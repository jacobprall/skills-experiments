-- Teardown is handled by the sandbox manager (DROP SCHEMA CASCADE)
-- This file exists for manual cleanup if needed.
USE ROLE {admin_role};
DROP SCHEMA IF EXISTS {database}.{raw_schema} CASCADE;
DROP SCHEMA IF EXISTS {database}.{staging_schema} CASCADE;
DROP SCHEMA IF EXISTS {database}.{analytics_schema} CASCADE;
DROP SCHEMA IF EXISTS {database}.{governance_schema} CASCADE;

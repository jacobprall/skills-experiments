USE ROLE {admin_role};

CREATE OR REPLACE SCHEMA {database}.{staging_schema}_CLONE
    CLONE {database}.{raw_schema};

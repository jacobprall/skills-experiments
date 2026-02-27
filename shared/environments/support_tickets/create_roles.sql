-- Role grants are managed at the account level.
-- The restricted role ({restricted_role}) access is tested via masking policy logic,
-- not by granting schema-level access from the admin role.
SELECT 'Roles configured' AS status;

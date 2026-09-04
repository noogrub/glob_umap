\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'gc'
    ) THEN
        RAISE EXCEPTION 'PostgreSQL role gc must exist before creating gc_ml';
    END IF;
END
$$;

SELECT format('CREATE DATABASE %I OWNER %I', 'gc_ml', 'gc')
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'gc_ml'
) \gexec

COMMENT ON DATABASE gc_ml IS
    'Globular-cluster machine-learning research database';

\set ON_ERROR_STOP on

BEGIN;
\ir 10_schemas.sql
\ir 20_raw.sql
\ir 30_core.sql
\ir 40_ml.sql
COMMIT;

\ir 90_verify.sql

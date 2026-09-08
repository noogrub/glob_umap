\set ON_ERROR_STOP on

WITH observed AS (
    SELECT
        'raw.fds'::text AS relation,
        'fds_aa_639_a136'::text AS catalog_code,
        min(source_file) AS source_file,
        count(DISTINCT source_file) AS source_files,
        count(*) AS observed_rows,
        count(DISTINCT (source_file, source_row)) AS distinct_keys,
        min(source_row) AS first_row,
        max(source_row) AS last_row
    FROM raw.fds
    UNION ALL
    SELECT
        'raw.des', 'des_dr2_fornax', min(source_file),
        count(DISTINCT source_file), count(*),
        count(DISTINCT (source_file, source_row)),
        min(source_row), max(source_row)
    FROM raw.des
    UNION ALL
    SELECT
        'raw.gc_master', 'fds_gc_master', min(source_file),
        count(DISTINCT source_file), count(*),
        count(DISTINCT (source_file, source_row)),
        min(source_row), max(source_row)
    FROM raw.gc_master
    UNION ALL
    SELECT
        'raw.spec', 'chaturvedi_aa_657_a93', min(source_file),
        count(DISTINCT source_file), count(*),
        count(DISTINCT (source_file, source_row)),
        min(source_row), max(source_row)
    FROM raw.spec
)
SELECT
    observed.relation,
    observed.observed_rows,
    catalog.expected_rows,
    catalog.loaded_rows,
    observed.distinct_keys,
    observed.first_row,
    observed.last_row,
    catalog.sha256,
    COALESCE((
        observed.source_files = 1
        AND observed.source_file = catalog.local_path
        AND observed.observed_rows = catalog.expected_rows
        AND observed.observed_rows = catalog.loaded_rows
        AND observed.distinct_keys = observed.observed_rows
        AND observed.first_row = 1
        AND observed.last_row = observed.observed_rows
    ), false) AS source_contract_ok
FROM observed
LEFT JOIN core.catalog AS catalog ON catalog.code = observed.catalog_code
ORDER BY observed.relation;

SELECT
    schemaname || '.' || tablename AS relation,
    tableowner,
    has_table_privilege('gc', schemaname || '.' || tablename, 'SELECT')
        AS gc_can_select,
    NOT (
        has_table_privilege('gc', schemaname || '.' || tablename, 'INSERT')
        OR has_table_privilege('gc', schemaname || '.' || tablename, 'UPDATE')
        OR has_table_privilege('gc', schemaname || '.' || tablename, 'DELETE')
        OR has_table_privilege('gc', schemaname || '.' || tablename, 'TRUNCATE')
    ) AS gc_write_locked
FROM pg_tables
WHERE schemaname = 'raw'
ORDER BY relation;

SELECT
    nspname AS schema,
    nspowner::regrole AS owner,
    has_schema_privilege('gc', nspname, 'USAGE') AS gc_has_usage,
    has_schema_privilege('gc', nspname, 'CREATE') AS gc_can_create
FROM pg_namespace
WHERE nspname = 'raw';

SELECT
    rolname,
    rolcanlogin,
    rolsuper,
    rolcreatedb,
    rolcreaterole
FROM pg_roles
WHERE rolname = 'gc_raw_owner';

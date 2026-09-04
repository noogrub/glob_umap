DO $$
DECLARE
    missing_tables text;
BEGIN
    SELECT string_agg(expected.name, ', ' ORDER BY expected.name)
    INTO missing_tables
    FROM (
        VALUES
            ('raw.fds'),
            ('raw.des'),
            ('raw.gc_master'),
            ('raw.spec'),
            ('core.catalog'),
            ('core.object'),
            ('core.record'),
            ('core.match_run'),
            ('core.match'),
            ('core.phot'),
            ('core.shape'),
            ('core.label'),
            ('ml.sample'),
            ('ml.member'),
            ('ml.run'),
            ('ml.embed'),
            ('ml.metric'),
            ('ml.stage_count'),
            ('ml.artifact')
    ) AS expected(name)
    WHERE to_regclass(expected.name) IS NULL;

    IF missing_tables IS NOT NULL THEN
        RAISE EXCEPTION 'Missing schema tables: %', missing_tables;
    END IF;
END
$$;

SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname IN ('raw', 'core', 'ml')
ORDER BY schemaname, tablename;

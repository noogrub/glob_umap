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
            ('ml.member_record'),
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

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'core'
          AND table_name = 'object'
          AND column_name = 'origin_record_id'
    ) THEN
        RAISE EXCEPTION 'Missing column: core.object.origin_record_id';
    END IF;
END
$$;

DO $$
BEGIN
    IF to_regclass('core.label_source_evidence_idx') IS NULL THEN
        RAISE EXCEPTION 'Missing index: core.label_source_evidence_idx';
    END IF;
END
$$;

SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname IN ('raw', 'core', 'ml')
ORDER BY schemaname, tablename;

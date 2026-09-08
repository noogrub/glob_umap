ALTER TABLE core.object
    ADD COLUMN IF NOT EXISTS origin_record_id bigint;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'object_origin_record_fk'
          AND conrelid = 'core.object'::regclass
    ) THEN
        ALTER TABLE core.object
            ADD CONSTRAINT object_origin_record_fk
            FOREIGN KEY (origin_record_id)
            REFERENCES core.record (record_id);
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS object_origin_record_idx
    ON core.object (origin_record_id)
    WHERE origin_record_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS ml.member_record (
    sample_id bigint NOT NULL,
    object_id bigint NOT NULL,
    source_role text NOT NULL
        CHECK (source_role IN ('reference', 'target')),
    record_id bigint NOT NULL REFERENCES core.record (record_id),
    PRIMARY KEY (sample_id, object_id, source_role),
    FOREIGN KEY (sample_id, object_id)
        REFERENCES ml.member (sample_id, object_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS member_record_record_idx
    ON ml.member_record (record_id, sample_id);

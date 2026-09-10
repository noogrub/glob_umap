CREATE UNIQUE INDEX IF NOT EXISTS label_source_evidence_idx
    ON core.label (object_id, record_id, evidence, provenance)
    WHERE record_id IS NOT NULL;

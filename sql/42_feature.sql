CREATE TABLE IF NOT EXISTS ml.feature_set (
    feature_set_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sample_id bigint NOT NULL REFERENCES ml.sample (sample_id),
    name text NOT NULL UNIQUE,
    config_path text NOT NULL,
    config_sha256 text NOT NULL CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    definition jsonb NOT NULL,
    feature_sha256 text CHECK (feature_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS feature_set_sample_idx
    ON ml.feature_set (sample_id);

CREATE TABLE IF NOT EXISTS ml.feature (
    feature_set_id bigint NOT NULL
        REFERENCES ml.feature_set (feature_set_id) ON DELETE CASCADE,
    object_id bigint NOT NULL,
    name text NOT NULL,
    value double precision NOT NULL,
    uncertainty double precision CHECK (uncertainty >= 0),
    PRIMARY KEY (feature_set_id, object_id, name),
    FOREIGN KEY (object_id) REFERENCES core.object (object_id)
);

CREATE INDEX IF NOT EXISTS feature_name_idx
    ON ml.feature (feature_set_id, name);

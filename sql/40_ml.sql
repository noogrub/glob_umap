CREATE TABLE IF NOT EXISTS ml.sample (
    sample_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE,
    description text NOT NULL,
    config_path text NOT NULL,
    config_sha256 text NOT NULL CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    definition jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml.member (
    sample_id bigint NOT NULL
        REFERENCES ml.sample (sample_id) ON DELETE CASCADE,
    object_id bigint NOT NULL REFERENCES core.object (object_id),
    split text NOT NULL
        CHECK (split IN ('train', 'validation', 'test', 'unassigned')),
    target_class text,
    weight double precision NOT NULL CHECK (weight > 0),
    PRIMARY KEY (sample_id, object_id)
);

CREATE INDEX IF NOT EXISTS member_split_idx ON ml.member (sample_id, split);

CREATE TABLE IF NOT EXISTS ml.run (
    run_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sample_id bigint NOT NULL REFERENCES ml.sample (sample_id),
    method text NOT NULL,
    status text NOT NULL
        CHECK (status IN ('planned', 'running', 'complete', 'failed')),
    config_path text NOT NULL,
    config_sha256 text NOT NULL CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    resolved_config jsonb NOT NULL,
    git_commit text NOT NULL CHECK (git_commit ~ '^[0-9a-f]{40}$'),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    CHECK (
        completed_at IS NULL
        OR started_at IS NULL
        OR completed_at >= started_at
    )
);

CREATE INDEX IF NOT EXISTS run_sample_idx ON ml.run (sample_id, method);

CREATE TABLE IF NOT EXISTS ml.embed (
    run_id bigint NOT NULL REFERENCES ml.run (run_id) ON DELETE CASCADE,
    object_id bigint NOT NULL REFERENCES core.object (object_id),
    component smallint NOT NULL CHECK (component > 0),
    value double precision NOT NULL,
    PRIMARY KEY (run_id, object_id, component)
);

CREATE INDEX IF NOT EXISTS embed_object_idx ON ml.embed (object_id, run_id);

CREATE TABLE IF NOT EXISTS ml.metric (
    metric_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES ml.run (run_id) ON DELETE CASCADE,
    split text NOT NULL,
    name text NOT NULL,
    target_class text,
    threshold double precision,
    value double precision NOT NULL,
    lower_bound double precision,
    upper_bound double precision,
    observation_count bigint CHECK (observation_count >= 0),
    scope jsonb NOT NULL DEFAULT '{}'::jsonb,
    CHECK (
        lower_bound IS NULL
        OR upper_bound IS NULL
        OR lower_bound <= upper_bound
    )
);

CREATE INDEX IF NOT EXISTS metric_run_idx ON ml.metric (run_id, name);

CREATE TABLE IF NOT EXISTS ml.stage_count (
    stage_count_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES ml.run (run_id) ON DELETE CASCADE,
    stage text NOT NULL,
    category text NOT NULL,
    count bigint NOT NULL CHECK (count >= 0),
    UNIQUE (run_id, stage, category)
);

CREATE TABLE IF NOT EXISTS ml.artifact (
    artifact_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES ml.run (run_id) ON DELETE CASCADE,
    kind text NOT NULL,
    path text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    media_type text,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (run_id, path)
);

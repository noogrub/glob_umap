CREATE TABLE IF NOT EXISTS core.catalog (
    catalog_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code text NOT NULL UNIQUE,
    title text NOT NULL,
    release text,
    source_url text NOT NULL,
    local_path text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    expected_rows bigint CHECK (expected_rows >= 0),
    loaded_rows bigint CHECK (loaded_rows >= 0),
    loaded_at timestamp with time zone,
    CHECK (
        expected_rows IS NULL
        OR loaded_rows IS NULL
        OR loaded_rows <= expected_rows
    )
);

CREATE TABLE IF NOT EXISTS core.object (
    object_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ra_deg double precision NOT NULL CHECK (ra_deg >= 0 AND ra_deg < 360),
    dec_deg double precision NOT NULL CHECK (dec_deg >= -90 AND dec_deg <= 90),
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS object_sky_idx ON core.object (ra_deg, dec_deg);

CREATE TABLE IF NOT EXISTS core.record (
    record_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    catalog_id bigint NOT NULL REFERENCES core.catalog (catalog_id),
    source_key text NOT NULL,
    ra_deg double precision NOT NULL CHECK (ra_deg >= 0 AND ra_deg < 360),
    dec_deg double precision NOT NULL CHECK (dec_deg >= -90 AND dec_deg <= 90),
    raw_ingest_id bigint,
    UNIQUE (catalog_id, source_key)
);

CREATE INDEX IF NOT EXISTS record_sky_idx ON core.record (ra_deg, dec_deg);

CREATE TABLE IF NOT EXISTS core.match_run (
    match_run_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE,
    method text NOT NULL,
    config_path text NOT NULL,
    config_sha256 text NOT NULL CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    resolved_config jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.match (
    match_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_run_id bigint NOT NULL
        REFERENCES core.match_run (match_run_id) ON DELETE CASCADE,
    object_id bigint NOT NULL REFERENCES core.object (object_id),
    record_id bigint NOT NULL REFERENCES core.record (record_id),
    angular_sep_arcsec double precision NOT NULL
        CHECK (angular_sep_arcsec >= 0),
    method text NOT NULL,
    search_radius_arcsec double precision NOT NULL
        CHECK (search_radius_arcsec > 0),
    candidate_count integer NOT NULL CHECK (candidate_count > 0),
    candidate_rank integer NOT NULL CHECK (candidate_rank > 0),
    selected boolean NOT NULL,
    ambiguous boolean NOT NULL,
    UNIQUE (match_run_id, record_id, object_id),
    UNIQUE (match_run_id, record_id, candidate_rank)
);

CREATE UNIQUE INDEX IF NOT EXISTS match_selected_record_idx
    ON core.match (match_run_id, record_id)
    WHERE selected;

CREATE INDEX IF NOT EXISTS match_object_idx ON core.match (object_id);

CREATE TABLE IF NOT EXISTS core.phot (
    phot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id bigint NOT NULL
        REFERENCES core.record (record_id) ON DELETE CASCADE,
    band text NOT NULL CHECK (band IN ('u', 'g', 'r', 'i', 'z', 'y')),
    measure text NOT NULL,
    mag double precision NOT NULL,
    mag_err double precision CHECK (mag_err >= 0),
    dereddened boolean NOT NULL,
    aperture_px double precision CHECK (aperture_px > 0),
    UNIQUE (record_id, band, measure, dereddened)
);

CREATE INDEX IF NOT EXISTS phot_band_idx ON core.phot (band, measure);

CREATE TABLE IF NOT EXISTS core.shape (
    shape_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id bigint NOT NULL
        REFERENCES core.record (record_id) ON DELETE CASCADE,
    band text CHECK (band IN ('u', 'g', 'r', 'i', 'z', 'y')),
    measure text NOT NULL,
    value double precision NOT NULL,
    unit text
);

CREATE UNIQUE INDEX IF NOT EXISTS shape_global_measure_idx
    ON core.shape (record_id, measure)
    WHERE band IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS shape_band_measure_idx
    ON core.shape (record_id, band, measure)
    WHERE band IS NOT NULL;

CREATE TABLE IF NOT EXISTS core.label (
    label_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    object_id bigint NOT NULL REFERENCES core.object (object_id),
    record_id bigint REFERENCES core.record (record_id),
    class text NOT NULL,
    evidence text NOT NULL,
    provenance text NOT NULL,
    confidence double precision CHECK (confidence >= 0 AND confidence <= 1),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS label_object_idx ON core.label (object_id);
CREATE INDEX IF NOT EXISTS label_class_idx ON core.label (class, evidence);

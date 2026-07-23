-- 005_meta_schema.sql — Pipeline metadata and observability

CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
    id              SERIAL PRIMARY KEY,
    run_at          TIMESTAMPTZ DEFAULT NOW(),
    layer           TEXT NOT NULL,
    step            TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    rows_affected   INT DEFAULT 0,
    duration_ms     INT DEFAULT 0,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS meta.watermarks (
    table_name  TEXT PRIMARY KEY,
    last_value  TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

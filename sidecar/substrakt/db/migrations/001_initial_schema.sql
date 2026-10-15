-- Initial schema matching the application's persistence model.
--
-- Conventions:
--   * timestamps are ISO 8601 text with a time zone;
--   * nested structures are JSON text in *_json columns;
--   * foreign keys cascade where deleting a parent owns the child rows.

CREATE TABLE document_type (
    id            INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE,
    description   TEXT    NOT NULL DEFAULT '',
    version       INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE field_block (
    id                INTEGER PRIMARY KEY,
    document_type_id  INTEGER NOT NULL REFERENCES document_type(id) ON DELETE CASCADE,
    name              TEXT    NOT NULL,
    -- Blocks represent repeated structures such as invoice line items.
    is_array          INTEGER NOT NULL DEFAULT 0 CHECK (is_array IN (0, 1)),
    sort_order        INTEGER NOT NULL DEFAULT 0,
    UNIQUE (document_type_id, name)
);

CREATE TABLE field (
    id                INTEGER PRIMARY KEY,
    document_type_id  INTEGER NOT NULL REFERENCES document_type(id) ON DELETE CASCADE,
    block_id          INTEGER REFERENCES field_block(id) ON DELETE SET NULL,
    -- The name becomes a JSON key in exports.
    name              TEXT    NOT NULL,
    question          TEXT    NOT NULL DEFAULT '',
    json_type         TEXT    NOT NULL DEFAULT 'string'
                      CHECK (json_type IN ('string','number','integer','date','boolean','array','object')),
    required          INTEGER NOT NULL DEFAULT 0 CHECK (required IN (0, 1)),
    -- One or more viewer highlights encoded as a JSON list of locators.
    locator_json      TEXT,
    extractor         TEXT    NOT NULL DEFAULT 'auto'
                      CHECK (extractor IN ('auto','region','regex','extractor')),
    regex             TEXT,
    normalization     TEXT,
    sort_order        INTEGER NOT NULL DEFAULT 0,
    UNIQUE (document_type_id, name)
);

CREATE INDEX idx_field_type  ON field(document_type_id);
CREATE INDEX idx_field_block ON field(block_id);

CREATE TABLE fingerprint (
    id                INTEGER PRIMARY KEY,
    document_type_id  INTEGER NOT NULL REFERENCES document_type(id) ON DELETE CASCADE,
    -- Stage 2 recognition uses normalized layout positions.
    layout_hash       TEXT,
    -- Stage 3 stores float32 embeddings as BLOBs and compares them with NumPy.
    -- A vector index only becomes worthwhile with several thousand types.
    embedding         BLOB,
    sample_file       TEXT,
    source            TEXT    NOT NULL DEFAULT 'initial'
                      CHECK (source IN ('initial','confirmed','corrected')),
    created_at        TEXT    NOT NULL
);

CREATE INDEX idx_fingerprint_type   ON fingerprint(document_type_id);
CREATE INDEX idx_fingerprint_layout ON fingerprint(layout_hash);

CREATE TABLE extraction_run (
    id                INTEGER PRIMARY KEY,
    document_sha256   TEXT    NOT NULL,
    file_name         TEXT    NOT NULL,
    document_type_id  INTEGER REFERENCES document_type(id) ON DELETE SET NULL,
    result_json       TEXT    NOT NULL DEFAULT '{}',
    confidences_json  TEXT    NOT NULL DEFAULT '{}',
    duration_ms       INTEGER NOT NULL DEFAULT 0,
    model             TEXT,
    occurred_at       TEXT    NOT NULL
);

CREATE INDEX idx_run_sha  ON extraction_run(document_sha256);
CREATE INDEX idx_run_time ON extraction_run(occurred_at);

CREATE TABLE correction (
    id                INTEGER PRIMARY KEY,
    extraction_run_id INTEGER NOT NULL REFERENCES extraction_run(id) ON DELETE CASCADE,
    field_name        TEXT    NOT NULL,
    old_value         TEXT,
    new_value         TEXT,
    locator_json      TEXT,
    occurred_at       TEXT    NOT NULL
);

CREATE INDEX idx_correction_run ON correction(extraction_run_id);

CREATE TABLE export_profile (
    id                INTEGER PRIMARY KEY,
    document_type_id  INTEGER NOT NULL REFERENCES document_type(id) ON DELETE CASCADE,
    format            TEXT    NOT NULL DEFAULT 'json',
    mapping_json      TEXT    NOT NULL DEFAULT '{}',
    target_json       TEXT    NOT NULL DEFAULT '{}',
    naming_scheme     TEXT    NOT NULL DEFAULT '{type}_{date}.json'
);

CREATE INDEX idx_export_type ON export_profile(document_type_id);

-- Every outbound attempt is recorded, including denied attempts.
-- A denial is normal in Air-gap mode and does not indicate a defect.
CREATE TABLE audit_log (
    id          INTEGER PRIMARY KEY,
    occurred_at TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    target      TEXT    NOT NULL,
    bytes       INTEGER NOT NULL DEFAULT 0,
    result      TEXT    NOT NULL CHECK (result IN ('allowed','denied','error')),
    mode        TEXT    NOT NULL CHECK (mode IN ('airgap','onprem','cloud'))
);

CREATE INDEX idx_audit_time ON audit_log(occurred_at);

CREATE TABLE app_setting (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

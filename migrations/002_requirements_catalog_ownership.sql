CREATE TABLE IF NOT EXISTS bundlegraph_requirement_drafts (
    request_reference TEXT PRIMARY KEY,
    owner_subject TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    draft JSONB NOT NULL,
    clarification_questions JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS bundlegraph_catalogs (
    catalog_id TEXT PRIMARY KEY,
    document JSONB NOT NULL,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS bundlegraph_one_active_catalog ON bundlegraph_catalogs (active) WHERE active;

CREATE TABLE IF NOT EXISTS bundlegraph_planning_inputs (
    confirmation_reference TEXT PRIMARY KEY,
    owner_subject TEXT NOT NULL,
    requirements JSONB NOT NULL,
    catalog_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bundlegraph_resource_owners (
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    owner_subject TEXT NOT NULL,
    PRIMARY KEY (resource_type, resource_id)
);

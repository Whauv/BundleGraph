CREATE TABLE IF NOT EXISTS bundlegraph_plans (plan_id TEXT PRIMARY KEY, document JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS bundlegraph_approvals (approval_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, document JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS bundlegraph_payment_operations (operation_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE, document JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS bundlegraph_webhook_events (event_id TEXT PRIMARY KEY, document JSONB NOT NULL, received_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS bundlegraph_plan_evidence (plan_id TEXT NOT NULL, evidence_id TEXT NOT NULL, document JSONB NOT NULL, PRIMARY KEY (plan_id, evidence_id));

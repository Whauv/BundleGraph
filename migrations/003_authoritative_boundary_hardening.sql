-- Forward-only hardening for durable replay and payment reservations.

CREATE UNIQUE INDEX IF NOT EXISTS bundlegraph_plan_creation_key_unique
    ON bundlegraph_plans ((document->>'creation_idempotency_key'))
    WHERE document->>'creation_idempotency_key' IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS bundlegraph_active_authorization_per_allocation
    ON bundlegraph_payment_operations (
        plan_id,
        (document->>'plan_version'),
        (document->>'merchant_allocation_id')
    )
    WHERE document->>'kind' = 'authorize'
      AND document->>'status' IN ('submitted', 'uncertain', 'succeeded');

CREATE UNIQUE INDEX IF NOT EXISTS bundlegraph_active_disposition_per_authorization
    ON bundlegraph_payment_operations ((document->>'parent_operation_id'))
    WHERE document->>'kind' IN ('capture', 'void')
      AND document->>'status' IN ('submitted', 'uncertain', 'succeeded');

CREATE INDEX IF NOT EXISTS bundlegraph_refunds_by_capture
    ON bundlegraph_payment_operations ((document->>'parent_operation_id'))
    WHERE document->>'kind' = 'refund';

CREATE INDEX IF NOT EXISTS bundlegraph_unprocessed_webhook_events
    ON bundlegraph_webhook_events (event_id)
    WHERE document->>'processed_at' IS NULL;

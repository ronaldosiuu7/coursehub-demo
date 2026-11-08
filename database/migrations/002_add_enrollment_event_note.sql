-- Apply once after migration 001. Existing rows receive note = NULL.
BEGIN;

ALTER TABLE enrollment_events
ADD COLUMN note VARCHAR(200);

INSERT INTO schema_migrations (version, description)
VALUES ('002', 'Add optional note to enrollment events');

COMMIT;

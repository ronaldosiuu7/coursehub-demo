-- WARNING: all note values are permanently lost when this rollback commits.
-- Existing events and their original columns are preserved.
BEGIN;

ALTER TABLE enrollment_events
DROP COLUMN note;

DELETE FROM schema_migrations WHERE version = '002';

COMMIT;


-- ========== TAB A ==========
-- Chay trong Query Tool A.

BEGIN;

SELECT id, capacity
FROM class_sections
WHERE id = 'RACE-01'
FOR UPDATE;

SELECT pg_sleep(8);

COMMIT;

-- ========== TAB B ==========

-- Chay trong khi Tab A dang pg_sleep(8).

 BEGIN;

 SELECT id, capacity
 FROM class_sections
 WHERE id = 'RACE-01'
 FOR UPDATE;

 ROLLBACK;

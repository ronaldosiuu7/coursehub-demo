-- Bai 3: 50 su kien CREATED gan nhat cua mot lop trong khoang thoi gian.
-- Chay tung phan trong pgAdmin; luu EXPLAIN truoc khi tao index.
-- Kiem tra index da co truoc khi do, khong DROP index dang dung.
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'enrollment_events';

ANALYZE enrollment_events;

-- 1. Do truoc index (chay 3 lan).
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, student_id, class_section_id, event_type, occurred_at
FROM enrollment_events
WHERE dataset = 'performance'
  AND class_section_id = 'WEB-01'
  AND event_type = 'CREATED'
  AND occurred_at >= TIMESTAMP '2025-12-20 00:00:00'
ORDER BY occurred_at DESC, id DESC
LIMIT 50;

-- 2. Cac cot loc bang nhau truoc; thoi gian va id theo thu tu sap xep sau.
CREATE INDEX idx_enrollment_events_dataset_section_type_time
ON enrollment_events
    (dataset, class_section_id, event_type, occurred_at DESC, id DESC);

-- 3. Do lai cung truy van (chay 3 lan).
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, student_id, class_section_id, event_type, occurred_at
FROM enrollment_events
WHERE dataset = 'performance'
  AND class_section_id = 'WEB-01'
  AND event_type = 'CREATED'
  AND occurred_at >= TIMESTAMP '2025-12-20 00:00:00'
ORDER BY occurred_at DESC, id DESC
LIMIT 50;

-- Script nay giu lai index. Script Python kem theo do trong transaction roi
-- ROLLBACK index thu nghiem de co the chay lai va giu nguyen trang thai ban dau.

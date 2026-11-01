
-- Chay khoi nay trong Tab A.

BEGIN;

SELECT cs.id, cs.capacity,
       COUNT(e.student_id) AS enrolled
FROM class_sections AS cs
LEFT JOIN enrollments AS e
    ON e.class_section_id = cs.id
WHERE cs.id = 'RACE-01'
GROUP BY cs.id, cs.capacity;

SELECT pg_sleep(8);

INSERT INTO enrollments (student_id, class_section_id)
VALUES ('22000002', 'RACE-01');

COMMIT;

--  Tab B 
-- KHONG chay chung voi Tab A.
-- Copy khoi nay sang Query Tool thu hai.
-- Chay khi Tab A dang pg_sleep(8).

 BEGIN;

 SELECT cs.id, cs.capacity,
        COUNT(e.student_id) AS enrolled
 FROM class_sections AS cs
 LEFT JOIN enrollments AS e
     ON e.class_section_id = cs.id
 WHERE cs.id = 'RACE-01'
 GROUP BY cs.id, cs.capacity;

 INSERT INTO enrollments (student_id, class_section_id)
 VALUES ('22000004', 'RACE-01');

 COMMIT;

======= KIEM TRA KET QUA ==========
-- Chi chay sau khi ca hai transaction hoan tat.

 SELECT cs.id, cs.capacity,
        COUNT(e.student_id) AS enrolled,
        cs.capacity - COUNT(e.student_id) AS remaining
 FROM class_sections AS cs
 LEFT JOIN enrollments AS e
     ON e.class_section_id = cs.id
 WHERE cs.id = 'RACE-01'
 GROUP BY cs.id, cs.capacity;

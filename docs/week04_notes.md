# CourseHub - Buoi 4
- Migration 001: enrollment_events.
- Demo class: RACE-01, capacity = 1.
- POST /enrollments: lock class_sections bang FOR UPDATE.
- Concurrency test: 1 request 201, 1 request 409.
- Performance data: 100000 rows, dataset=performance.
- Index: idx_enrollment_events_dataset_student_time.
- Ghi lai scan type va Execution Time truoc/sau o day.

Khong commit backend/.env.
## VII. Toi uu truy van

So ban ghi performance: 100000

### Truoc khi tao Index
- Scan Type: Seq Scan
- Execution Time: 5.348 ms


### Sau khi tao Index
- Scan Type: Index Scan
- Execution Time: 0.137 ms



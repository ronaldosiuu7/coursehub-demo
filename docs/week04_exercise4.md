# Bài 4 — Migration 002: ghi chú lịch sử đăng ký

## Thay đổi

Thêm `note VARCHAR(200)` vào enrollment_events để lưu ghi chú tùy chọn cho một sự kiện.
Cho phép NULL, không có giá trị mặc định bắt buộc: dữ liệu cũ nhận NULL và các INSERT
hiện tại của API vẫn hoạt động mà không cần truyền note. Bài này chỉ thay schema,
chưa bổ sung API ghi hoặc đọc ghi chú.

- Migration: `database/migrations/002_add_enrollment_event_note.sql`.
- Rollback: `database/migrations/002_add_enrollment_event_note_rollback.sql`.
- Test: `backend/tests/week04_migration002_test.py`.

ALTER TABLE và ghi version 002 nằm trong cùng transaction. Khi một lệnh thất bại,
không được COMMIT riêng các bước còn lại; chạy ROLLBACK trên phiên lỗi.
Migration thiết kế chạy một lần sau 001, không dùng IF NOT EXISTS để che giấu trạng thái sai.

## Kiểm thử tự động

Chạy tại thư mục gốc, dùng PostgreSQL cấu hình trong backend/.env, không cần Uvicorn:

```powershell
.venv\Scripts\python.exe -m unittest backend.tests.week04_migration002_test -v
```

Test sao chép cấu trúc và dữ liệu hiện có sang bảng TEMP của một phiên PostgreSQL,
rồi chạy chính hai file SQL migration/rollback. Bảng TEMP được ưu tiên khi SQL dùng
tên không kèm schema. Không sửa bảng public hoặc sequence của dữ liệu thật.
Kết thúc test, đóng hẳn phiên kết nối để xóa bản sao, kể cả khi có lỗi.
LIKE INCLUDING ALL sao chép CHECK/identity/index nhưng không sao chép foreign key;
bài này kiểm thử thay cột, version và bảo toàn dữ liệu, không kiểm thử khóa ngoại.

Đối chiếu tất cả 7 cột gốc bằng EXCEPT ALL theo hai chiều để chứng minh dữ liệu giữ nguyên,
không chỉ kiểm tra số dòng. Test có thể chạy lại kể cả khi public đã áp dụng 002;
nó dựng bản sao ở trạng thái trước 002 và không sao chép ghi chú thật.

## Kết quả ngày 2026-11-08

Một test tích hợp gồm các bước apply, validation, rollback và reapply: **PASS**, 1.345 giây.

```text
APPLY: 100001 original rows unchanged; note=NULL; version 002 recorded
VALIDATION: 200 characters accepted; 201 rejected; duplicate apply rejected
ROLLBACK: original rows preserved; note column and version 002 removed
REAPPLY: succeeds; deleted note values do not return
```

Đã xác nhận cột đúng VARCHAR(200), tất cả dòng cũ nhận NULL, version 002 được ghi một lần.
Chạy lặp migration bị từ chối, sau ROLLBACK dữ liệu/version vẫn đúng.
Rollback xóa version 002 nhưng giữ version 001.

## Áp dụng vào database học tập bằng pgAdmin

1. Mở Query Tool đúng database coursehub; kiểm tra migration 001 đã có và 002 chưa có:

```sql
SELECT version, description, applied_at
FROM schema_migrations
ORDER BY version;

SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'enrollment_events'
ORDER BY ordinal_position;
```

2. Trong cùng Query Tool, lưu bản chụp tạm trước thay đổi:

```sql
CREATE TEMP TABLE exercise4_before AS
SELECT id, student_id, class_section_id, event_type, source, dataset, occurred_at
FROM enrollment_events;
```

3. Chạy toàn bộ `002_add_enrollment_event_note.sql` một lần.
4. Kiểm tra kết quả trên cùng phiên, khi không có tác vụ khác đang ghi lịch sử:

```sql
SELECT COUNT(*) AS total, COUNT(note) AS rows_with_note
FROM enrollment_events;
-- Tổng số dòng không đổi; rows_with_note = 0 ngay sau migration.

SELECT COUNT(*) AS changed_rows
FROM (
    (SELECT * FROM exercise4_before
     EXCEPT ALL
     SELECT id, student_id, class_section_id, event_type, source, dataset, occurred_at
     FROM enrollment_events)
    UNION ALL
    (SELECT id, student_id, class_section_id, event_type, source, dataset, occurred_at
     FROM enrollment_events
     EXCEPT ALL
     SELECT * FROM exercise4_before)
) AS differences;
-- changed_rows = 0.

SELECT version, description FROM schema_migrations WHERE version = '002';
```

Chạy lại truy vấn information_schema ở bước 1 để xem note có độ dài 200, nullable YES.
ALTER TABLE cần khóa bảng; thực hành lúc không có transaction khác đang sử dụng bảng.
Không cần chạy migration thủ công chỉ để chạy test tự động.

## Rollback có mất dữ liệu không?

**Có: mất toàn bộ giá trị note đã ghi.** File rollback DROP COLUMN note và xóa version 002
trong cùng transaction. Các sự kiện cùng 7 cột cũ được giữ nguyên.
Chỉ chạy rollback khi chấp nhận mất ghi chú hoặc đã sao lưu chúng.
Áp dụng lại migration chỉ tạo cột note rỗng, không phục hồi ghi chú đã bị xóa.

## Tự review

Đã kiểm tra đúng yêu cầu thêm cột, migration có version và transaction, tương thích INSERT
cũ, giới hạn 200 ký tự, bảo toàn dữ liệu và hậu quả của rollback.
Minh chứng được chạy trên bản sao TEMP chứa dữ liệu thực tế; chưa áp dụng 002 vào public.
Đã tự review; chưa có review độc lập từ thành viên khác.

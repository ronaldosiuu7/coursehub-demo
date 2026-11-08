# Bài 1 — API đọc lịch sử đăng ký

`GET /enrollment-events` trả danh sách sự kiện; không có dữ liệu trả HTTP 200 với `[]`.

| Query parameter | Mặc định | Ý nghĩa |
| --- | --- | --- |
| student_id | Không lọc | Mã sinh viên, chuỗi |
| event_type | Không lọc | CREATED hoặc CANCELLED |
| skip | 0 | Số dòng bỏ qua, >= 0 |
| limit | 10 | Số dòng trả về, 1–100 |

Các giá trị được bind qua SQLAlchemy `text()`; không ghép input vào SQL.
Thứ tự là `occurred_at DESC, id DESC`: id phân định các sự kiện cùng thời gian.
API đọc cả dataset demo và performance theo yêu cầu đề bài.

## Chạy và kiểm thử

Database phải đã áp dụng migration 001 và có ít nhất một sự kiện.
Migration tạo bảng: `database/migrations/001_add_enrollment_events.sql`.
Rollback: `database/migrations/001_add_enrollment_events_rollback.sql` (xóa lịch sử).
Không chạy lại migration trên database đã có bảng; thay đổi tên file không yêu cầu chạy lại SQL.

```powershell
.venv\Scripts\python.exe -m unittest backend.tests.week04_enrollment_events_test -v
```
Kết quả : **6/6 test thành công**, thời gian unittest 2.044 giây.
Đã kiểm tra trên PostgreSQL có 100.001 sự kiện; số sự kiện sau kiểm thử vẫn là 100.001.

- Bộ lọc riêng và kết hợp, dữ liệu trả về đối chiếu SQL, thời gian serialize thành JSON.
- Kết quả rỗng và input dạng SQL injection đều trả 200 với `[]`.
- Hai trang đối chiếu thứ tự SQL `occurred_at DESC, id DESC`.
- Mặc định 10 dòng, biên limit 1 và 100.
- Limit 0/101/abc, skip âm và event_type sai đều trả 422.

## Postman

Chạy API:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Import `postman/CourseHub_Buoi_4_Bai_1.postman_collection.json`.
Collection có 8 request và assertion HTTP/data cho ca có dữ liệu, rỗng, phân trang và lỗi.
Đặt `base_url=http://127.0.0.1:8000`. Chọn student_id/event_type thực sự có trong bảng:

```sql
SELECT student_id, event_type
FROM enrollment_events
ORDER BY id
LIMIT 1;
```

Điền hai giá trị đó vào collection variables rồi Run collection.
Ca rỗng dùng `__no_student__`, dài hơn giới hạn VARCHAR(8) của student_id trong bảng.
Collection đã được kiểm tra JSON; chưa chạy bằng ứng dụng Postman.

## review

Đã kiểm tra bind parameter cho input, validation, thứ tự ổn định, phân trang và chiều migration/rollback.

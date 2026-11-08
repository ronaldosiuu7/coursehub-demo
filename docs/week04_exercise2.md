# Bài 2 — Kiểm thử rollback nhiều bảng

## Mục tiêu và cách làm

Chứng minh INSERT enrollments và INSERT enrollment_events cùng thành công hoặc cùng rollback.
Mã kiểm thử: `backend/tests/week04_rollback_test.py`.

Test gọi trực tiếp hàm `create_enrollment` đang dùng cho POST /enrollments.
Chỉ trong test, thay engine bằng adapter dùng một connection PostgreSQL thật.
Adapter vẫn dùng `connection.begin()` để COMMIT/ROLLBACK thật.
Trước INSERT lịch sử, test xác nhận INSERT đăng ký đã tạo 1 dòng, rồi thay
event_type CREATED bằng INVALID. PostgreSQL từ chối với CHECK constraint
`ck_enrollment_events_type`, SQLSTATE `23514`.
Exception thoát khỏi transaction nên đăng ký cũng bị rollback; hàm API chuyển
IntegrityError thành HTTPException 409 theo cách xử lý hiện tại.

Không thêm endpoint demo hoặc logic cố ý gây lỗi vào `backend/app/main.py`.

## Môi trường và dữ liệu

Mỗi test tạo bốn bảng TEMP cùng tên từ cấu trúc public bằng LIKE INCLUDING ALL.
Các bảng tạm được ưu tiên khi hàm API truy vấn tên bảng không kèm schema.
CHECK constraint được sao chép; identity của bảng sự kiện dùng sequence riêng.
LIKE không sao chép foreign key: bài này xác minh transaction và CHECK event_type,
không kiểm thử ràng buộc khóa ngoại.

Test sao chép một sinh viên và một lớp vào bảng tạm; hai bảng đăng ký/lịch sử bắt đầu rỗng.
Kết thúc mỗi test, đóng hẳn phiên kết nối để xóa bảng tạm, kể cả khi test thất bại.
Không INSERT/UPDATE/DELETE vào bảng public, không cần reset dữ liệu học tập.

## Chạy kiểm thử

Tại thư mục gốc dự án, không cần khởi động Uvicorn:

```powershell
.venv\Scripts\python.exe -m unittest backend.tests.week04_rollback_test -v
```

## Minh chứng ngày 2026-11-08

Đã chạy trên PostgreSQL thực tế: **2/2 test thành công**, 0.497 giây.

```text
test_invalid_event_rolls_back_both_tables ... ok
test_valid_event_commits_both_tables ... ok
Ran 2 tests in 0.497s
OK
ROLLBACK: before=(0, 0), after enrollment INSERT=1, event CHECK violation=23514, after=(0, 0), HTTPException=409
COMMIT: before=(0, 0), after=(1, 1), event_type=CREATED
```

| Ca kiểm thử | Trước (đăng ký, lịch sử) | Sau | Kết quả |
| --- | --- | --- | --- |
| event_type=INVALID | (0, 0) | (0, 0) | Rollback cả transaction |
| event_type=CREATED | (0, 0) | (1, 1) | Commit cả hai INSERT |

Truy vấn xác nhận được chạy trên cùng phiên chứa bảng tạm, sau khi transaction kết thúc:

```sql
SELECT (SELECT COUNT(*) FROM enrollments),
       (SELECT COUNT(*) FROM enrollment_events);
```

Mở pgAdmin ở phiên khác sẽ thấy bảng public, không thấy các bảng TEMP của test.

## Tự review

- Ca lỗi xác nhận INSERT thứ nhất đã thành công trước khi gây lỗi INSERT thứ hai.
- Kiểm tra đúng CHECK constraint và SQLSTATE để tránh nhầm với lỗi trùng đăng ký/đầy lớp.
- Kiểm tra trạng thái sau rollback và ca đối chứng commit thành công.
- Fault injection chỉ nằm trong tests; dữ liệu và endpoint production giữ nguyên.
- Đây là kiểm thử hàm xử lý với database thật, không phải kiểm thử HTTP qua mạng.


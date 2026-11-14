# Ghi chú Buổi 5 — Frontend React & Tìm kiếm / Phân trang phía Server

## Bài 4: Tìm kiếm và phân trang phía Server cho `GET /sections`

- **Endpoint**: `GET /sections` ([backend/app/main.py](../backend/app/main.py))
- **Tham số truy vấn (Query Parameters)**:
  - `q` (`str | None`, mặc định `None`): từ khóa tìm kiếm không phân biệt hoa thường trên `class_id`, `course_code`, và `courses.name` (`LOWER(...) LIKE :keyword`).
  - `course_code` (`str | None`, mặc định `None`): lọc chính xác theo mã học phần (`v.course_code = :course_code`).
  - `available_only` (`bool`, mặc định `false`): chỉ lấy lớp còn chỗ (`v.remaining > 0`).
  - `skip` (`int`, `ge=0`, mặc định `0`): vị trí bắt đầu (`OFFSET :skip`).
  - `limit` (`int`, `ge=1, le=100`, mặc định `20`): số bản ghi tối đa trả về (`LIMIT :limit`).
- **Giới hạn kích thước trang**:
  - Backend giới hạn `1 <= limit <= 100` (từ chối `HTTP 422` nếu vượt ngưỡng).
  - Frontend ([frontend/src/App.jsx](../frontend/src/App.jsx)) đặt `SECTION_PAGE_SIZE = 3` (gửi `limit = 4` để xác định có trang tiếp theo hay không).
- **Thứ tự sắp xếp ổn định (Deterministic Ordering)**:
  - `ORDER BY v.class_id ASC` (sắp xếp tăng dần theo khóa chính `class_id` của bảng `class_sections`), đảm bảo các trang không bị trùng hoặc sót dòng khi chuyển trang.
- **Lưu ý**: Việc lọc và phân trang được thực hiện trực tiếp bằng câu lệnh SQL trên PostgreSQL (`WHERE`, `ORDER BY`, `LIMIT`, `OFFSET`), không tải toàn bộ danh sách về rồi `.filter()` trên trình duyệt.

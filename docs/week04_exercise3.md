# Bài 3 — Chỉ mục thứ hai theo nghiệp vụ

## Truy vấn và chỉ mục

Nghiệp vụ: xem 50 sự kiện đăng ký CREATED gần nhất của lớp WEB-01 từ 2025-12-20,
theo thời gian giảm dần. Dùng dataset=performance để đo trên dữ liệu sinh, không nhầm
với lịch sử thật. Đây là truy vấn khác truy vấn theo student_id trong bài thực hành.

SQL đầy đủ: `database/13_exercise3_section_event_index.sql`.

```sql
CREATE INDEX idx_enrollment_events_dataset_section_type_time
ON enrollment_events
    (dataset, class_section_id, event_type, occurred_at DESC, id DESC);
```

Giải thích thứ tự cột:

- dataset, class_section_id, event_type đều lọc bằng nhau, đứng trước cột khoảng thời gian.
  Thứ tự này phù hợp với cách tra cứu theo bộ dữ liệu rồi theo lớp và loại sự kiện;
  không khẳng định đây là thứ tự tối ưu cho mọi truy vấn khác.
- occurred_at dùng điều kiện >= và ORDER BY DESC, đứng sau nhóm điều kiện bằng nhau.
- id DESC phân định các sự kiện cùng thời gian, khớp ORDER BY để tránh Sort riêng.
- Không tạo chỉ mục riêng cho từng cột. Chỉ mục ghép này phục vụ truy vấn đã chọn.

## Đo và minh chứng

Chạy từ thư mục gốc, dùng kết nối backend/.env, không cần Uvicorn:

```powershell
.venv\Scripts\python.exe -m backend.tests.week04_section_index_benchmark
```

Script yêu cầu ít nhất 100.000 dòng performance và truy vấn có dữ liệu.
Script ANALYZE một lần trước cả hai phương án, đo mỗi phương án 3 lần bằng
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON), so sánh toàn bộ 50 dòng kết quả.
Không ép planner và không xóa chỉ mục cũ. Nếu chỉ mục thử đã tồn tại, script dừng
để tránh ghi sai kết quả trước/sau. DDL chạy trong transaction rồi ROLLBACK,
kể cả khi lỗi; không INSERT/UPDATE/DELETE sự kiện.

Kết quả thực tế ngày 2026-11-08 trên 100.000 dòng performance và 1 dòng demo:

| Chỉ tiêu | Trước chỉ mục mới | Sau chỉ mục mới |
| --- | --- | --- |
| Kế hoạch chính | Bitmap Heap Scan + Sort | Index Scan, không Sort |
| Execution Time lần 1 (ms) | 0.895 | 0.138 |
| Execution Time lần 2 (ms) | 0.717 | 0.070 |
| Execution Time lần 3 (ms) | 0.657 | 0.068 |
| Trung vị (ms) | 0.717 | 0.070 |
| Dòng trả về | 50 | 50 |
| Shared buffers lần 1, ở node Limit | hit=348, read=0 | hit=50, read=4 |

Trước khi thêm chỉ mục, planner dùng chỉ mục có sẵn
`idx_enrollment_events_dataset_student_time`, lấy 3.279 dòng qua bitmap,
lọc bỏ 2.597 dòng, còn 682 dòng để chọn 50 dòng sau Sort.
Sau khi thêm chỉ mục, Index Scan dùng
`idx_enrollment_events_dataset_section_type_time` và lấy 50 dòng theo thứ tự yêu cầu.

Trung vị nhanh hơn khoảng 10,24 lần trong lần đo này. Đây không phải cam kết tốc độ
cho mọi máy: cache, phân bố dữ liệu và workload ảnh hưởng kết quả; thời gian tuyệt đối rất nhỏ.
Không cộng buffers của các node cha/con vì số liệu có thể bao gồm nhau.

Toàn bộ 6 execution plan nằm trong `docs/week04_exercise3_plans.json`.
Script xác nhận `same_results=true`, `returned_rows=50`, `trial_index_removed=true`.
Chỉ mục thử có kích thước 6.799.360 byte (khoảng 6,48 MiB).

## Chạy bằng pgAdmin và giữ lại chỉ mục

Mở `database/13_exercise3_section_event_index.sql`, thực hiện từng phần:

1. Kiểm tra danh sách chỉ mục, chạy ANALYZE.
2. Chạy EXPLAIN trước chỉ mục 3 lần và lưu kết quả.
3. Chạy CREATE INDEX một lần.
4. Chạy cùng EXPLAIN sau chỉ mục 3 lần và so sánh.

SQL này giữ lại chỉ mục, khác với script benchmark Python tự rollback.
Không chạy lại CREATE INDEX khi chỉ mục đã tồn tại và không đổi tên để tạo bản sao.
Chỉ mục tốn dung lượng và làm tăng chi phí ghi; cần đánh giá tần suất truy vấn trước
khi áp dụng vào môi trường sử dụng thực tế. CREATE INDEX thường có thể chặn ghi
trong lúc xây dựng, nên thực hành trên database học tập khi không có thao tác ghi đồng thời.

## Tự review

Đã đối chiếu cùng truy vấn, cùng tham số, cùng dữ liệu trước/sau; không ép Seq Scan
hay bỏ chỉ mục cũ để làm đẹp số liệu. Kết quả 50 dòng giống nhau hoàn toàn.
Chỉ mục thử đã rollback, dữ liệu được giữ nguyên. Không sửa script sinh dữ liệu hiện có.
Đã tự review; chưa có thành viên khác review độc lập.

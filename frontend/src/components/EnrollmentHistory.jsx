import Notice from "./Notice.jsx";

function formatOccurredAt(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("vi-VN");
}

export default function EnrollmentHistory({
  studentId,
  rows,
  page,
  hasNext,
  loading,
  error,
  onPrevPage,
  onNextPage,
}) {
  return (
    <section className="panel">
      <div className="history-header">
        <div>
          <h2>4. Lịch sử đăng ký (demo)</h2>
          <p className="muted">
            Sinh viên {studentId} · Trang {page + 1} · Chỉ hiển thị nhật ký demo
          </p>
        </div>
        <div className="pagination">
          <button
            type="button"
            className="secondary"
            disabled={loading || page === 0}
            onClick={onPrevPage}
          >
            Trang trước
          </button>
          <button
            type="button"
            className="secondary"
            disabled={loading || !hasNext}
            onClick={onNextPage}
          >
            Trang sau
          </button>
        </div>
      </div>

      <Notice kind="error">{error}</Notice>
      {loading && <Notice>Đang tải lịch sử...</Notice>}

      {!loading && !error && rows.length === 0 && (
        <p className="muted">Chưa có sự kiện demo nào cho sinh viên này.</p>
      )}

      {!loading && !error && rows.length > 0 && (
        <div className="table-scroll">
          <table aria-label="Lịch sử đăng ký demo">
            <thead>
              <tr>
                <th>Thời gian</th>
                <th>Lớp học phần</th>
                <th>Thao tác</th>
                <th>Nguồn</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => (
                <tr key={item.id}>
                  <td>{formatOccurredAt(item.occurred_at)}</td>
                  <td><strong>{item.class_section_id}</strong></td>
                  <td>
                    <span className={item.event_type === "CREATED" ? "badge" : "badge full"}>
                      {item.event_type === "CREATED" ? "Đăng ký (CREATED)" : "Hủy (CANCELLED)"}
                    </span>
                  </td>
                  <td>{item.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

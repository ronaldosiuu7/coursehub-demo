export default function StudentForm({
  draftId,
  studentId,
  busy,
  loading,
  onDraftChange,
  onSubmit,
  onReload,
}) {
  return (
    <section className="panel">
      <h2>1. Chọn sinh viên</h2>
      <form className="student-form" onSubmit={onSubmit}>
        <label htmlFor="student-id">Mã sinh viên</label>
        <input
          id="student-id"
          value={draftId}
          maxLength={8}
          required
          inputMode="numeric"
          onChange={(e) => onDraftChange(e.target.value)}
          disabled={busy}
        />
        <button type="submit" disabled={busy}>Xem đăng ký</button>
        <button
          type="button"
          className="secondary"
          disabled={busy || loading}
          onClick={onReload}
        >
          Tải lại dữ liệu
        </button>
      </form>
      <p className="muted">
        Dữ liệu đang xem: <strong>{studentId}</strong>. Mã mẫu: 22000001–22000004.
      </p>
    </section>
  );
}
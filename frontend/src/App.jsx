import { useEffect, useState } from "react";
import { api } from "./api.js";
import Notice from "./components/Notice.jsx";
import SectionTable from "./components/SectionTable.jsx";
import EnrollmentList from "./components/EnrollmentList.jsx";
import StudentForm from "./components/StudentForm.jsx";
import EnrollmentHistory from "./components/EnrollmentHistory.jsx";

const SECTION_PAGE_SIZE = 3;
const HISTORY_PAGE_SIZE = 5;

export default function App() {
  const [draftId, setDraftId] = useState("22000004");
  const [studentId, setStudentId] = useState("22000004");
  const [courses, setCourses] = useState([]);
  const [sections, setSections] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [search, setSearch] = useState("");
  const [selectedCourse, setSelectedCourse] = useState("");
  const [onlyAvailable, setOnlyAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState({ kind: "info", text: "" });
  const [refresh, setRefresh] = useState(0);
  const [sectionPage, setSectionPage] = useState(0);
  const [sectionHasNext, setSectionHasNext] = useState(false);
  const [sectionsLoading, setSectionsLoading] = useState(true);
  const [sectionsError, setSectionsError] = useState("");
  const [history, setHistory] = useState([]);
  const [historyPage, setHistoryPage] = useState(0);
  const [historyHasNext, setHistoryHasNext] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const options = { signal: controller.signal };
    async function loadData() {
      setLoading(true);
      setError("");
      try {
        const [courseData, enrollmentData] = await Promise.all([
          api("/courses", options),
          api(`/students/${encodeURIComponent(studentId)}/enrollments`, options),
        ]);
        if (controller.signal.aborted) return;
        setCourses(courseData);
        setEnrollments(enrollmentData);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err.message);
        setCourses([]);
        setEnrollments([]);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    loadData();
    return () => controller.abort();
  }, [studentId, refresh]);

  useEffect(() => {
    const controller = new AbortController();
    async function loadSections() {
      setSectionsLoading(true);
      setSectionsError("");
      try {
        const params = new URLSearchParams({
          available_only: String(onlyAvailable),
          skip: String(sectionPage * SECTION_PAGE_SIZE),
          limit: String(SECTION_PAGE_SIZE + 1),
        });
        if (search.trim()) params.set("q", search.trim());
        if (selectedCourse) params.set("course_code", selectedCourse);

        const data = await api(`/sections?${params.toString()}`, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setSectionHasNext(data.length > SECTION_PAGE_SIZE);
        setSections(data.slice(0, SECTION_PAGE_SIZE));
      } catch (err) {
        if (controller.signal.aborted) return;
        setSectionsError(err.message);
        setSections([]);
        setSectionHasNext(false);
      } finally {
        if (!controller.signal.aborted) setSectionsLoading(false);
      }
    }
    loadSections();
    return () => controller.abort();
  }, [search, selectedCourse, onlyAvailable, sectionPage, refresh]);

  useEffect(() => {
    const controller = new AbortController();
    async function loadHistory() {
      setHistoryLoading(true);
      setHistoryError("");
      try {
        const skip = historyPage * HISTORY_PAGE_SIZE;
        const limit = HISTORY_PAGE_SIZE + 1;
        const data = await api(
          `/enrollment-events?student_id=${encodeURIComponent(studentId)}` +
          `&dataset=demo&skip=${skip}&limit=${limit}`,
          { signal: controller.signal },
        );
        if (controller.signal.aborted) return;
        setHistoryHasNext(data.length > HISTORY_PAGE_SIZE);
        setHistory(data.slice(0, HISTORY_PAGE_SIZE));
      } catch (err) {
        if (controller.signal.aborted) return;
        setHistoryError(err.message);
        setHistory([]);
        setHistoryHasNext(false);
      } finally {
        if (!controller.signal.aborted) setHistoryLoading(false);
      }
    }
    loadHistory();
    return () => controller.abort();
  }, [studentId, historyPage, refresh]);

  function chooseStudent(event) {
    event.preventDefault();
    const nextId = draftId.trim();
    if (!/^\d{8}$/.test(nextId)) {
      setNotice({ kind: "error", text: "Mã demo phải gồm 8 chữ số." });
      return;
    }
    setNotice({ kind: "info", text: "" });
    setLoading(true);
    setHistoryPage(0);
    setStudentId(nextId);
    setRefresh((value) => value + 1);
  }

  async function changeEnrollment(sectionId, cancel = false) {
    if (busy || loading || error) return;
    if (cancel && !window.confirm(`Hủy đăng ký lớp ${sectionId}?`)) return;
    setBusy(true);
    setNotice({ kind: "info", text: "Đang gửi yêu cầu..." });
    try {
      if (cancel) {
        await api(
          `/enrollments/${encodeURIComponent(studentId)}/${encodeURIComponent(sectionId)}`,
          { method: "DELETE" },
        );
      } else {
        await api("/enrollments", {
          method: "POST",
          body: { student_id: studentId, class_section_id: sectionId },
        });
      }
      setNotice({
        kind: "success",
        text: cancel
          ? `Đã hủy đăng ký ${sectionId}.`
          : `Đăng ký ${sectionId} thành công.`,
      });
    } catch (err) {
      setNotice({ kind: "error", text: err.message });
    } finally {
      // Đọc lại CSDL kể cả sau lỗi; không tự cộng/trừ số chỗ ở giao diện.
      setLoading(true);
      setHistoryPage(0);
      setRefresh((value) => value + 1);
      setBusy(false);
    }
  }

  const rows = sections.map((section) => ({
    ...section,
    course_name: courses.find((course) => course.code === section.course_code)?.name
      ?? section.course_code,
    registered: enrollments.some((item) => item.class_section_id === section.class_id),
  }));
  const disabled = loading || sectionsLoading || busy || Boolean(error) || Boolean(sectionsError);

  return (
    <main className="container">
      <header className="hero">
        <p className="eyebrow">CSDL WEB VÀ HỆ THỐNG THÔNG TIN · BUỔI 5</p>
        <h1>CourseHub</h1>
        <p>Tra cứu và đăng ký lớp học phần</p>
        <span className="chip">React → FastAPI → PostgreSQL</span>
      </header>
      <p className="demo-note">
        Môi trường thực hành. Nhập mã sinh viên để thử dữ liệu, không phải đăng nhập.
      </p>
      <StudentForm
        draftId={draftId}
        studentId={studentId}
        busy={busy}
        loading={loading}
        onDraftChange={setDraftId}
        onSubmit={chooseStudent}
        onReload={() => setRefresh((value) => value + 1)}
      />
      <Notice kind={notice.kind}>{notice.text}</Notice>
      <Notice kind="error">{error}</Notice>
      {loading && <Notice>Đang tải dữ liệu từ API...</Notice>}
      {!loading && !error && (
        <div className="workspace">
          <section className="panel">
            <h2>2. Danh sách lớp học phần</h2>
            <div className="filters">
              <label htmlFor="search">Tìm lớp / học phần</label>
              <input id="search" value={search} placeholder="Ví dụ: web"
                onChange={(e) => {
                  setSearch(e.target.value);
                  setSectionPage(0);
                }} />
              <select
                aria-label="Lọc theo học phần"
                value={selectedCourse}
                onChange={(e) => {
                  setSelectedCourse(e.target.value);
                  setSectionPage(0);
                }}
              >
                <option value="">Tất cả học phần</option>
                {courses.map((course) => (
                  <option key={course.code} value={course.code}>
                    {course.code} — {course.name}
                  </option>
                ))}
              </select>
              <label className="check">
                <input type="checkbox" checked={onlyAvailable}
                  onChange={(e) => {
                    setOnlyAvailable(e.target.checked);
                    setSectionPage(0);
                  }} />
                Chỉ hiện lớp còn chỗ
              </label>
            </div>
            <Notice kind="error">{sectionsError}</Notice>
            {sectionsLoading
              ? <Notice>Đang tải danh sách lớp...</Notice>
              : !sectionsError && (
                <>
                  <SectionTable rows={rows} disabled={disabled}
                    onEnroll={(id) => changeEnrollment(id)} />
                  <div className="history-header" style={{ marginTop: "14px", marginBottom: 0 }}>
                    <span className="muted">Trang {sectionPage + 1}</span>
                    <div className="pagination">
                      <button
                        type="button"
                        className="secondary"
                        disabled={sectionsLoading || sectionPage === 0}
                        onClick={() => setSectionPage((p) => Math.max(0, p - 1))}
                      >
                        Trang trước
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        disabled={sectionsLoading || !sectionHasNext}
                        onClick={() => setSectionPage((p) => p + 1)}
                      >
                        Trang sau
                      </button>
                    </div>
                  </div>
                </>
              )}
          </section>
          <section className="panel">
            <h2>3. Lớp đã đăng ký</h2>
            <p className="muted">Sinh viên {studentId} · {enrollments.length} lớp</p>
            <EnrollmentList rows={enrollments} disabled={disabled}
              onCancel={(id) => changeEnrollment(id, true)} />
          </section>
        </div>
      )}
      {!loading && !error && (
        <EnrollmentHistory
          studentId={studentId}
          rows={history}
          page={historyPage}
          hasNext={historyHasNext}
          loading={historyLoading}
          error={historyError}
          onPrevPage={() => setHistoryPage((p) => Math.max(0, p - 1))}
          onNextPage={() => setHistoryPage((p) => p + 1)}
        />
      )}
      <footer>Số chỗ và đăng ký được đọc từ API; Backend quyết định tính hợp lệ.</footer>
    </main>
  );
}

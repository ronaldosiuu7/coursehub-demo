from __future__ import annotations

from typing import Literal

import logging

from fastapi import FastAPI, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .database import engine
from .schemas import EnrollmentCreate, SectionCapacityUpdate

logger = logging.getLogger(__name__)
app = FastAPI(
    title="CourseHub API",
    version="0.4.0",
    description="API thuc hanh Buoi 4 - transaction, locking va hieu nang",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "CourseHub API dang hoat dong"}


@app.get("/health")
def health_check() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("Khong ket noi duoc co so du lieu")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Khong ket noi duoc co so du lieu",
        ) from exc
    return {"status": "ok", "database": "connected"}


@app.get("/lecturers")
def list_lecturers() -> list[dict[str, object]]:
    sql = """
        SELECT id, name
        FROM lecturers
        ORDER BY id
    """

    with engine.connect() as connection:
        rows = connection.execute(text(sql)).mappings().all()

    return [dict(row) for row in rows]


@app.get("/courses")
def list_courses(
    q: str | None = Query(default=None, min_length=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict[str, object]]:
    sql = """
        SELECT code, name, credits
        FROM courses
    """
    parameters: dict[str, object] = {}

    if q is not None:
        keyword = q.strip().lower()
        if not keyword:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tu khoa tim kiem khong duoc rong",
            )
        sql += """
            WHERE LOWER(code) LIKE :keyword
               OR LOWER(name) LIKE :keyword
        """
        parameters["keyword"] = f"%{keyword}%"

    sql += " ORDER BY code OFFSET :skip LIMIT :limit"
    parameters["skip"] = skip
    parameters["limit"] = limit

    with engine.connect() as connection:
        rows = connection.execute(text(sql), parameters).mappings().all()
    return [dict(row) for row in rows]


@app.get("/courses/{course_code}")
def get_course(course_code: str) -> dict[str, object]:
    sql = """
        SELECT code, name, credits
        FROM courses
        WHERE code = :course_code
    """

    with engine.connect() as connection:
        row = connection.execute(
            text(sql),
            {"course_code": course_code.upper()},
        ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay hoc phan",
        )

    return dict(row)


@app.get("/sections")
def list_sections(
    available_only: bool = False,
) -> list[dict[str, object]]:
    sql = """
        SELECT class_id, course_code, capacity, enrolled, remaining
        FROM v_section_summary
    """
    if available_only:
        sql += " WHERE remaining > 0"

    sql += " ORDER BY class_id"
    with engine.connect() as connection:
        rows = connection.execute(text(sql)).mappings().all()
    return [dict(row) for row in rows]


@app.get("/sections/{section_id}")
def get_section(section_id: str) -> dict[str, object]:
    sql = """
        SELECT cs.id AS class_id,
               c.code AS course_code,
               c.name AS course_name,
               sem.code AS semester_code,
               sem.name AS semester_name,
               lec.id AS lecturer_id,
               lec.name AS lecturer_name,
               cs.capacity,
               summary.enrolled,
               summary.remaining
        FROM class_sections AS cs
        JOIN courses AS c ON c.code = cs.course_code
        JOIN semesters AS sem ON sem.code = cs.semester_code
        JOIN lecturers AS lec ON lec.id = cs.lecturer_id
        JOIN v_section_summary AS summary ON summary.class_id = cs.id
        WHERE cs.id = :section_id
    """

    with engine.connect() as connection:
        row = connection.execute(
            text(sql),
            {"section_id": section_id.upper()},
        ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay lop hoc phan",
        )

    return dict(row)


@app.patch("/sections/{section_id}/capacity")
def update_section_capacity(
    section_id: str,
    payload: SectionCapacityUpdate,
) -> dict[str, object]:
    section_sql = """
        SELECT cs.id,
               COUNT(e.student_id) AS enrolled
        FROM class_sections AS cs
        LEFT JOIN enrollments AS e ON e.class_section_id = cs.id
        WHERE cs.id = :section_id
        GROUP BY cs.id
    """
    update_sql = """
        UPDATE class_sections
        SET capacity = :capacity
        WHERE id = :section_id
    """
    parameters = {
        "section_id": section_id.upper(),
        "capacity": payload.capacity,
    }

    with engine.begin() as connection:
        section = connection.execute(
            text(section_sql),
            {"section_id": parameters["section_id"]},
        ).mappings().first()

        if section is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Khong tim thay lop hoc phan",
            )

        if payload.capacity < int(section["enrolled"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Suc chua khong duoc nho hon so sinh vien da dang ky",
            )

        connection.execute(text(update_sql), parameters)

    return {
        "message": "Cap nhat suc chua thanh cong",
        "class_section_id": str(parameters["section_id"]),
        "capacity": payload.capacity,
        "remaining": payload.capacity - int(section["enrolled"]),
    }


@app.get("/students/{student_id}/enrollments")
def list_student_enrollments(student_id: str) -> list[dict[str, object]]:
    student_sql = "SELECT id FROM students WHERE id = :student_id"
    enrollment_sql = """
        SELECT e.student_id,
               s.name AS student_name,
               cs.id AS class_section_id,
               c.code AS course_code,
               c.name AS course_name,
               e.registered_at
        FROM enrollments AS e
        JOIN students AS s ON s.id = e.student_id
        JOIN class_sections AS cs ON cs.id = e.class_section_id
        JOIN courses AS c ON c.code = cs.course_code
        WHERE e.student_id = :student_id
        ORDER BY cs.id
    """

    with engine.connect() as connection:
        student = connection.execute(
            text(student_sql),
            {"student_id": student_id},
        ).first()
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Khong tim thay sinh vien",
            )

        rows = connection.execute(
            text(enrollment_sql),
            {"student_id": student_id},
        ).mappings().all()

    return [dict(row) for row in rows]



@app.post(
    "/enrollments",
    status_code=status.HTTP_201_CREATED,
)
def create_enrollment(payload: EnrollmentCreate) -> dict[str, str]:
    student_sql = "SELECT id FROM students WHERE id = :student_id"

    lock_section_sql = """
    SELECT id, capacity
    FROM class_sections
    WHERE id = :class_section_id
    FOR UPDATE
    """

    duplicate_sql = """
    SELECT 1
    FROM enrollments
    WHERE student_id = :student_id
    AND class_section_id = :class_section_id
    """

    count_sql = """
    SELECT COUNT(*)
    FROM enrollments
    WHERE class_section_id = :class_section_id
    """

    insert_sql = """
    INSERT INTO enrollments (student_id, class_section_id)
    VALUES (:student_id, :class_section_id)
    """

    event_sql = """
    INSERT INTO enrollment_events
    (student_id, class_section_id, event_type, source, dataset)
    VALUES
    (:student_id, :class_section_id, 'CREATED', 'api', 'demo')
    """

    parameters = {
        "student_id": payload.student_id,
        "class_section_id": payload.class_section_id,
    }

    try:
        with engine.begin() as connection:
            student = connection.execute(
                text(student_sql),
                {"student_id": payload.student_id},
            ).first()

            if student is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Khong tim thay sinh vien",
                )

            section = connection.execute(
                text(lock_section_sql),
                {"class_section_id": payload.class_section_id},
            ).mappings().first()

            if section is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Khong tim thay lop hoc phan",
                )

            duplicated = connection.execute(
                text(duplicate_sql), parameters
            ).first()

            if duplicated is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Sinh vien da dang ky lop nay",
                )

            enrolled = connection.execute(
                text(count_sql),
                {"class_section_id": payload.class_section_id},
            ).scalar_one()

            if int(enrolled) >= int(section["capacity"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Lop hoc phan da het cho",
                )

            connection.execute(text(insert_sql), parameters)
            connection.execute(text(event_sql), parameters)

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dang ky xung dot voi du lieu hien tai",
        ) from exc

    return {
        "message": "Dang ky thanh cong",
        "student_id": payload.student_id,
        "class_section_id": payload.class_section_id,
    }




@app.delete(
    "/enrollments/{student_id}/{class_section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_enrollment(student_id: str, class_section_id: str) -> Response:
    lock_section_sql = """
    SELECT id
    FROM class_sections
    WHERE id = :class_section_id
    FOR UPDATE
    """

    delete_sql = """
    DELETE FROM enrollments
    WHERE student_id = :student_id
    AND class_section_id = :class_section_id
    RETURNING student_id
    """

    event_sql = """
    INSERT INTO enrollment_events
    (student_id, class_section_id, event_type, source, dataset)
    VALUES
    (:student_id, :class_section_id, 'CANCELLED', 'api', 'demo')
    """

    parameters = {
        "student_id": student_id,
        "class_section_id": class_section_id,
    }

    with engine.begin() as connection:
        section = connection.execute(
            text(lock_section_sql),
            {"class_section_id": class_section_id},
        ).first()

        if section is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Khong tim thay lop hoc phan",
            )

        deleted = connection.execute(
            text(delete_sql), parameters
        ).first()

        if deleted is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Khong tim thay dang ky can huy",
            )

        connection.execute(text(event_sql), parameters)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/enrollment-events")
def get_enrollment_events(
    student_id: str | None = None,
    event_type: Literal["CREATED", "CANCELLED"] | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict[str, object]]:
    sql = """
        SELECT id, student_id, class_section_id,
               event_type, source, dataset, occurred_at
        FROM enrollment_events
        WHERE 1 = 1
    """

    parameters: dict[str, object] = {
        "skip": skip,
        "limit": limit,
    }

    if student_id is not None:
        sql += " AND student_id = :student_id"
        parameters["student_id"] = student_id

    if event_type is not None:
        sql += " AND event_type = :event_type"
        parameters["event_type"] = event_type

    sql += """
        ORDER BY occurred_at DESC, id DESC
        LIMIT :limit OFFSET :skip
    """

    with engine.connect() as connection:
        rows = connection.execute(
            text(sql), parameters
        ).mappings().all()

    return [dict(row) for row in rows]

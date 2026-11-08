"""Exercise 2: real PostgreSQL rollback using session-local temporary tables.

Run: python -m unittest backend.tests.week04_rollback_test -v
Calls the production create_enrollment function; fault injection stays in tests.
"""
from contextlib import contextmanager
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app import main
from backend.app.database import engine
from backend.app.schemas import EnrollmentCreate


class TransactionEngine:
    """Use the test connection while retaining real COMMIT/ROLLBACK behavior."""

    def __init__(self, connection, fail_event=False):
        self.connection = connection
        self.fail_event = fail_event
        self.enrollments_before_failure = None
        self.constraint = None
        self.sqlstate = None

    @contextmanager
    def begin(self):
        with self.connection.begin():
            yield self

    def execute(self, statement, parameters=None):
        if self.fail_event and "INSERT INTO enrollment_events" in str(statement):
            # Prove the first INSERT succeeded inside this same transaction.
            self.enrollments_before_failure = self.connection.execute(
                text("SELECT COUNT(*) FROM enrollments")
            ).scalar_one()
            statement = text(str(statement).replace("'CREATED'", "'INVALID'"))
            try:
                return self.connection.execute(statement, parameters)
            except IntegrityError as exc:
                self.constraint = exc.orig.diag.constraint_name
                self.sqlstate = exc.orig.sqlstate
                raise
        return self.connection.execute(statement, parameters)


class EnrollmentRollbackTest(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.addCleanup(self.close_connection)
        with self.connection.begin():
            # PostgreSQL resolves these session-local tables before public tables.
            # INCLUDING ALL copies CHECK constraints and creates a separate identity.
            for table in ('students', 'class_sections', 'enrollments', 'enrollment_events'):
                self.connection.execute(text(
                    f"CREATE TEMP TABLE {table} (LIKE public.{table} INCLUDING ALL)"
                ))
            self.connection.execute(text(
                "INSERT INTO students SELECT * FROM public.students ORDER BY id LIMIT 1"
            ))
            self.connection.execute(text(
                "INSERT INTO class_sections SELECT * FROM public.class_sections ORDER BY id LIMIT 1"
            ))
            student = self.connection.execute(text("SELECT id FROM students")).scalar_one()
            section = self.connection.execute(text("SELECT id FROM class_sections")).scalar_one()
        self.payload = EnrollmentCreate(student_id=student, class_section_id=section)

    def close_connection(self):
        # Destroy the physical session so temporary tables cannot leak through the pool.
        self.connection.invalidate()
        self.connection.close()

    def counts(self):
        with self.connection.begin():
            return tuple(self.connection.execute(text(
                "SELECT (SELECT COUNT(*) FROM enrollments), "
                "(SELECT COUNT(*) FROM enrollment_events)"
            )).one())

    def test_invalid_event_rolls_back_both_tables(self):
        before = self.counts()
        test_engine = TransactionEngine(self.connection, fail_event=True)
        with patch.object(main, 'engine', test_engine):
            with self.assertRaises(HTTPException) as caught:
                main.create_enrollment(self.payload)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(test_engine.enrollments_before_failure, 1)
        self.assertEqual(test_engine.sqlstate, '23514')
        self.assertEqual(test_engine.constraint, 'ck_enrollment_events_type')
        self.assertEqual(before, (0, 0))
        self.assertEqual(self.counts(), before)
        print("ROLLBACK: before=(0, 0), after enrollment INSERT=1, "
              "event CHECK violation=23514, after=(0, 0), HTTPException=409")

    def test_valid_event_commits_both_tables(self):
        self.assertEqual(self.counts(), (0, 0))
        with patch.object(main, 'engine', TransactionEngine(self.connection)):
            result = main.create_enrollment(self.payload)
        self.assertEqual(result['student_id'], self.payload.student_id)
        self.assertEqual(self.counts(), (1, 1))
        with self.connection.begin():
            event = self.connection.execute(text(
                "SELECT student_id, class_section_id, event_type FROM enrollment_events"
            )).one()
        self.assertEqual(tuple(event), (
            self.payload.student_id, self.payload.class_section_id, 'CREATED'
        ))
        print("COMMIT: before=(0, 0), after=(1, 1), event_type=CREATED")


if __name__ == '__main__':
    unittest.main()

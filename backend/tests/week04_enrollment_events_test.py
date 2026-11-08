"""Read-only integration checks against PostgreSQL; starts its own local API.

Run from the repository root:
    python -m unittest backend.tests.week04_enrollment_events_test -v
Requires migration 001 and at least one enrollment event. No data is written.
"""
import socket
import subprocess
import sys
import time
import unittest

import requests
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text

from backend.app.database import engine


class EnrollmentEventsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with engine.connect() as connection:
            cls.total = connection.execute(text("SELECT COUNT(*) FROM enrollment_events")).scalar_one()
            cls.sample = connection.execute(text(
                "SELECT student_id, event_type FROM enrollment_events ORDER BY id LIMIT 1"
            )).mappings().first()
        if cls.sample is None:
            raise RuntimeError("Need at least one enrollment event for the nonempty case")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.base = f"http://127.0.0.1:{port}"
        cls.server = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "backend.app.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "error",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(cls.stop_server)
        for _ in range(100):
            try:
                if requests.get(cls.base + "/health", timeout=2).status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(0.1)
        raise RuntimeError("Test API did not become healthy")

    @classmethod
    def stop_server(cls):
        cls.server.terminate()
        cls.server.wait(timeout=10)

    def get(self, **params):
        return requests.get(self.base + "/enrollment-events", params=params, timeout=10)

    def test_filters_and_serialization(self):
        params = dict(self.sample)
        response = self.get(**params, limit=100)
        self.assertEqual(response.status_code, 200)
        with engine.connect() as connection:
            expected = connection.execute(text(
                "SELECT id, student_id, class_section_id, event_type, source, dataset, occurred_at "
                "FROM enrollment_events WHERE student_id = :student_id AND event_type = :event_type "
                "ORDER BY occurred_at DESC, id DESC LIMIT 100"
            ), params).mappings().all()
        self.assertTrue(expected)
        self.assertEqual(response.json(), jsonable_encoder([dict(row) for row in expected]))

    def test_each_filter(self):
        for key, value in self.sample.items():
            with self.subTest(filter=key):
                response = self.get(**{key: value})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json())
                self.assertTrue(all(row[key] == value for row in response.json()))

    def test_empty_and_sql_input(self):
        for student in ("__no_student__", "' OR '1'='1' --"):
            with self.subTest(student=student):
                response = self.get(student_id=student)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [])

    def test_pagination_and_order(self):
        first = self.get(skip=0, limit=2)
        second = self.get(skip=2, limit=2)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        with engine.connect() as connection:
            ids = connection.execute(text(
                "SELECT id FROM enrollment_events ORDER BY occurred_at DESC, id DESC LIMIT 4"
            )).scalars().all()
        self.assertEqual([row['id'] for row in first.json()], ids[:2])
        self.assertEqual([row['id'] for row in second.json()], ids[2:])

    def test_validation(self):
        for params in ({'limit': 0}, {'limit': 101}, {'skip': -1},
                       {'event_type': 'INVALID'}, {'limit': 'abc'}):
            with self.subTest(params=params):
                self.assertEqual(self.get(**params).status_code, 422)

    def test_defaults_and_bounds(self):
        self.assertEqual(len(self.get().json()), min(10, self.total))
        for limit in (1, 100):
            response = self.get(limit=limit)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()), min(limit, self.total))

    @classmethod
    def tearDownClass(cls):
        with engine.connect() as connection:
            total = connection.execute(text("SELECT COUNT(*) FROM enrollment_events")).scalar_one()
        if total != cls.total:
            raise AssertionError("Event count changed during read-only tests")


if __name__ == '__main__':
    unittest.main()

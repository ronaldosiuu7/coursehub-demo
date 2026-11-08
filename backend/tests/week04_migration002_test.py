"""Run the actual migration files on temporary copies of existing PostgreSQL data.

Run: python -m unittest backend.tests.week04_migration002_test -v
No public tables or production sequences are modified.
"""
from pathlib import Path
import unittest

import psycopg

from backend.app.database import engine


MIGRATIONS = Path(__file__).resolve().parents[2] / 'database' / 'migrations'
COLUMNS = 'id, student_id, class_section_id, event_type, source, dataset, occurred_at'


class Migration002Test(unittest.TestCase):
    def setUp(self):
        self.pool_connection = engine.raw_connection()
        self.addCleanup(self.close_connection)
        self.connection = self.pool_connection.driver_connection
        self.connection.autocommit = True
        with self.connection.cursor() as cursor:
            cursor.execute('SET statement_timeout = \'60s\'')
            cursor.execute('CREATE TEMP TABLE enrollment_events '
                           '(LIKE public.enrollment_events INCLUDING ALL)')
            # Allow repeatable tests even after the user applies 002 in public.
            cursor.execute('ALTER TABLE pg_temp.enrollment_events DROP COLUMN IF EXISTS note')
            cursor.execute(f'INSERT INTO pg_temp.enrollment_events ({COLUMNS}) '
                           f'OVERRIDING SYSTEM VALUE SELECT {COLUMNS} FROM public.enrollment_events')
            cursor.execute('CREATE TEMP TABLE schema_migrations '
                           '(LIKE public.schema_migrations INCLUDING ALL)')
            cursor.execute("INSERT INTO pg_temp.schema_migrations "
                           "SELECT * FROM public.schema_migrations WHERE version <> '002'")
            cursor.execute('CREATE TEMP TABLE original_events AS '
                           f'SELECT {COLUMNS} FROM pg_temp.enrollment_events')
            cursor.execute('SELECT COUNT(*) FROM pg_temp.enrollment_events')
            self.count = cursor.fetchone()[0]
            if self.count == 0:
                raise RuntimeError('Need existing events to verify preservation')
            cursor.execute("SELECT COUNT(*) FROM pg_temp.schema_migrations WHERE version='001'")
            self.assertEqual(cursor.fetchone()[0], 1)

    def close_connection(self):
        self.pool_connection.invalidate()
        self.pool_connection.close()

    def run_file(self, name):
        with self.connection.cursor() as cursor:
            cursor.execute((MIGRATIONS / name).read_text(encoding='utf-8'))

    def scalar(self, sql, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()[0]

    def assert_original_data(self):
        # Compare every original value in both directions, not just row counts.
        difference = self.scalar(
            f'SELECT COUNT(*) FROM ((SELECT {COLUMNS} FROM pg_temp.enrollment_events '
            'EXCEPT ALL SELECT * FROM original_events) UNION ALL '
            f'(SELECT * FROM original_events EXCEPT ALL SELECT {COLUMNS} '
            'FROM pg_temp.enrollment_events)) AS differences'
        )
        self.assertEqual(difference, 0)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM pg_temp.enrollment_events'), self.count)

    def test_migration_validation_rollback_and_reapply(self):
        forward = '002_add_enrollment_event_note.sql'
        rollback = '002_add_enrollment_event_note_rollback.sql'
        self.run_file(forward)
        self.assert_original_data()
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM pg_temp.enrollment_events '
                                     'WHERE note IS NULL'), self.count)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM pg_temp.schema_migrations "
                                     "WHERE version='002'"), 1)
        self.assertEqual(self.scalar("SELECT atttypmod FROM pg_attribute WHERE "
                                     "attrelid='pg_temp.enrollment_events'::regclass "
                                     "AND attname='note' AND NOT attisdropped"), 204)
        print(f'APPLY: {self.count} original rows unchanged; note=NULL; version 002 recorded')

        # The migration is intentionally single-use. A second run must not hide drift.
        with self.assertRaises(psycopg.errors.DuplicateColumn):
            self.run_file(forward)
        self.connection.execute('ROLLBACK')
        self.assert_original_data()
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM pg_temp.schema_migrations "
                                     "WHERE version='002'"), 1)

        update = ('UPDATE pg_temp.enrollment_events SET note=%s '
                  'WHERE id=(SELECT MIN(id) FROM pg_temp.enrollment_events)')
        self.connection.execute(update, ('a' * 200,))
        with self.assertRaises(psycopg.errors.StringDataRightTruncation):
            self.connection.execute(update, ('a' * 201,))
        self.assertEqual(self.scalar('SELECT MAX(length(note)) FROM pg_temp.enrollment_events'), 200)
        print('VALIDATION: 200 characters accepted; 201 rejected; duplicate apply rejected')

        self.run_file(rollback)
        self.assert_original_data()
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM pg_attribute WHERE "
                                     "attrelid='pg_temp.enrollment_events'::regclass "
                                     "AND attname='note' AND NOT attisdropped"), 0)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM pg_temp.schema_migrations "
                                     "WHERE version='002'"), 0)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM pg_temp.schema_migrations "
                                     "WHERE version='001'"), 1)
        print('ROLLBACK: original rows preserved; note column and version 002 removed')

        self.run_file(forward)
        self.assert_original_data()
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM pg_temp.enrollment_events '
                                     'WHERE note IS NOT NULL'), 0)
        print('REAPPLY: succeeds; deleted note values do not return')


if __name__ == '__main__':
    unittest.main()

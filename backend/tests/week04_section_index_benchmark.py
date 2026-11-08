"""Measure a second index on real PostgreSQL and roll back the trial index.

Run from repository root:
python -m backend.tests.week04_section_index_benchmark
Prints JSON evidence. Does not generate, delete, or modify enrollment events.
"""
import json
from statistics import median

from sqlalchemy import text

from backend.app.database import engine


INDEX = 'idx_enrollment_events_dataset_section_type_time'
QUERY = """
SELECT id, student_id, class_section_id, event_type, occurred_at
FROM public.enrollment_events
WHERE dataset = :dataset
  AND class_section_id = :section
  AND event_type = :event_type
  AND occurred_at >= CAST(:since AS timestamp)
ORDER BY occurred_at DESC, id DESC
LIMIT 50
"""
PARAMS = dict(dataset='performance', section='WEB-01',
              event_type='CREATED', since='2025-12-20 00:00:00')


def measure(connection):
    plans = [connection.execute(text(
        'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + QUERY
    ), PARAMS).scalar_one()[0] for _ in range(3)]
    return {
        'execution_ms': [plan['Execution Time'] for plan in plans],
        'median_execution_ms': median(plan['Execution Time'] for plan in plans),
        'plans': plans,
    }


def benchmark():
    with engine.connect() as connection:
        report = {'parameters': PARAMS, 'query': QUERY.strip()}
        # DDL and ANALYZE are enclosed in the transaction; always roll back.
        with connection.begin() as transaction:
            connection.execute(text("SET LOCAL lock_timeout = '5s'"))
            connection.execute(text("SET LOCAL statement_timeout = '60s'"))
            if connection.execute(text(
                'SELECT to_regclass(:name)'
            ), {'name': 'public.' + INDEX}).scalar_one() is not None:
                raise RuntimeError('Trial index already exists; not dropping an existing index.')
            report['dataset_counts'] = dict(connection.execute(text(
                'SELECT dataset, COUNT(*) FROM public.enrollment_events GROUP BY dataset'
            )).all())
            if report['dataset_counts'].get('performance', 0) < 100000:
                raise RuntimeError('Prepare at least 100000 performance events before measuring.')
            connection.execute(text('ANALYZE public.enrollment_events'))
            report['before'] = measure(connection)
            before = connection.execute(text(QUERY), PARAMS).all()
            if not before:
                raise RuntimeError('Benchmark query must return data.')
            connection.execute(text(
                f'CREATE INDEX {INDEX} ON public.enrollment_events '
                '(dataset, class_section_id, event_type, occurred_at DESC, id DESC)'
            ))
            report['after'] = measure(connection)
            after = connection.execute(text(QUERY), PARAMS).all()
            if before != after:
                raise AssertionError('Query results changed after adding index.')
            report['same_results'] = True
            report['returned_rows'] = len(after)
            report['index_bytes'] = connection.execute(text(
                'SELECT pg_relation_size(CAST(:name AS regclass))'
            ), {'name': 'public.' + INDEX}).scalar_one()
            transaction.rollback()
        report['trial_index_removed'] = connection.execute(text(
            'SELECT to_regclass(:name) IS NULL'
        ), {'name': 'public.' + INDEX}).scalar_one()
        if not report['trial_index_removed']:
            raise AssertionError('Trial index was not rolled back.')
        return report


if __name__ == '__main__':
    print(json.dumps(benchmark(), indent=2, default=str))

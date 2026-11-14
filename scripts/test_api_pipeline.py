"""Real HTTP -> Redis/Celery -> PostgreSQL integration smoke test.

Starts an API and solo worker on a unique queue. Existing processes are untouched.
Requires the project's services and model dependencies. Keeps job/report evidence.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import UUID, uuid4
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from database.connection import get_connection
from database.jobs import get_job
from worker.celery_app import celery_app

ROOT = Path(__file__).resolve().parents[1]


def main():
    suffix = uuid4().hex[:10]
    queue = f'integration_{suffix}'
    node = f'integration_{suffix}@localhost'
    output = ROOT / 'evaluation_results' / ('api_integration_' + datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%Y%m%d_%H%M%S'))
    output.mkdir(parents=True)
    summary = {'status': 'running', 'queue': queue, 'checks': [], 'jobs': []}
    processes, handles = [], []
    start = time.perf_counter()

    def save():
        (output / 'results.json').write_text(json.dumps(summary, indent=2, default=str))

    def check(name, condition):
        summary['checks'].append({'name': name, 'passed': bool(condition)})
        save()
        if not condition:
            raise AssertionError(name)
        print(f'PASS: {name}', flush=True)

    def launch(name, args):
        handle = (output / f'{name}.log').open('w')
        handles.append(handle)
        process = subprocess.Popen(args, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                                   env={**os.environ, 'PYTHONUNBUFFERED': '1'})
        processes.append(process)
        return process

    def submit(client, files):
        response = client.post('/investigations', data={'run_id': 'RUN-1042'}, files=files)
        check('Upload accepted with HTTP 202', response.status_code == 202)
        body = response.json()
        record = {'job_id': body['job_id'], 'submission': body, 'states': [], 'submitted_at': time.time()}
        summary['jobs'].append(record)
        save()
        return record

    def follow(client, record, expected, timeout=480):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = client.get(record['submission']['status_url'])
            response.raise_for_status()
            body = response.json()
            if not record['states'] or record['states'][-1]['status'] != body['status']:
                record['states'].append({'status': body['status'], 'elapsed_seconds': time.time() - record['submitted_at']})
                print(f"Job {record['job_id']}: {body['status']}", flush=True)
                save()
            if body['status'] in ('SUCCEEDED', 'FAILED'):
                record['api_result'] = body
                record['elapsed_seconds'] = time.time() - record['submitted_at']
                row = get_job(UUID(record['job_id']))
                record['database_result'] = row
                save()
                check(f'Job finished as {expected}', body['status'] == expected)
                check('API status matches PostgreSQL', row['status'] == body['status'])
                check('Database records start and finish timestamps', row['started_at'] is not None and row['finished_at'] >= row['started_at'] >= row['created_at'])
                return body
            time.sleep(2)
        raise TimeoutError(f"Job {record['job_id']} did not finish within {timeout}s")

    try:
        print(f'Artifacts: {output}', flush=True)
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT to_regclass('public.investigation_jobs')")
                check('PostgreSQL job table exists', cursor.fetchone()[0] is not None)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        summary['api_url'] = f'http://127.0.0.1:{port}'
        launcher = ('import sys, uvicorn; from worker.celery_app import celery_app; '
                    'celery_app.conf.task_default_queue=sys.argv[1]; '
                    'uvicorn.run("api:app",host="127.0.0.1",port=int(sys.argv[2]))')
        api_process = launch('api', [sys.executable, '-c', launcher, queue, str(port)])
        worker_process = launch('worker', [sys.executable, '-m', 'celery', '-A', 'worker.celery_app:celery_app',
                                          'worker', '--pool=solo', '--concurrency=1', '--loglevel=info',
                                          '-Q', queue, '-n', node, '--without-gossip', '--without-mingle'])
        with httpx.Client(base_url=summary['api_url'], timeout=15) as client:
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if api_process.poll() is not None or worker_process.poll() is not None:
                    raise RuntimeError('Test API or worker exited; see logs')
                try:
                    ready = client.get('/openapi.json').status_code == 200
                except httpx.HTTPError:
                    ready = False
                if ready and ' ready.' in (output / 'worker.log').read_text():
                    break
                time.sleep(1)
            else:
                raise TimeoutError('API/worker startup timed out')
            check('Real HTTP API and dedicated worker are ready', True)
            check('Unknown job returns 404', client.get(f'/investigations/{uuid4()}').status_code == 404)
            for name, log, config, status in [
                ('Empty log rejected', b'', None, 422),
                ('Non-UTF8 log rejected', b'\xff', None, 422),
                ('Mismatched configuration rejected', b'log', b'{"run_id":"RUN-9999"}', 422),
                ('Oversized log rejected', b'x' * (1024 * 1024 + 1), None, 413),
            ]:
                files = {'execution_log': ('execution.log', log, 'text/plain')}
                if config is not None:
                    files['configuration'] = ('config.json', config, 'application/json')
                response = client.post('/investigations', data={'run_id': 'RUN-1042'}, files=files)
                check(name, response.status_code == status)
            log = (ROOT / 'data/runs/RUN-1042/execution.log').read_bytes()
            config = (ROOT / 'data/runs/RUN-1042/config.json').read_bytes()
            record = submit(client, {'execution_log': ('execution.log', log, 'text/plain'),
                                     'configuration': ('config.json', config, 'application/json')})
            job_dir = ROOT / 'data/jobs' / record['job_id']
            check('Uploaded log and config saved without changes', (job_dir/'execution.log').read_bytes() == log and (job_dir/'config.json').read_bytes() == config)
            body = follow(client, record, 'SUCCEEDED')
            report_path = ROOT / body['report_file']
            report = report_path.read_text()
            (output / 'report.md').write_text(report)
            check('Database and API agree on generated report path', record['database_result']['report_file'] == body['report_file'])
            check('Report exists and includes run and throughput values', all(value in report for value in ('RUN-1042', '42', '100', '50')))
            result = celery_app.AsyncResult(record['job_id'])
            deadline = time.monotonic() + 10
            while not result.ready() and time.monotonic() < deadline:
                time.sleep(.5)
            check('Redis Celery result is SUCCESS', result.state == 'SUCCESS')
            check('Celery result identifies the same report', result.result['report_file'] == body['report_file'])
            # A valid upload containing one oversized entry must fail cleanly in chunking.
            failed = submit(client, {'execution_log': ('execution.log', b'word ' * 4000, 'text/plain')})
            body = follow(client, failed, 'FAILED', timeout=60)
            check('Failed job exposes a safe error without report', body['error'] == 'Investigation failed. Check worker logs for details.' and body['report_file'] is None)
            check('Database stores useful failure detail', 'exceeds 2000 tokens' in failed['database_result']['error_message'])
            failure_result = celery_app.AsyncResult(failed['job_id'])
            deadline = time.monotonic() + 10
            while not failure_result.ready() and time.monotonic() < deadline:
                time.sleep(.5)
            check('Redis Celery result is FAILURE', failure_result.state == 'FAILURE')
        summary['status'] = 'passed'
    except Exception as error:
        summary['status'] = 'failed'
        summary['error'] = str(error)
        print(f'FAILED: {error}', flush=True)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        for handle in handles:
            handle.close()
        summary['total_seconds'] = time.perf_counter() - start
        save()
        print(f"{summary['status']}: {summary['total_seconds']:.2f}s; {output}", flush=True)
    if summary['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

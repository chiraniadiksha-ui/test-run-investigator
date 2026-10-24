from uuid import UUID

from psycopg.rows import dict_row

from database.connection import get_connection


def create_job(job_id: UUID, run_id: str):
    query = """
        INSERT INTO investigation_jobs (job_id, run_id)
        VALUES (%s, %s)
        RETURNING *;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (job_id, run_id))
            job = cursor.fetchone()

    return job


def get_job(job_id: UUID):
    query = """
        SELECT *
        FROM investigation_jobs
        WHERE job_id = %s;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (job_id,))
            job = cursor.fetchone()

    return job
def mark_job_queued(job_id: UUID):
    query = """
        UPDATE investigation_jobs
        SET status = 'QUEUED'
        WHERE job_id = %s
          AND status = 'CREATED'
        RETURNING *;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (job_id,))
            job = cursor.fetchone()

    return job


def mark_job_running(job_id: UUID):
    query = """
        UPDATE investigation_jobs
        SET status = 'RUNNING',
            started_at = CURRENT_TIMESTAMP
        WHERE job_id = %s
          AND status IN ('CREATED', 'QUEUED')
        RETURNING *;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (job_id,))
            job = cursor.fetchone()

    return job


def mark_job_succeeded(job_id: UUID, report_file: str):
    query = """
        UPDATE investigation_jobs
        SET status = 'SUCCEEDED',
            finished_at = CURRENT_TIMESTAMP,
            report_file = %s,
            error_message = NULL
        WHERE job_id = %s
          AND status = 'RUNNING'
        RETURNING *;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (report_file, job_id))
            job = cursor.fetchone()

    return job


def mark_job_failed(job_id: UUID, error_message: str):
    query = """
        UPDATE investigation_jobs
        SET status = 'FAILED',
            finished_at = CURRENT_TIMESTAMP,
            error_message = %s
        WHERE job_id = %s
          AND status IN ('CREATED', 'QUEUED', 'RUNNING')
        RETURNING *;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (error_message, job_id))
            job = cursor.fetchone()

    return job

if __name__ == "__main__":
    from uuid import uuid4

    job_id = uuid4()

    created_job = create_job(job_id, "RUN-1042")
    print("Created job:", created_job["job_id"])
    print("Initial status:", created_job["status"])

    saved_job = get_job(job_id)

    assert saved_job is not None
    assert saved_job["run_id"] == "RUN-1042"
    assert saved_job["status"] == "CREATED"

    assert get_job(uuid4()) is None

    print("Create and read checks passed")
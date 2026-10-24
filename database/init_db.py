from database.connection import get_connection


CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS investigation_jobs (
    job_id UUID PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'CREATED'
        CHECK (
            status IN (
                'CREATED',
                'QUEUED',
                'RUNNING',
                'SUCCEEDED',
                'FAILED'
            )
        ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,

    report_file TEXT,
    error_message TEXT
);
"""


def initialize_database():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_JOBS_TABLE)

    print("investigation_jobs table is ready")


if __name__ == "__main__":
    initialize_database()
from worker.celery_app import celery_app
import re
import logging
from uuid import UUID

from database.jobs import (
    mark_job_running,
    mark_job_succeeded,
    mark_job_failed,
)
logger = logging.getLogger(__name__)

@celery_app.task(name="worker.check_queue")
def check_queue(message):
    return {
        "message": message,
        "processed_by": "celery_worker",
    }

def _run_investigation(self, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r"RUN-\d+", run_id):
        raise ValueError("Expected a run ID such as RUN-1042.")

    # Imports happen during task execution, inside the worker.
    from investigate import (
        PROJECT_DIR,
        read_run_log,
        build_search_query,
        retrieve_guides,
        generate_investigation,
        get_models
    )

    # Check the input before loading expensive models.
    log_text = read_run_log(run_id)
    query = build_search_query(log_text)

    tokenizer, model, embedding_model,device= get_models()

    guides = retrieve_guides(
        query,
        embedding_model,
        top_k=1,
    )

    report = generate_investigation(
        run_id=run_id,
        log_text=log_text,
        retrieved_guides=guides
    )

    # Our existing function returns this prefix for invalid tool requests.
    # Raise an exception so Celery records FAILURE instead of SUCCESS.
    if report.startswith("Investigation stopped:"):
        raise RuntimeError(report)

    reports_dir = PROJECT_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    task_id = self.request.id
    report_path = reports_dir / f"{task_id}.md"

    report_path.write_text(
        f"# Investigation: {run_id}\n\n{report}\n",
        encoding="utf-8",
    )

    return {
        "task_id": task_id,
        "run_id": run_id,
        "report_file": str(report_path.relative_to(PROJECT_DIR)),
    }


@celery_app.task(bind=True, name="worker.investigate_run")
def investigate_run(self, run_id):
    job_id = UUID(self.request.id)

    # This conditional update also prevents a second execution
    # from claiming a job that is already running or finished.
    job = mark_job_running(job_id)

    if job is None:
        raise RuntimeError(
            f"Job {job_id} is missing or cannot transition to RUNNING."
        )

    try:
        if job["run_id"] != run_id:
            raise ValueError("Task run ID does not match the job record.")

        result = _run_investigation(self, run_id)

    except Exception as error:
        try:
            mark_job_failed(job_id, str(error))
        except Exception:
            logger.exception(
                "Could not record failure for job %s",
                job_id,
            )

        # Re-raise so Celery also records task failure.
        raise

    saved_job = mark_job_succeeded(
        job_id,
        report_file=result["report_file"],
    )

    if saved_job is None:
        raise RuntimeError(
            f"Could not transition job {job_id} to SUCCEEDED."
        )

    return result
import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from database.jobs import create_job, get_job, mark_job_queued
from worker.tasks import investigate_run


app = FastAPI(title="Test Run Investigator")
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_DIR / "data" / "runs"


class InvestigationRequest(BaseModel):
    run_id: str = Field(
        pattern=r"^RUN-[0-9]+$",
        max_length=64,
        examples=["RUN-1042"],
    )


@app.post("/investigations", status_code=202)
def submit_investigation(request: InvestigationRequest):
    log_path = RUNS_DIR / request.run_id / "execution.log"

    if not log_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Execution log not found for {request.run_id}",
        )

    # Generate the ID before submitting the task.
    job_id = uuid4()

    # Save and commit the record before the worker can start.
    try:
        create_job(job_id, request.run_id)
    except Exception:
        logger.exception("Could not create job record")
        raise HTTPException(
            status_code=503,
            detail="Could not save the investigation request.",
        ) from None

    try:
        investigate_run.apply_async(
            args=[request.run_id],
            task_id=str(job_id),
            retry=False,
        )
    except Exception:
        logger.exception("Could not confirm submission for %s", job_id)

        # A connection failure can leave delivery uncertain.
        # Keep the record rather than incorrectly marking it FAILED.
        raise HTTPException(
            status_code=503,
            detail={
                "message": (
                    "Could not confirm queue submission. "
                    "Check this job's status before submitting again."
                ),
                "job_id": str(job_id),
                "status_url": f"/investigations/{job_id}",
            },
        ) from None

    try:
        mark_job_queued(job_id)
    except Exception:
        # Submission already succeeded. The worker can still
        # transition the record from CREATED to RUNNING.
        logger.exception("Could not mark job %s as queued", job_id)

    return {
        "job_id": str(job_id),
        "run_id": request.run_id,
        "status": "SUBMITTED",
        "status_url": f"/investigations/{job_id}",
    }


@app.get("/investigations/{job_id}")
def get_investigation_status(job_id: UUID):
    try:
        job = get_job(job_id)
    except Exception:
        logger.exception("Could not read job %s", job_id)
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve investigation status.",
        ) from None

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found.",
        )

    return {
        "job_id": job["job_id"],
        "run_id": job["run_id"],
        "status": job["status"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "report_file": job["report_file"],
        "error": (
            "Investigation failed. Check worker logs for details."
            if job["status"] == "FAILED"
            else None
        ),
    }
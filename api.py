import logging
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from worker.celery_app import celery_app
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

    try:
        job = investigate_run.delay(request.run_id)
    except Exception:
        logger.exception("Could not submit investigation")
        raise HTTPException(
            status_code=503,
            detail="Could not submit investigation. Check the queue service.",
        ) from None

    return {
        "job_id": job.id,
        "run_id": request.run_id,
        "status": "SUBMITTED",
        "status_url": f"/investigations/{job.id}",
    }


@app.get("/investigations/{job_id}")
def get_investigation_status(job_id: UUID):
    job = celery_app.AsyncResult(str(job_id))

    try:
        state = job.state

        response = {
            "job_id": str(job_id),
            "status": state,
        }

        if state == "SUCCESS":
            response["result"] = job.result

        elif state == "FAILURE":
            response["error"] = (
                "Investigation failed. Check the worker logs using this job ID."
            )

        elif state == "PENDING":
            response["message"] = (
                "Waiting for execution, or this job ID is unknown "
                "or its result has expired."
            )

    except Exception:
        logger.exception("Could not read investigation status")
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve status. Check the result backend.",
        ) from None

    return response
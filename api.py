import logging
from pathlib import Path
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException
from database.jobs import create_job, get_job, mark_job_queued
from worker.tasks import investigate_run
import json

from fastapi import File, Form, HTTPException, UploadFile
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


app = FastAPI(title="Test Run Investigator")
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_DIR / "data" / "runs"


MAX_LOG_BYTES = 1024 * 1024       # 1 MiB
MAX_CONFIG_BYTES = 256 * 1024    # 256 KiB


class InvestigationRequest(BaseModel):
    run_id: str = Field(
        pattern=r"^RUN-[0-9]+$",
        max_length=64,
        examples=["RUN-1042"],
    )

    log_content: bytes = Field(
        min_length=1,
        max_length=MAX_LOG_BYTES,
    )

    config_content: bytes | None = Field(
        default=None,
        max_length=MAX_CONFIG_BYTES,
    )

    @field_validator("log_content")
    @classmethod
    def validate_log(cls, value):
        try:
            text = value.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Execution log must be UTF-8 text.") from None

        if not text.strip() or "\x00" in text:
            raise ValueError(
                "Execution log must contain non-empty text without NUL bytes."
            )

        return value

    @model_validator(mode="after")
    def validate_configuration(self):
        if self.config_content is None:
            return self

        try:
            config = json.loads(self.config_content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise ValueError(
                "Configuration must contain valid UTF-8 JSON."
            ) from None

        if not isinstance(config, dict):
            raise ValueError("Configuration must be a JSON object.")

        if config.get("run_id") != self.run_id:
            raise ValueError(
                "Configuration run_id must match the submitted run ID."
            )

        return self


@app.post("/investigations", status_code=202)
def submit_investigation(
    run_id: str = Form(...),
    execution_log: UploadFile = File(...),
    configuration: UploadFile | None = File(None),
):
    # Read a bounded amount rather than loading an unlimited file.
    try:
        log_content = execution_log.file.read(MAX_LOG_BYTES + 1)

        config_content = (
            configuration.file.read(MAX_CONFIG_BYTES + 1)
            if configuration is not None
            else None
        )
    finally:
        execution_log.file.close()

        if configuration is not None:
            configuration.file.close()

    if len(log_content) > MAX_LOG_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Execution log must not exceed 1 MiB.",
        )

    if (
        config_content is not None
        and len(config_content) > MAX_CONFIG_BYTES
    ):
        raise HTTPException(
            status_code=413,
            detail="Configuration must not exceed 256 KiB.",
        )

    # Validate file contents and run ID using Pydantic.
    try:
        request = InvestigationRequest(
            run_id=run_id,
            log_content=log_content,
            config_content=config_content,
        )
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail=error.errors(
                include_input=False,
                include_context=False,
                include_url=False,
            ),
        ) from None

    job_id = uuid4()
    job_dir = PROJECT_DIR / "data" / "jobs" / str(job_id)

    # Save uploaded inputs before submitting the task.
    try:
        job_dir.mkdir(parents=True, exist_ok=False)

        (job_dir / "execution.log").write_bytes(request.log_content)

        if request.config_content is not None:
            (job_dir / "config.json").write_bytes(
                request.config_content
            )

    except OSError:
        logger.exception("Could not save inputs for job %s", job_id)
        raise HTTPException(
            status_code=503,
            detail="Could not save investigation input files.",
        ) from None

    # Commit the job record before the worker can start.
    try:
        create_job(job_id, request.run_id)
    except Exception:
        logger.exception("Could not create job record for %s", job_id)
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

        # Preserve inputs: the task may have reached Redis even
        # if confirmation failed.
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
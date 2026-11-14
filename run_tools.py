import json
import re
from pathlib import Path
from uuid import UUID


RUNS_DIR = Path(__file__).resolve().parent / "data" / "runs"


def get_run_config(run_id, job_id=None):
    """Read configuration belonging to this investigation."""

    if (
        not isinstance(run_id, str)
        or not re.fullmatch(r"RUN-[0-9]+", run_id)
    ):
        return {
            "ok": False,
            "error": "Invalid run ID. Expected a value such as RUN-1042.",
        }

    project_dir = Path(__file__).resolve().parent

    if job_id is not None:
        try:
            validated_job_id = UUID(str(job_id))
        except ValueError:
            return {
                "ok": False,
                "error": "Invalid job ID.",
            }

        config_path = (
            project_dir
            / "data"
            / "jobs"
            / str(validated_job_id)
            / "config.json"
        )
    else:
        # Preserve standalone sample-run behavior.
        config_path = RUNS_DIR / run_id / "config.json"

    if not config_path.is_file():
        return {
            "ok": False,
            "error": "No saved configuration is available for this investigation.",
        }

    try:
        config = json.loads(
            config_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, RecursionError):
        return {
            "ok": False,
            "error": "Could not read a valid configuration file.",
        }

    if not isinstance(config, dict) or config.get("run_id") != run_id:
        return {
            "ok": False,
            "error": "Configuration does not match the requested run.",
        }

    return {
        "ok": True,
        "source": str(config_path.relative_to(project_dir)),
        "data": config,
    }
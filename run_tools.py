import json
import re
from pathlib import Path


RUNS_DIR = Path(__file__).resolve().parent / "data" / "runs"


def get_run_config(run_id):
    """Read the saved configuration for one test run."""

    # Accept run identifiers, not arbitrary file paths.
    if not re.fullmatch(r"RUN-\d+", run_id):
        return {
            "ok": False,
            "error": "Invalid run ID. Expected a value such as RUN-1042.",
        }

    config_path = RUNS_DIR / run_id / "config.json"

    if not config_path.is_file():
        return {
            "ok": False,
            "error": f"No configuration found for {run_id}.",
        }

    try:
        with config_path.open(encoding="utf-8") as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        return {
            "ok": False,
            "error": f"Could not read configuration: {error}",
        }

    if not isinstance(config, dict) or config.get("run_id") != run_id:
        return {
            "ok": False,
            "error": "Configuration does not match the requested run.",
        }

    return {
        "ok": True,
        "source": f"data/runs/{run_id}/config.json",
        "data": config,
    }


if __name__ == "__main__":
    result = get_run_config("RUN-1042")
    print(json.dumps(result, indent=2))
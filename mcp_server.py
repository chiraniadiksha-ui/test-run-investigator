from mcp.server.fastmcp import FastMCP

from run_tools import get_run_config as read_saved_config
import argparse
from uuid import UUID


mcp = FastMCP("Test Run Tools")

JOB_ID = None
EXPECTED_RUN_ID = None



@mcp.tool()
def get_run_config(run_id: str) -> dict:
    if JOB_ID is not None and run_id != EXPECTED_RUN_ID:
        return {
            "ok": False,
            "error": "Requested run does not match this investigation.",
        }

    return read_saved_config(
        run_id=run_id,
        job_id=JOB_ID,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--job-id", type=UUID)
    parser.add_argument("--run-id")

    args = parser.parse_args()

    if (args.job_id is None) != (args.run_id is None):
        parser.error("--job-id and --run-id must be supplied together.")

    JOB_ID = args.job_id
    EXPECTED_RUN_ID = args.run_id

    mcp.run(transport="stdio")
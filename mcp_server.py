from mcp.server.fastmcp import FastMCP

from run_tools import get_run_config as read_saved_config


mcp = FastMCP("Test Run Tools")


@mcp.tool()
def get_run_config(run_id: str) -> dict:
    """Read a run's saved endpoint, traffic settings, and pass criteria.

    This reads saved configuration only.
    It does not check live device status or confirm runtime enforcement.
    """
    return read_saved_config(run_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
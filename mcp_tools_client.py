import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_DIR = Path(__file__).resolve().parent

def get_server_parameters(job_id=None, run_id=None):
    arguments = [str(PROJECT_DIR / "mcp_server.py")]

    if job_id is not None:
        if run_id is None:
            raise ValueError("run_id is required when job_id is supplied.")

        arguments.extend([
            "--job-id",
            str(UUID(str(job_id))),
            "--run-id",
            run_id,
        ])

    return StdioServerParameters(
        command=sys.executable,
        args=arguments,
    )


async def _fetch_run_config(run_id, job_id=None):
    server_parameters = get_server_parameters(
        job_id=job_id,
        run_id=run_id,
    )

    async with stdio_client(server_parameters,errlog=sys.__stderr__,) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "get_run_config",
                arguments={"run_id": run_id},
            )

            if result.isError:
                return {
                    "ok": False,
                    "error": "MCP server reported a tool execution error.",
                }

            # Version 1 of the SDK provides structuredContent.
            data = result.structuredContent

            # Fall back to the JSON text response if needed.
            if data is None:
                text = "\n".join(
                    block.text
                    for block in result.content
                    if block.type == "text"
                )
                data = json.loads(text)

            if not isinstance(data, dict):
                return {
                    "ok": False,
                    "error": "MCP tool returned an unexpected response.",
                }

            return data
        
async def _discover_tools(job_id=None, run_id=None):
    server_parameters = get_server_parameters(
        job_id=job_id,
        run_id=run_id,
    )

    async with stdio_client(
    server_parameters,
    errlog=sys.__stderr__,
) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            response = await session.list_tools()

            # Only expose tools our investigator allows.
            allowed_tools = {"get_run_config"}

            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema,
                }
                for tool in response.tools
                if tool.name in allowed_tools
            ]

def discover_tools_via_mcp(job_id=None, run_id=None):
    return asyncio.run(
        _discover_tools(
            job_id=job_id,
            run_id=run_id,
        )
    )


def get_run_config_via_mcp(run_id, job_id=None):
    try:
        return asyncio.run(
            _fetch_run_config(
                run_id=run_id,
                job_id=job_id,
            )
        )
    except Exception as error:
        return {
            "ok": False,
            "error": (
                f"Could not retrieve configuration through MCP: {error}"
            ),
        }

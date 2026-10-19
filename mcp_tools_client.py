import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_DIR = Path(__file__).resolve().parent


async def _fetch_run_config(run_id):
    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(PROJECT_DIR / "mcp_server.py")],
    )

    async with stdio_client(server_parameters) as (read, write):
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
        
async def _discover_tools():
    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(PROJECT_DIR / "mcp_server.py")],
    )

    async with stdio_client(server_parameters) as (read, write):
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


def discover_tools_via_mcp():
    return asyncio.run(_discover_tools())


def get_run_config_via_mcp(run_id):
    """Call the asynchronous MCP client from our synchronous script."""
    try:
        return asyncio.run(_fetch_run_config(run_id))
    except Exception as error:
        return {
            "ok": False,
            "error": f"Could not retrieve configuration through MCP: {error}",
        }
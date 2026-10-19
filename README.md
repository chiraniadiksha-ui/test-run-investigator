# Test Run Investigator

A local AI assistant that investigates failed test runs using execution
logs, troubleshooting guides, and saved run configurations.

## How it works

1. Reads the selected run's execution log.
2. Uses sentence embeddings to search troubleshooting guides in Qdrant.
3. Discovers available tools through a local MCP server.
4. Uses Qwen3-4B to decide whether additional configuration is needed.
5. Validates the tool request and executes it through MCP.
6. Generates a report separating observed facts, possible causes,
   recommended checks, and unknowns.

## Technology

- Python
- PyTorch and Hugging Face Transformers
- Qwen3-4B for report generation and tool selection
- sentence-transformers/all-MiniLM-L6-v2 for embeddings
- Qdrant local vector storage
- MCP Python SDK v1 for tool discovery and execution

## Setup

Python 3.12 was used for development.

Create and activate a virtual environment:

    python3.12 -m venv venv
    source venv/bin/activate

Install dependencies:

    python -m pip install -r requirements.txt

Index the sample knowledge base:

    python index_kb.py

Run an investigation:

    python investigate.py

The current entry point selects RUN-1042 in investigate.py.

Model files download on first use. Qwen3-4B weights require roughly
8 GB of disk space, with additional memory needed during execution.
The code uses Apple MPS when available and otherwise falls back to CPU.

## MCP connection test

    python test_mcp_client.py

The client starts the local MCP server automatically.

## Evaluation

    python evaluate.py

Generated reports are saved under evaluation_results.
Review them manually against expected_findings.md.

The RUN-1042 sample was manually checked for correct numerical facts,
conditional interpretation of the configured cap, and acknowledgement
of missing evidence. This is a limited evaluation, not a general
accuracy benchmark.

## Limitations

- Uses fictional sample data.
- Reads saved configuration; does not check live devices.
- Currently supports at most one tool call per investigation.
- Reports can contain reasoning errors and require human review.
- Source filename citations are not consistently complete.
- Not production-ready.
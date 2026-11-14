# Test Run Investigator

A local AI prototype for investigating failed test runs from execution logs,
retrieved troubleshooting guides, and saved run configurations. Reports separate
observed failures, possible causes, next checks, and unknowns.

## Project structure

```text
test-run-investigator/
├── api.py                  # FastAPI: upload inputs and check job status
├── investigate.py          # Log preparation, observations, retrieval, reports
├── index_kb.py             # Index troubleshooting guides in Qdrant
├── mcp_server.py           # Expose the configuration tool through MCP
├── mcp_tools_client.py     # Discover and call allowed MCP tools
├── run_tools.py            # Read and validate saved run configuration
├── settings.py             # Qdrant connection setting
├── worker/                 # Celery setup and investigation task
├── database/               # PostgreSQL connection, schema, job transitions
├── knowledge_base/         # Troubleshooting guide source documents
├── data/
│   ├── runs/               # Sample logs and configurations
│   └── jobs/               # Uploaded inputs, grouped by job UUID (ignored)
├── scripts/                # Preview, evaluation, and benchmark commands
├── tests/                  # Automated regression tests
├── docs/
│   ├── expected_findings.md # Manual accuracy-check criteria
│   └── notes/              # Background study material
├── compose.yaml            # Local Qdrant, Redis, and PostgreSQL services
├── requirements.txt        # Dependency pins (see setup limitation below)
├── reports/                # Generated worker reports (ignored)
└── evaluation_results/     # Generated evaluations and timings (ignored)
```

`venv/`, `__pycache__/`, and `vector_db/` are local environment/cache directories,
not application source. Root Python files are application entry points and shared
runtime modules; developer commands belong in `scripts/` and tests in `tests/`.

## Investigation flow

The standalone command, worker, and evaluation tools use the same helpers:
read the log, compact repeated events, split into chunks, extract observations,
retrieve a troubleshooting guide from Qdrant, discover MCP tools, optionally
fetch saved configuration, and generate a report. Embeddings use
all-MiniLM-L6-v2; observation extraction, tool decisions, and reporting use
Qwen3-4B. Apple MPS is used when available; otherwise inference uses CPU.

Recognized routine DEBUG messages can be grouped despite changing sequence
counters. State changes, measurements, and unknown message formats remain
significant. Compression preserves original line ranges and first/last messages.
Observation JSON is checked for structure and line bounds, and identical overlap
observations are deduplicated. These checks do not guarantee that model-written
observations are complete or correct.

The API submits work through Celery and Redis, tracks job states in PostgreSQL,
and saves reports under `reports/`.

## Setup and application commands

Run commands from the project root. Development uses Python 3.12.

```sh
python3.12 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

**Current setup limitation:** `requirements.txt` does not yet include all direct
runtime dependencies. PyTorch, Transformers, sentence-transformers, FastAPI,
Celery with Redis support, and psycopg must also be installed. A clean-environment
installation has not yet been verified.

Create a local `.env` with these values; choose your own password:

```dotenv
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=investigations
POSTGRES_USER=investigator
POSTGRES_PASSWORD=replace-with-your-local-password
```

Start Docker Desktop, then provision the services and sample guide index:

```sh
docker compose up -d
python -m database.init_db
python index_kb.py
```

Wait for PostgreSQL to be healthy before initializing the schema. Run the API
and worker in separate terminals with the virtual environment activated:

```sh
uvicorn api:app --reload
```

```sh
celery -A worker.celery_app:celery_app worker --pool=solo --concurrency=1 --loglevel=info
```

Open `http://127.0.0.1:8000/docs` to upload inputs through `POST /investigations`
and check the returned job UUID through `GET /investigations/{job_id}`. Successful
job status includes the report's local file path. There is no report-download
endpoint yet.

For a direct investigation without the API or job queue:

```sh
python investigate.py
```

The direct entry point currently selects `RUN-1042`. Models download on first
use and need substantial disk space and memory. The direct pipeline needs
Qdrant; API job processing additionally needs Redis and PostgreSQL.

## Developer commands

Use module commands from the project root so imports resolve consistently:

```sh
# Preview chunk counts without running model inference
python -m scripts.preview_chunks --run-id RUN-CHUNK-DEMO

# Also extract observations with the model
python -m scripts.preview_chunks --run-id RUN-CHUNK-DEMO --extract

# Generate reports for the configured evaluation runs
python -m scripts.evaluate

# Benchmark the observation pipeline and save intermediate evidence
python -m scripts.benchmark_pipeline --run-id RUN-1042

# Run regression tests without model generation
python -m unittest discover -s tests -v

# Test real API, Celery, database, model inference, and failure handling
python -m scripts.test_api_pipeline
```

Compare evaluation reports with `docs/expected_findings.md`. Benchmark artifacts
include stage timings, chunk contents, observations, tool results, and the final
report. Benchmark timings exclude API upload and queue wait.

## Current validation and limitations

- After the compression and observation-helper repairs, a direct-pipeline run
  completed in 129.12 seconds on Apple MPS with 1,500 lines compressed to 2
  chunks. Qdrant retrieval, MCP configuration access, and report generation
  succeeded. This is one sample, not a general performance guarantee.
- Nine regression tests cover compression, line coverage, token limits, invalid
  observation responses, empty evidence, and overlap deduplication.
- Uses fictional sample data and a specific structured log format.
- Saved configuration does not establish what was enforced on a live device.
- At most one configuration tool call is supported per investigation.
- Observation extraction can omit relevant facts; source citations in reports
  are not consistently complete. Human review is required.
- A real API → Redis/Celery → PostgreSQL integration test passed 23 assertions,
  including successful report generation, upload validation, and worker-failure
  propagation. The successful job took about 113 seconds on the test machine.
  The harness starts and stops its own API and solo worker on an isolated queue
  and retains two test job records plus evidence on each run.
- Installation from a clean environment, concurrent load, and crash recovery
  still need verification. This is a local prototype, not a production deployment.

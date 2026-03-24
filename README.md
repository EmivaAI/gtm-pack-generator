# Emiva (Context Graph for GTM)
Emiva is a **Context Graph for GTM** that connects to Jira, GitHub, and Slack to detect product changes and generate launch-ready GTM packs. Emiva is not just a writing assistant; it's a workflow system for detection, decisioning, approvals, and market memory.

## V1 Goal
Turn every real product change into an approved GTM pack with minimal manual coordination.

## Architecture & Features
- **Foundation (`emiva_core`)**: Shared library containing the context graph schema, CRUD logic, and core configuration used across the Emiva ecosystem.
- **Service (`gtm_pack_generator`)**: Orchestrates GTM asset generation from `LaunchCandidate` data.
- **FastAPI Core**: Lightweight web server to handle synchronous and asynchronous requests.
- **A2A Skill Interface**: Authenticated interface for other agents to pull "approved context bundles."
- **RL-lite**: A small "learn from approvals" layer to bias future variant generation.

## Environment Setup
Create a `.env` file in the root directory:

```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=emivav1
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

LLM_PROVIDER=openai # openai, anthropic, or groq
LLM_MODEL_NAME=gpt-4o
OPENAI_API_KEY=sk-...
```

## Running Locally

1. **Start the Database**:
   ```powershell
   docker-compose up -d db
   ```
2. **Apply Migrations**:
   ```powershell
   uv run alembic upgrade head
   ```
3. **Run the API Server**:
   ```powershell
   uv run uvicorn gtm_pack_generator.main:app --reload
   ```
   Swagger docs: `http://localhost:8000/docs`.

## User Flows (V1)
1. **Ingestion**: Raw events from Jira/GitHub/Slack stored as `source_event`.
2. **Normalization**: Merging signals into a unified `change_event`.
3. **Decisioning**: Scoring and tiering to create a `launch_candidate`.
4. **Generation**: Creating a `gtm_pack` with internal/external assets.
5. **Approval**: Capturing edits/approvals into `approval_event` for learning.
6. **A2A Interaction**: External agents querying context via `/v1/context/bundle`.

## Observability (Local Tracing)
Emiva uses **Arize Phoenix** for local LLM observability. To view your traces:
1. Start the server as usual (`uv run uvicorn gtm_pack_generator.main:app`).
2. The Phoenix dashboard will automatically start at `http://localhost:6006`.
3. Every LLM call, prompt, and output will be recorded there for debugging.

## API Documentation
- **POST `/api/generate/{candidate_id}`**: Generates a complete GTM pack.
- **GET `/v1/context/brand`**: Returns the brand truth profile.
- **POST `/v1/context/bundle`**: Fetches task-scoped context for external agents.

## Running Tests
```powershell
# Example for integration tests
$env:LLM_PROVIDER="groq"; $env:LLM_MODEL_NAME="llama-3.3-70b-versatile"; $env:GROQ_API_KEY="dummy"; uv run pytest tests/ -v
```

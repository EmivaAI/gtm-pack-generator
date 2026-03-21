# gtm-pack-generator
An AI agent that generates GTM packs based on the current context given the launch candidate. This is the **Stage 4** component for Emiva V1.

## Architecture & Features
- **FastAPI Core**: Lightweight web server to handle synchronous and asynchronous requests.
- **SQLAlchemy DB**: Connected to PostgreSQL for tracking `LaunchCandidate`, `GtmPack`, and `GtmAsset` states.
- **LangChain Integration**: Connects to the LLM (OpenAI, Anthropic, or Groq) using structured prompts to map out six distinct GTM assets.
- **Background Tasks**: Generates heavy AI assets in the background, updating database states as they complete.

## Environment Setup
Create a `.env` file in the root directory and configure the following required variables:

```ini
# Database (if running locally without Docker, or overriding Docker defaults)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=emivav1
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Language Model
LLM_PROVIDER=openai # Options: openai, anthropic, groq
LLM_MODEL_NAME=gpt-4o

# API Keys (Provide the one corresponding to your provider)
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
```

## Running Locally

1. **Start the Database** (using the provided docker-compose):
   ```bash
   docker-compose up -d db
   ```
2. **Apply Migrations** (if any schema updates):
   ```bash
   uv run alembic upgrade head
   ```
3. **Run the API Server**:
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   The API will be available at `http://localhost:8000`. You can view the Swagger documentation at `http://localhost:8000/docs`.

## API Documentation

### POST `/api/generate/{candidate_id}`
Generates a complete GTM pack for a specific launch candidate.
- **Path Parameter**: `candidate_id` (Integer ID of an existing LaunchCandidate in the database)
- **Response**: Returns the created `GtmPack` metadata. Asset generation continues asynchronously.

## Running Tests
To run tests locally, you must provide a valid LLM provider in your environment because Pydantic will validate the settings on startup. For integration tests, real API keys are not required as network requests are cached via `vcrpy`.

```bash
LLM_PROVIDER=groq LLM_MODEL_NAME=llama-3.3-70b-versatile GROQ_API_KEY=dummy uv run pytest tests/ -v
```

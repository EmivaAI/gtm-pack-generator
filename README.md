# gtm-pack-generator
An AI agent that generates GTM pack based on the current context given the launch candidate

## Running Tests
To run tests locally, you must provide a valid LLM provider in your environment because Pydantic will validate the settings on startup. For integration tests, real API keys are not required as responses are cached via `vcrpy`.

```bash
LLM_PROVIDER=openai LLM_MODEL_NAME=gpt-4o OPENAI_API_KEY=dummy uv run pytest tests/ -v
```

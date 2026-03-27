# Use a slim Python image
FROM python:3.12-slim-bookworm

# Install UV via pip (more reliable than GHCR in some environments)
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy the entire workspace first (for lockfile and workspace members)
COPY pyproject.toml uv.lock ./
COPY emiva_core/ ./emiva_core/
COPY emiva_api/ ./emiva_api/
COPY gtm_pack_generator/ ./gtm_pack_generator/

# Install dependencies for the whole workspace
RUN uv sync --frozen

# Set the path to the virtualenv
ENV PATH="/app/.venv/bin:$PATH"

# Default command (will be overridden in docker-compose)
CMD ["uvicorn", "emiva_api.main:app", "--host", "0.0.0.0", "--port", "8001"]

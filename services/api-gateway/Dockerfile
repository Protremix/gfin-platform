# GFIN API Gateway — Dockerfile
# Layer B: REQUIRES EXTERNAL INFRASTRUCTURE (Docker build + Kubernetes deployment)

FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY packages/ packages/
COPY services/ services/

# Run as non-root user
RUN useradd -m gfin
USER gfin

EXPOSE 8000

CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

# Install Node.js
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Build frontend
COPY frontend/package*.json frontend/
RUN npm --prefix frontend install
COPY frontend/ frontend/
RUN npm --prefix frontend run build

# Setup backend
COPY backend/pyproject.toml backend/uv.lock backend/
RUN uv sync --project backend
COPY backend/ backend/

# Copy built frontend to backend/static
RUN cp -r frontend/dist backend/static

EXPOSE 8000

CMD uv run --project backend uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir backend

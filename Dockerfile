FROM python:3.11-slim

# Install Node.js and curl
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

# Setup backend dependencies
COPY backend/pyproject.toml backend/uv.lock backend/
RUN uv sync --project backend

# Copy all backend source
COPY backend/ backend/

# Copy built frontend into backend/static
RUN cp -r frontend/dist backend/static

EXPOSE 8000

WORKDIR /app/backend

ENV PORT=8000

CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

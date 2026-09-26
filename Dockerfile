# Multi-stage Dockerfile for unified Debug Assistant (Frontend + Backend)

# Stage 1: Build React/Vite Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY debug_assistant/frontend/package*.json ./
RUN npm ci
COPY debug_assistant/frontend/ ./
RUN npm run build

# Stage 2: Python FastAPI Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY debug_assistant/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code, models, and core engine
COPY debug_assistant/ ./debug_assistant/

# Copy built frontend from Stage 1 into frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./debug_assistant/frontend/dist

# Expose port (injected by host/platform or default 8000)
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn debug_assistant.backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
